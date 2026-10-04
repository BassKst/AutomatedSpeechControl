import logging
import numpy as np
import librosa

from common.config import TOP_DB, SAMPLE_RATE

logger = logging.getLogger(__name__)


def trim_silence(audio_np: np.ndarray) -> np.ndarray:
    """
    обрезки тишины по краям аудио
    """
    if audio_np.ndim > 1:
        audio_np = audio_np.flatten()

    trimmed_audio, _ = librosa.effects.trim(audio_np, top_db=TOP_DB)

    # Защита: если после обрезки осталось меньше 0.5 секунды, возвращаем оригинал
    min_length = int(SAMPLE_RATE * 0.5)
    if len(trimmed_audio) < min_length:
        logger.debug("Аудио слишком короткое после обрезки, используем оригинал.")
        return audio_np

    return trimmed_audio

