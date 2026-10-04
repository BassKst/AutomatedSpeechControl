from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator, Optional


@dataclass
class UserRequest:
    """Единый формат запроса, независимый от того, откуда он пришел."""
    text: str
    raw_audio: bytes  # Для биометрии (всегда нужно передавать)
    meta: Optional[dict] = None  # В будущем здесь может быть {"telegram_user_id": 123}


class IAssistantChannel(ABC):
    """
    Абстрактный канал общения (Port).
    Скрывает в себе специфику работы с сетью, потоками, микрофоном и т.д.
    """

    @abstractmethod
    def listen(self) -> Generator[UserRequest, None, None]:
        """Бесконечный генератор входящих запросов пользователя."""
        pass

    @abstractmethod
    def reply(self, text: str) -> None:
        """Отправить текст пользователю (канал сам решит, озвучить его или послать текстом)."""
        pass

    @abstractmethod
    def interrupt(self) -> None:
        """Принудительно прервать текущий ответ (Barge-in / Остановка речи)."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Освободить ресурсы (остановить потоки, закрыть сокеты и т.д.)."""
        pass
