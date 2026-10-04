import importlib
import inspect
import logging
import pkgutil
from pathlib import Path

from .base import BaseIntegration

logger = logging.getLogger("IntegrationFactory")


class IntegrationManager:
    """
    Менеджер интеграций (Registry Pattern).
    """

    def __init__(self):
        self.integrations = {}
        self._nlu_schema_cache = None
        self._discover_and_register_integrations()

    def _discover_and_register_integrations(self):
        plugins_folder_name = "plugins"

        plugins_package_name = f"{__package__}.{plugins_folder_name}"

        plugins_dir = Path(__file__).resolve().parent / plugins_folder_name

        if not plugins_dir.exists() or not plugins_dir.is_dir():
            logger.warning(f"Папка с плагинами не найдена по пути: {plugins_dir}. Создайте её.")
            return

        logger.info(f"Авто-поиск интеграций в директории {plugins_folder_name}...")

        for _, module_name, is_pkg in pkgutil.iter_modules([str(plugins_dir)]):
            if is_pkg:
                continue

            full_module_name = f"{plugins_package_name}.{module_name}"

            try:
                module = importlib.import_module(full_module_name)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseIntegration) and obj is not BaseIntegration:
                        if obj.__module__ == full_module_name:
                            try:
                                plugin_instance = obj()
                                self.register(plugin_instance)
                            except Exception as e:
                                logger.error(f"Не удалось инициализировать плагин {name} в {module_name}: {e}")

            except ImportError as e:
                logger.error(f"Ошибка импорта в плагине {module_name}. Детали: {e}")
            except Exception as e:
                logger.error(f"Неизвестная ошибка при загрузке плагина {module_name}: {e}")

    def register(self, integration_instance):
        """Добавление интеграции в словарь"""
        self.integrations[integration_instance.intent_name] = integration_instance
        self._nlu_schema_cache = None
        logger.info(f"Успешно зарегистрирована интеграция: {integration_instance.intent_name}")

    @property
    def nlu_schema(self) -> dict:
        """
        Собирает чистый JSON-словарь с правилами для NLU-сервера.
        """
        if self._nlu_schema_cache is None:
            schema = {}
            for intent_name, integration in self.integrations.items():
                schema[intent_name] = {
                    "intent_corpus": integration.intent_corpus,
                    "entity_corpus": [
                        {"name": corpus.name, "data": corpus.data}
                        for corpus in integration.entity_corpus
                    ]
                }
            self._nlu_schema_cache = schema
        return self._nlu_schema_cache

    def execute_intent(self, intent_name: str, entities: dict, context: dict) -> dict:
        """
        Поиск нужного класса и запуск его метода execute.
        """
        integration = self.integrations.get(intent_name)

        if not integration:
            logger.error(f"Интеграция для интента '{intent_name}' не найдена!")
            return {"status": "error", "message": "Эта команда пока не поддерживается системой."}

        logger.info(f"Передача управления модулю: {integration.__class__.__name__}")

        try:
            # Выполняем саму логику
            result = integration.execute(entities, context)
            return result
        except Exception as e:
            logger.exception("Ошибка внутри модуля интеграции")
            return {"status": "error", "message": "Произошла критическая ошибка при выполнении скрипта."}