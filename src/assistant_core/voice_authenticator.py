import logging

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine

import common.config
from common.audio_utils import trim_silence
from common.encryption_service import decrypt_list

logger = logging.getLogger(__name__)


class VoiceAuthenticator:
    """
    Модуль биометрической аутентификации по голосу.
    """

    def __init__(self):
        logger.info("Инициализация модели Resemblyzer (VoiceEncoder)...")
        self.encoder = VoiceEncoder()
        self._embeddings_cache = {}

    def sync_cache(self, active_users: list):
        """
        кэширует профили в оперативную память.
        """
        logger.info("Синхронизация кэша голосовых профилей...")
        new_cache = {}

        for user in active_users:
            if not user.voice_embedding:
                continue
            try:
                decrypted_list = decrypt_list(user.voice_embedding)
                emb_array = np.array(decrypted_list, dtype=np.float32)
                new_cache[user.id] = (user, emb_array)
            except Exception as e:
                logger.error(f"Ошибка кэширования профиля юзера {user.username}: {e}")

        self._embeddings_cache = new_cache
        logger.info(f"Загружено профилей в кэш: {len(self._embeddings_cache)}")

    def identify_user(self, raw_audio: bytes, threshold: float = 0.8):
        if not self._embeddings_cache:
            logger.warning("Кэш пользователей пуст! Аутентификация невозможна.")
            return None, 0.0

        audio_np = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
        audio_np /= 32768.0  # Нормализация от -1.0 до 1.0
        audio_np = trim_silence(audio_np)

        wav = preprocess_wav(audio_np, source_sr=common.config.SAMPLE_RATE)
        emb = self.encoder.embed_utterance(wav)

        best_user = None
        best_score = 0.0

        for user, stored_emb in self._embeddings_cache.values():
            score = 1 - cosine(stored_emb, emb)

            if score > best_score:
                best_score = score
                best_user = user

        if best_score >= threshold:
            return best_user, best_score

        return None, best_score

    def get_user_and_access(self, raw_audio) -> tuple[int | None, int]:
        user, similarity_score = self.identify_user(raw_audio)

        if not user:
            logger.warning(f"Пользователь не распознан ({similarity_score:.3f})")
            return None, 0

        logger.info(f"Определён пользователь: {user.username} ({similarity_score:.3f})")

        access_level = user.role.access_level if user.role else 0
        return user.id, access_level


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    import sounddevice as sd
    import soundfile as sf
    import sys
    import os
    from assistant_core.database.db_service import get_active_users

    print("ТЕСТОВЫЙ РЕЖИМ: Voice Authenticator")

    auth = VoiceAuthenticator()
    active_users = get_active_users()

    if not active_users:
        print("❌ ОШИБКА: В базе данных нет активных пользователей.")
        sys.exit(1)

    auth.sync_cache(active_users)

    RECORD_SECONDS = 5
    print(f"\nСейчас начнется запись на {RECORD_SECONDS} секунд.")
    input("Нажмите ENTER, чтобы начать запись...")

    print("\nЗАПИСЬ")
    audio_data = sd.rec(
        int(RECORD_SECONDS * common.config.SAMPLE_RATE),
        samplerate=common.config.SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    print("ЗАПИСЬ ОСТАНОВЛЕНА.\n")

    raw_audio_bytes = audio_data.tobytes()

    print("Анализ биометрии...")
    user_obj, score = auth.identify_user(raw_audio_bytes, threshold=0.8)

    if user_obj:
        print(f"Система распознала '{user_obj.username}'")
    else:
        print("Голос не распознан.")

    print(f"Лучший Similarity Score: {score:.3f} (Порог: 0.800)")

    print("\nСохраняем обрезанный файл")

    audio_float = np.frombuffer(raw_audio_bytes, dtype=np.int16).astype(np.float32)
    audio_float /= 32768.0
    trimmed_audio_float = trim_silence(audio_float)

    os.makedirs(os.path.join(common.config.BASE_DIR, "cache"), exist_ok=True)
    save_path = os.path.join(common.config.BASE_DIR, "cache", "test_trimmed.wav")

    sf.write(save_path, trimmed_audio_float, common.config.SAMPLE_RATE)

    print(f"Файл успешно сохранен по пути: {save_path}")
