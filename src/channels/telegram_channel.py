from assistant_core.interfaces import IAssistantChannel, UserRequest

"""
Благодаря гексагональной архитектуре, ядро приложения позволяет инкапсулировать потоки ввода/вывода в отдельные
интерфейсы, управляющие ими
Пример создания канала для клиента телеграм-бота
"""


class TelegramChannel(IAssistantChannel):
    def listen(self):
        # Логика Long-polling библиотеки python-telegram-bot
        # При получении Voice-message: скачиваем, распознаем, выдаем объект
        yield UserRequest(text="настрой новый узел", raw_audio=b"...", meta={"user_id": 12345})

    def reply(self, text):
        # Вместо TTS, мы просто делаем API запрос в Telegram
        self.bot.send_message(chat_id=self.current_user, text=text)

    def interrupt(self):
        pass  # В телеграме нет перебивания
