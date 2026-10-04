"""Заготовка канала Telegram: пример подключения к порту IAssistantChannel, не рабочая реализация."""

from typing import Generator

from assistant_core.interfaces import IAssistantChannel, UserRequest


class TelegramChannel(IAssistantChannel):
    def listen(self) -> Generator[UserRequest, None, None]:
        # Логика Long-polling библиотеки python-telegram-bot
        # При получении Voice-message: скачиваем, распознаем, выдаем объект
        yield UserRequest(text="настрой новый узел", raw_audio=b"...", meta={"user_id": 12345})

    def reply(self, text: str) -> None:
        # Вместо TTS, мы просто делаем API запрос в Telegram
        self.bot.send_message(chat_id=self.current_user, text=text)

    def interrupt(self) -> None:
        pass  # В телеграме нет перебивания

    def close(self) -> None:
        pass
