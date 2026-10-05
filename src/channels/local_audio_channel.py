import common.logger_config  # noqa: F401 - импорт ради побочного эффекта: настройка корневого логгера
import queue

import threading
import logging
import sounddevice as sd
from typing import Generator

from assistant_core.interfaces import IAssistantChannel, UserRequest
from assistant_core.asr_engine import ASREngine
from assistant_core.tts_engine import TTSEngine

logger = logging.getLogger(__name__)


class LocalAudioChannel(IAssistantChannel):
    """
    реализация канала для локального ПК (Микрофон + Динамики).
    """

    def __init__(
            self,
            asr: ASREngine,
            tts: TTSEngine,
            wake_word: str,
            interrupt_enabled: bool = True,
            ignore_when_speaking: bool = False
    ):
        self.asr = asr
        self.tts = tts
        self.wake_word = wake_word.lower()
        self.interrupt_enabled = interrupt_enabled
        self.ignore_when_speaking = ignore_when_speaking

        self._tts_queue = queue.Queue()
        self._is_speaking = threading.Event()
        self._stop_event = threading.Event()

        # Запускаем внутренний поток озвучки
        self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_thread.start()

    def _tts_worker(self):
        """Фоновый поток для последовательного воспроизведения речи."""
        while not self._stop_event.is_set():
            text = self._tts_queue.get()
            if text is None:  # сигнал к остановке
                break
            try:
                self._is_speaking.set()
                self.tts.speak(text)
            except Exception as e:
                logger.error(f"Ошибка воспроизведения TTS: {e}")
            finally:
                self._is_speaking.clear()
                self._tts_queue.task_done()

    def listen(self) -> Generator[UserRequest, None, None]:
        logger.info(f"Канал активирован. Ожидаю фразу: '{self.wake_word}'")

        for text, raw_audio in self.asr.listen():
            if self._stop_event.is_set():
                break

            audio_text = text.lower().strip()
            if not audio_text:
                continue

            if self.ignore_when_speaking and self._is_speaking.is_set():
                continue

            if self.wake_word not in audio_text:
                continue

            if self._is_speaking.is_set() and self.interrupt_enabled:
                self.interrupt()

            command_text = audio_text.split(self.wake_word, 1)[1].strip()
            if command_text:
                logger.info(f"[MIC] Распознана команда: {command_text}")
                yield UserRequest(text=command_text, raw_audio=raw_audio)

    def reply(self, text: str) -> None:
        self._tts_queue.put(text)

    def interrupt(self) -> None:
        if not self._is_speaking.is_set():
            return
        logger.info("[MIC] остановка речи (Barge-in)!")
        with self._tts_queue.mutex:
            self._tts_queue.queue.clear()
        sd.stop()

    def close(self) -> None:
        self._stop_event.set()
        self._tts_queue.put(None)
        self._tts_thread.join(timeout=2)
        logger.info("Аудиоканал успешно выключен.")
