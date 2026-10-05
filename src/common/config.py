"""Централизованная конфигурация приложения.

Значения читаются из переменных окружения и из файла ``src/common/.env``.
Путь к ``.env`` вычисляется явно, поэтому результат больше не зависит от
способа запуска процесса (``python main.py``, ``python -m pytest``,
``python -c``) - раньше ``load_dotenv()`` без аргумента искал файл обходом
кадров стека и в некоторых режимах запуска не находил его вовсе.

Модуль намеренно сохраняет плоский набор констант: их импортируют как
``from common.config import SAMPLE_RATE`` и обращаются к ним как
``common.config.SAMPLE_RATE``.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

#: Каталог пакета ``common`` (``src/common``).
PACKAGE_DIR = Path(__file__).resolve().parent

#: Файл переменных окружения, лежащий рядом с этим модулем.
ENV_FILE = PACKAGE_DIR / ".env"

#: Файл-маркер корня проекта.
PROJECT_MARKER = "pyproject.toml"

#: Ограничение обхода вверх. ``Path.parent`` для корня файловой системы
#: возвращает тот же самый путь, поэтому без ограничения поиск маркера
#: зацикливался навсегда.
MAX_ROOT_SEARCH_DEPTH = 10


class ConfigError(RuntimeError):
    """Переменная окружения не задана, обязательна или имеет неверный формат."""


def find_project_root(
    start: Optional[Path] = None,
    marker: str = PROJECT_MARKER,
    max_depth: int = MAX_ROOT_SEARCH_DEPTH,
) -> Path:
    """Возвращает корень проекта, поднимаясь от ``start`` вверх до ``marker``.

    Результат можно переопределить переменной окружения ``PROJECT_ROOT`` - это
    нужно для контейнеров, где дерево исходников не содержит ``pyproject.toml``.

    :raises ConfigError: если ``PROJECT_ROOT`` указывает на несуществующий
        каталог, либо маркер не найден в пределах ``max_depth`` уровней.
    """
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
        if parent == current:  # достигнут корень файловой системы
            break
        current = parent

    raise ConfigError(
        f"Не найден {marker} выше {start or PACKAGE_DIR}. "
        f"Задайте переменную окружения PROJECT_ROOT явно."
    )


def env_str(name: str, default: Optional[str] = None, *, required: bool = False) -> Optional[str]:
    """Возвращает строковое значение переменной окружения.

    Пустая строка трактуется как отсутствие значения.

    :raises ConfigError: если значение обязательно, но не задано.
    """
    value = os.getenv(name)
    if value is None or value == "":
        if required:
            raise ConfigError(f"Обязательная переменная окружения {name} не задана.")
        return default
    return value


def env_int(name: str, default: Optional[int] = None, *, required: bool = False) -> Optional[int]:
    """Возвращает целочисленное значение переменной окружения.

    :raises ConfigError: если значение обязательно, но не задано, либо задано
        и не является целым числом.
    """
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
    """Интерпретирует значение переменной окружения как булево.

    Истинными считаются ``1``, ``true``, ``yes``, ``on`` без учёта регистра.
    """
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# Файл .env не перезаписывает уже установленные переменные окружения
# (override=False по умолчанию), поэтому контейнер и тесты могут задать
# любое значение извне.
load_dotenv(ENV_FILE)

# --- Пути --------------------------------------------------------------------
BASE_DIR: Path = find_project_root()
CERT_PATH = os.path.join(BASE_DIR, "certs", "server.crt")

# --- Аудио -------------------------------------------------------------------
# Обязательны: без них конвейер ASR/биометрии не имеет смысла.
SAMPLE_RATE: int = env_int("SAMPLE_RATE", required=True)
TOP_DB: int = env_int("TOP_DB", required=True)

# --- Секреты и модели --------------------------------------------------------
ENCRYPTION_KEY = env_str("ENCRYPTION_KEY")
VOSK_MODEL_PATH = env_str("VOSK_MODEL_PATH")

# --- NLU-сервис --------------------------------------------------------------
# Значения по умолчанию совпадают с src/common/.env.example.
NLU_MODE = env_str("NLU_MODE", default="both")
API_HOST = env_str("API_HOST", default="localhost")
PORT: int = env_int("PORT", required=True)

# --- Поведение ассистента ----------------------------------------------------
WAKE_WORD = env_str("WAKE_WORD", default="ассистент")
IGNORE_WHEN_SPEAKING = env_bool("IGNORE_WHEN_SPEAKING")
IGNORE_UNAUTHORIZED = env_bool("IGNORE_UNAUTHORIZED")
INTERRUPT_TTS = env_bool("INTERRUPT_TTS")

