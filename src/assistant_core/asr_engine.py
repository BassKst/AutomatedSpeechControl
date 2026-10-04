import os
import sys
import json
import queue
import logging
from typing import List, Generator
from resemblyzer import VoiceEncoder

import pyaudio
from vosk import Model, KaldiRecognizer, SetLogLevel

from assistant_core.database.models import User
from common.config import SAMPLE_RATE

logger = logging.getLogger(__name__)
encoder = VoiceEncoder()

SetLogLevel(-1)


class ASREngine:
    def __init__(self, model_path: str, vocabulary: List = None):
        self.model_path = model_path
        self.vocabulary = vocabulary

        self.audio_queue = queue.Queue()

        self._check_model_exists()

        logger.info("Инициализация акустической модели Vosk...")
        self.model = Model(self.model_path)

        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        logger.info("Модуль ASR загружен в режиме полного распознавания.")

    def _check_model_exists(self):
        if not os.path.exists(self.model_path):
            logger.error(f"Модель Vosk не найдена по пути: {self.model_path}")
            logger.error("Скачайте модель с https://alphacephei.com/vosk/models и распакуйте.")
            sys.exit(1)

    def _audio_callback(self, in_data, frame_count, time_info, status):
        self.audio_queue.put(in_data)
        return None, pyaudio.paContinue

    def listen(self) -> Generator:
        audio_interface = pyaudio.PyAudio()
        audio_buffer = []

        try:
            stream = audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=8000,
                stream_callback=self._audio_callback
            )

            stream.start_stream()
            logger.info("Микрофон активирован. Голосовой помощник слушает...")

            while True:
                data = self.audio_queue.get()
                audio_buffer.append(data)

                if self.recognizer.AcceptWaveform(data):
                    result_json = self.recognizer.Result()
                    result_dict = json.loads(result_json)
                    text = result_dict.get("text", "").strip()

                    if text:
                        full_audio = b"".join(audio_buffer)
                        audio_buffer = []
                        yield text, full_audio

        except KeyboardInterrupt:
            logger.info("Остановка работы ASR модуля (прервано пользователем).")
        except Exception as e:
            logger.error(f"Ошибка аудиопотока: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            audio_interface.terminate()
            logger.info("Аудиоинтерфейс корректно закрыт.")
