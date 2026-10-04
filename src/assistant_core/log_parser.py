import re
import logging

logger = logging.getLogger(__name__)


class LogParser:
    """
    Модуль анализа системных логов (Log Parsing).
    Соответствует блоку BPMN: 'Парсинг логов ошибок (выделение ключевой причины)'.
    Использует детерминированные правила для извлечения сути ошибки из сырого текста.
    """

    def __init__(self):
        # Словарь известных паттернов ошибок.
        # Значение (Value) - это кортеж из регулярных выражений, которые могут встретиться в логах SSH или API.
        # Ключ (Key) - это человекочитаемый диагноз на русском языке для озвучки (TTS).
        self.error_signatures = {
            "Ошибка соединения. Порт заблокирован файрволом.": (
                r"Connection refused",
                r"No route to host",
                r"UFW DROP",
                r"iptables: Permission denied"
            ),
            "Таймаут операции. Сервер не отвечает.": (
                r"Connection timed out",
                r"TimeoutError",
                r"ReadTimeout"
            ),
            "Ошибка аутентификации. Проверьте SSH ключи.": (
                r"Permission denied \(publickey",
                r"Authentication failed",
                r"Invalid password"
            ),
            "Недостаточно места на диске сервера.": (
                r"No space left on device",
                r"Disk quota exceeded"
            ),
            "Служба VPN не запущена или упала.": (
                r"vpn-service\.service: Failed",
                r"code=exited, status=1/FAILURE",
                r"Active: failed"
            ),
            "Не предоставлены необходимые данные.": (
                r"NoIP",
                r"NoRG",
                r"NoNB"
            )
        }

    def analyze_error_log(self, raw_log: str) -> str:
        """
        Сканирует сырой текст лога и возвращает короткую выжимку (суть ошибки).
        Если сигнатура не найдена, возвращает базовое сообщение.
        """
        if not raw_log:
            return "Журнал ошибок пуст."

        logger.warning("Анализ системного лога...")

        # Переводим лог в нижний регистр для независимости от регистра (оставляя паттерны в нижнем/смешанном)
        # Но регулярки лучше искать с флагом re.IGNORECASE
        for diagnosis, patterns in self.error_signatures.items():
            for pattern in patterns:
                # Поиск паттерна в логе без учета регистра
                if re.search(pattern, raw_log, re.IGNORECASE):
                    logger.warning(f"Найдена сигнатура ошибки: {pattern} -> {diagnosis}")
                    return diagnosis

        # Если ни один паттерн не совпал, выдаем универсальный ответ
        logger.warning("Неизвестная ошибка в логе. Требуется визуальный анализ.")
        return "Произошла неизвестная системная ошибка. Рекомендуется ручная проверка логов."


# ==========================================
# Пример использования и тестирования Парсера
# ==========================================
if __name__ == "__main__":
    parser = LogParser()

    # Эмулируем различные "портянки" логов, которые могут прийти от серверов
    test_logs = (
        # 1. Лог падения SSH из-за закрытого порта (UFW)
        "ssh: connect to host 192.168.1.105 port 22: Connection refused\n"
        "fatal: Could not read from remote repository.",

        # 2. Лог падения API из-за таймаута
        "requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.ramware.com', port=443): "
        "Max retries exceeded with url: /deploy (Caused by ReadTimeoutError)",

        # 3. Лог SystemD, где упал процесс
        "May 14 12:00:01 node-de-1 systemd: vpn-service.service: Failed with result 'exit-code'.\n"
        "May 14 12:00:01 node-de-1 systemd: Failed to start VPN Tunneling Service.",

        # 4. Неизвестный лог (кастомная ошибка)
        "Error 500: Database synchronization sequence failed at step 4."
    )

    print("--- Тестирование модуля парсинга логов ---")
    for i, raw_log in enumerate(test_logs, 1):
        print(f"\n Входящий сырой лог (фрагмент):\n   {raw_log}...")

        diagnosis = parser.analyze_error_log(raw_log)
        print(f"    Анализ Парсера (Суть): => {diagnosis}")