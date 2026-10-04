"""Настройки приложения из переменных окружения и src/common/.env."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
ENV_FILE = PACKAGE_DIR / ".env"
PROJECT_MARKER = "pyproject.toml"
MAX_ROOT_SEARCH_DEPTH = 10


class ConfigError(RuntimeError):
    pass


def find_project_root(
    start: Optional[Path] = None,
    marker: str = PROJECT_MARKER,
    max_depth: int = MAX_ROOT_SEARCH_DEPTH,
) -> Path:
    """Ищет каталог с pyproject.toml вверх от start. PROJECT_ROOT имеет приоритет (нужно в Docker)."""
    override = os.getenv("PROJECT_ROOT")
    if override:
        root = Path(override).resolve()
        if not root.is_dir():
            raise ConfigError(f"PROJECT_ROOT указывает на несуществующий каталог: {root}")
        return root

    current = (start or PACKAGE_DIR).resolve()
    for _ in range(max_depth):
        if (current / marker).exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    raise ConfigError(
        f"Не найден {marker} выше {start or PACKAGE_DIR}. "
        f"Задайте переменную окружения PROJECT_ROOT явно."
    )


def env_str(name: str, default: Optional[str] = None, *, required: bool = False) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        if required:
            raise ConfigError(f"Обязательная переменная окружения {name} не задана.")
        return default
    return value


def env_int(name: str, default: Optional[int] = None, *, required: bool = False) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or raw == "":
        if required:
            raise ConfigError(f"Обязательная переменная окружения {name} не задана.")
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"Переменная окружения {name} должна быть целым числом, получено: {raw!r}"
        ) from exc


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# Уже заданные переменные окружения не перезаписываются
load_dotenv(ENV_FILE)

BASE_DIR: Path = find_project_root()
CERT_PATH = os.path.join(BASE_DIR, "certs", "server.crt")
KEY_PATH = os.path.join(BASE_DIR, "certs", "server.key")


def resolve_project_path(raw: str) -> Path:
    """Относительный путь считается от корня проекта, абсолютный возвращается как есть."""
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else (BASE_DIR / candidate).resolve()


# Аудио
SAMPLE_RATE: int = env_int("SAMPLE_RATE", required=True)
TOP_DB: int = env_int("TOP_DB", required=True)

# Секреты и модели
ENCRYPTION_KEY = env_str("ENCRYPTION_KEY")
_raw_vosk_model_path = env_str("VOSK_MODEL_PATH")
VOSK_MODEL_PATH: Optional[str] = (
    str(resolve_project_path(_raw_vosk_model_path)) if _raw_vosk_model_path else None
)

# NLU-сервис
NLU_MODE = env_str("NLU_MODE", default="both")
API_HOST = env_str("API_HOST", default="localhost")
PORT: int = env_int("PORT", required=True)

# Поведение ассистента
WAKE_WORD = env_str("WAKE_WORD", default="ассистент")
IGNORE_WHEN_SPEAKING = env_bool("IGNORE_WHEN_SPEAKING")
IGNORE_UNAUTHORIZED = env_bool("IGNORE_UNAUTHORIZED")
INTERRUPT_TTS = env_bool("INTERRUPT_TTS")
