import os
from pathlib import Path

from dotenv import load_dotenv

def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")

load_dotenv()
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
WAKE_WORD = os.getenv("WAKE_WORD")
NLU_MODE = os.getenv("NLU_MODE")
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE"))
TOP_DB = int(os.getenv("TOP_DB"))

IGNORE_WHEN_SPEAKING = env_bool("IGNORE_WHEN_SPEAKING")
IGNORE_UNAUTHORIZED = env_bool("IGNORE_UNAUTHORIZED")
INTERRUPT_TTS = env_bool("INTERRUPT_TTS")

BASE_DIR = Path(__file__).resolve()
while not (BASE_DIR / "pyproject.toml").exists():
    BASE_DIR = BASE_DIR.parent
CERT_PATH = os.path.join(BASE_DIR, "certs", "server.crt")
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH")

API_HOST = os.getenv("API_HOST")
PORT = int(os.getenv("PORT"))