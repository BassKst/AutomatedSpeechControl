import logging
from concurrent.futures import ThreadPoolExecutor

from assistant_core.integrations.manager import IntegrationManager
from assistant_core.interfaces import IAssistantChannel, UserRequest
from assistant_core.database.db_service import update_log_in_db, add_db_log
from assistant_core.nlu_client import remote_call
from assistant_core.log_parser import LogParser
from assistant_core.voice_authenticator import VoiceAuthenticator
from common.config import IGNORE_UNAUTHORIZED

logger = logging.getLogger(__name__)


class AssistantApplication:

    def __init__(
            self,
            channel: IAssistantChannel,
            manager: IntegrationManager,
            parser: LogParser,
            voice_auth: VoiceAuthenticator
    ):
        self.channel = channel
        self.manager = manager
        self.parser = parser
        self.voice_auth = voice_auth

        self.executor = ThreadPoolExecutor(max_workers=4)
        self.session_context = {}

    def _execute_async(self, integration, entities, log_id):
        """Запуск долгих интеграций в отдельном потоке."""
        try:
            result = integration.execute(entities, self.session_context)
            status = result.get("status", "error")
            raw_log = result.get("raw_log", "")

            if status == "error":
                speech_text = self.parser.analyze_error_log(raw_log)
            else:
                speech_text = result.get("message", "Фоновая задача завершена.")

            self.channel.reply(speech_text)
            update_log_in_db(log_id, status, raw_log if raw_log else speech_text)
        except Exception as e:
            logger.exception(f"Критическая ошибка в фоне: {e}")
            self.channel.reply("Произошла критическая ошибка при выполнении фоновой задачи.")
            update_log_in_db(log_id, "ERROR", str(e))

    def _process_request(self, req: UserRequest):
        # Биометрия
        user_id, access_level = self.voice_auth.get_user_and_access(req.raw_audio)

        if user_id is None and IGNORE_UNAUTHORIZED:
            logger.warning("Отмена выполнения: Пользователь не распознан по голосу.")
            self.channel.reply("Голос не распознан. Доступ запрещен.")
            return

        # NLU
        nlu_data = remote_call(req.text, self.manager.nlu_schema)
        if nlu_data:
            intent = nlu_data.get("intent")
            entities = nlu_data.get("entities", {})
            sys_msg = nlu_data.get("msg") or "Команда не распознана."
        else:
            intent = None
            entities = None
            sys_msg = "Не удалось установить соединение с сервером."

        # БД
        log_id = add_db_log(user_id, req.text, entities, intent)

        if intent is None:
            update_log_in_db(log_id, "CONNECTION_ERROR", sys_msg)
            self.channel.reply(sys_msg)
            return

        if intent == "unknown":
            logger.warning(sys_msg)
            update_log_in_db(log_id, "UNKNOWN_COMMAND", "Не удалось извлечь intent из текста.")
            self.channel.reply(sys_msg)
            return

        # Проверка интеграции
        integration = self.manager.integrations.get(intent)
        if not integration:
            self.channel.reply("Данная команда пока не поддерживается.")
            update_log_in_db(log_id, "ERROR", f"Интеграция {intent} не найдена.")
            logger.warning(f"Модуль для интента {intent} не найден.")
            return

        # Проверка прав (RBAC)
        if access_level < integration.access_level:
            logger.warning(f"Доступ запрещен. У пользователя уровень {access_level}, нужен {integration.access_level}")
            self.channel.reply("У вас недостаточно прав для выполнения этой операции.")
            update_log_in_db(log_id, "DENIED", "Недостаточно прав.")
            return

        # 6. Выполнение бизнес-логики
        if integration.is_long_running:
            self.channel.reply(sys_msg)
            # self.channel.reply("Запускаю процесс в фоновом режиме.")
            self.executor.submit(self._execute_async, integration, entities, log_id)
        else:
            result = integration.execute(entities, self.session_context)
            status = result.get("status", "error")
            speech_text = result.get("message", "Выполнено.")

            if status == "error":
                speech_text = self.parser.analyze_error_log(result.get("raw_log", ""))

            self.channel.reply(sys_msg)
            self.channel.reply(speech_text)
            update_log_in_db(log_id, status, speech_text)

    def run(self):
        self.channel.reply("Система запущена и готова к работе.")

        try:
            for request in self.channel.listen():
                # Хардкод выключения оставим здесь, так как это команда ядру
                if request.text in ["стоп", "отмена", "отключись"]:
                    self.channel.reply("Служба отключается.")
                    break

                self._process_request(request)
        except KeyboardInterrupt:
            logger.info("Программа остановлена комбинацией Ctrl+C.")
        finally:
            self.shutdown()

    def shutdown(self):
        self.channel.close()
        self.executor.shutdown(wait=False)
        logger.info("Главное ядро остановлено.")