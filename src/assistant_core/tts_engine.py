import torch
import sounddevice as sd
import logging
import warnings

# Отключаем лишние предупреждения от PyTorch, чтобы лог был чистым
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)


class TTSEngine:
    """
    Модуль автономного синтеза речи (Edge TTS) на базе Silero.
    """

    def __init__(self, speaker: str = 'baya', sample_rate: int = 48000):
        self.device = torch.device('cpu')
        self.speaker = speaker
        self.sample_rate = sample_rate

        logger.info("Инициализация локальной акустической модели Silero TTS...")

        try:
            self.model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                           model='silero_tts',
                                           language='ru',
                                           speaker='v4_ru',
                                           trust_repo=True)
            self.model.to(self.device)
            logger.info("Модуль TTS успешно загружен и готов к работе в offline-режиме.")
        except Exception as e:
            logger.error(f"Не удалось загрузить модель Silero: {e}")
            raise e

    def speak(self, text: str):
        """
        Метод озвучивания текста.
        Блокирует выполнение программы до конца произнесения фразы.
        """
        # Убираем лишние символы, которые нейросеть может не понять
        if text:
            clean_text = text.replace('\n', ' ').strip()
        else:
            return
        if not clean_text:
            return

        logger.info(f"Озвучивание: '{clean_text}'")

        try:
            # Генерация тензора аудиосигнала
            audio_tensor = self.model.apply_tts(text=clean_text,
                                                speaker=self.speaker,
                                                sample_rate=self.sample_rate)

            # Конвертация в numpy массив и воспроизведение через sounddevice
            audio_data = audio_tensor.numpy()
            sd.play(audio_data, self.sample_rate)
            sd.wait()  # Ожидание окончания воспроизведения

        except Exception as e:
            logger.error(f"Ошибка при синтезе речи: {e}")


# ==========================================
# Пример использования и тестирования TTS
# ==========================================
if __name__ == "__main__":
    # Инициализация движка. Голоса (speaker) в v4_ru: 'aidar', 'baya', 'kseniya', 'xenia', 'eugene'
    tts = TTSEngine(speaker='baya')

    # Тестируем ответы, которые мы получали из Модуля Интеграции
    test_responses = (
        "Узел в Нидерландах успешно развернут.",
        "Ошибка соединения. Порт заблокирован.",
        "Скрипт исправления файрвола успешно применен, пользователи подключены."
    )

    for response in test_responses:
        tts.speak(response)
