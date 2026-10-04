import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Переменные должны быть заданы до импорта common.config: .env в CI нет,
# а настоящий ключ шифрования в тестах использоваться не должен.
os.environ.setdefault("SAMPLE_RATE", "16000")
os.environ.setdefault("TOP_DB", "10")
os.environ.setdefault("PORT", "8000")

try:
    from cryptography.fernet import Fernet
except ImportError:  # pragma: no cover
    pass
else:
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")
