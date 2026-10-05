"""Пример driving-адаптера для Telegram.

Благодаря гексагональной архитектуре ядро приложения позволяет инкапсулировать
потоки ввода/вывода в отдельные интерфейсы, управляющие ими. Этот модуль -
образец того, как канал телеграм-бота подключается к порту ``IAssistantChannel``.

.. note::
    Это **не** рабочая реализация, а каркас-иллюстрация: здесь нет ни клиента
    ``python-telegram-bot``, ни токена бота, ни очереди сообщений. Модуль
    показывает точки расширения (long-polling в ``listen``, отправка текста в
    ``reply``) и гарантирует, что адаптер удовлетворяет контракту порта -
    иначе его нельзя было бы даже инстанцировать.
"""

from typing import Generator

from assistant_core.interfaces import IAssistantChannel, UserRequest


class TelegramChannel(IAssistantChannel):
    """Каркас телеграм-канала, реализующий все четыре метода порта."""

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
        # Реальный адаптер здесь остановил бы long-polling и закрыл сессию
        # python-telegram-bot. В каркасе ресурсов нет, поэтому и освобождать
        # нечего. Метод обязателен: без него ABC не дал бы создать экземпляр.
        pass
