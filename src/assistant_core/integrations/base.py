from abc import ABC, abstractmethod
import logging

from assistant_core.integrations.entity_corpus import Corpus


class BaseIntegration(ABC):
    """
    Абстрактный базовый класс для всех интеграций.
    Гарантирует, что каждый плагин будет иметь метод execute.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def intent_name(self) -> str:
        """Связь класса с намерением из NLU (например, 'deploy_node')"""
        pass

    @property
    @abstractmethod
    def intent_corpus(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def entity_corpus(self) -> list[Corpus]:
        pass

    @property
    def is_long_running(self) -> bool:
        """
        Если True, диспетчер запустит эту задачу в отдельном потоке (асинхронно),
        чтобы голосовой помощник мог продолжить слушать эфир.
        """
        return False

    @property
    def access_level(self) -> int:
        """
        Уровень доступа
        """
        return 0

    @abstractmethod
    def execute(self, entities: dict, context: dict) -> dict:
        """
        Основной метод выполнения логики.
        :param entities: Извлеченные сущности (регион, IP и тд)
        :param context: Общий контекст сессии (последний скопированный IP, текущий юзер)
        :return: Словарь со статусом и сообщением
        """
        pass
