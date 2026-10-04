"""Общая конфигурация pytest для проекта AutomatedSpeechControl.

conftest выполняет две задачи.

1. Гарантирует, что каталог ``src`` доступен для импорта даже тогда, когда
   pytest запускается способом, не учитывающим ``pythonpath`` из
   ``pyproject.toml`` (например, запуск одного файла из IDE).

2. Подставляет одноразовый тестовый ``ENCRYPTION_KEY`` ДО первого импорта
   кода проекта. ``common.config`` вызывает ``load_dotenv()`` без
   ``override=True``, поэтому значение, уже присутствующее в ``os.environ``,
   не будет перезаписано значением из ``src/common/.env``.

   Следствие: тесты никогда не используют и не раскрывают боевой ключ
   шифрования разработчика, а ``common.encryption_service`` строит
   ``cipher_suite`` из заведомо тестового ключа.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from cryptography.fernet import Fernet
except ImportError:  # pragma: no cover - cryptography отсутствует в окружении
    pass
else:
    # Важно: присваивание должно произойти до импорта common.config.
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")
