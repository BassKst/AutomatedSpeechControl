import os
import shutil
import sounddevice as sd
import soundfile as sf
import numpy as np
from resemblyzer import VoiceEncoder
import librosa
from numpy.linalg import norm

from common.audio_utils import trim_silence
from common.config import SAMPLE_RATE

CACHE_DIR = "cache"
PHRASES =[
    "Голосовой помощник активирован",
    "Открой пожалуйста блокнот",
    "Сегодня хорошая погода"
]

encoder = VoiceEncoder()


def clear_cache():
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    os.makedirs(CACHE_DIR)


def record_phrase(index):
    print(f"\nСкажите фразу: \"{PHRASES[index]}\"")
    input("Нажмите Enter для начала записи...")

    duration = 3
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()

    # --- ПРИМЕНЯЕМ ОБРЕЗКУ ТИШИНЫ ПЕРЕД СОХРАНЕНИЕМ ---
    audio_trimmed = trim_silence(audio)

    path = f"{CACHE_DIR}/voice_{index}.wav"
    sf.write(path, audio_trimmed, SAMPLE_RATE)

    return path


def get_embedding(path):
    wav, _sr = librosa.load(path, sr=SAMPLE_RATE)
    # Исправлен баг: раньше тут дважды вызывался embed_utterance(wav)
    embedding = encoder.embed_utterance(wav)
    return embedding


def average_embeddings(embeddings):
    return np.mean(embeddings, axis=0)


def similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))


def record_and_build_embedding():
    clear_cache()
    embeddings = []

    for i in range(len(PHRASES)):
        path = record_phrase(i)
        emb = get_embedding(path)
        embeddings.append(emb)

    final_embedding = average_embeddings(embeddings)

    clear_cache()
    return final_embedding.tolist()


def test_embedding(user_embedding):
    clear_cache()
    print("\nТестовая фраза. Скажите что-нибудь.")

    input("Enter для записи...")

    audio = sd.rec(int(3 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()

    # --- ПРИМЕНЯЕМ ОБРЕЗКУ ДЛЯ ТЕСТОВОЙ ФРАЗЫ ---
    audio_trimmed = trim_silence(audio)

    path = f"{CACHE_DIR}/test.wav"
    sf.write(path, audio_trimmed, SAMPLE_RATE)

    emb = get_embedding(path)
    sim = similarity(np.array(user_embedding), emb)

    clear_cache()
    return sim
