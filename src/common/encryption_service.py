# common/encryption_service.py
import json
import secrets
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

from common.config import ENCRYPTION_KEY, ConfigError

_GENERATE_KEY_HINT = (
    'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
)


def _build_cipher_suite(key: Optional[str]) -> Fernet:
    """Строит ``Fernet`` из ``ENCRYPTION_KEY`` с понятной диагностикой.

    Без этой проверки отсутствие ключа давало
    ``AttributeError: 'NoneType' object has no attribute 'encode'``, а неверный
    формат - неочевидный ``ValueError`` из недр cryptography. Обе ситуации
    теперь сообщают, какую именно команду выполнить.
    """
    if not key:
        raise ConfigError(
            "ENCRYPTION_KEY не задана. Сгенерируйте ключ Fernet командой:\n"
            f"    {_GENERATE_KEY_HINT}"
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise ConfigError(
            "ENCRYPTION_KEY не является корректным ключом Fernet: требуются "
            "32 url-safe base64-байта. Сгенерируйте ключ командой:\n"
            f"    {_GENERATE_KEY_HINT}"
        ) from exc


cipher_suite = _build_cipher_suite(ENCRYPTION_KEY)


def generate_secret_key() -> str:
    """Генерирует высокоэнтропийный секрет в виде 64 шестнадцатеричных символов.

    Назначение - секреты **внешних** систем, а не ``ENCRYPTION_KEY``.
    Единственный потребитель сейчас: ``integrations/plugins/deploy_node.py``,
    где значение уходит в Ansible как ``secret_key`` и рендерится в
    ``SECRET_KEY`` файла ``node.env`` VPN-узла (XRay/Remnawave).

    .. warning::
        Результат НЕ является валидным ключом Fernet: Fernet требует
        32 url-safe base64-байта, а здесь 64 hex-символа. Для
        ``ENCRYPTION_KEY`` используйте :func:`generate_fernet_key`.
    """
    return secrets.token_hex(32)


def generate_fernet_key() -> str:
    """Генерирует ключ, пригодный для переменной окружения ``ENCRYPTION_KEY``.

    Эквивалент однострочника из README::

        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    Функция добавлена, чтобы разделить два разных назначения: секрет VPN-узла
    (hex, см. :func:`generate_secret_key`) и ключ шифрования биометрии
    (url-safe base64). Раньше существовала только первая, и её результат
    нельзя было передать в ``Fernet(...)`` без ``ValueError``.
    """
    return Fernet.generate_key().decode("ascii")


def encrypt_data(data: str) -> str:
    """Шифрует строку."""
    if not data:
        return ""
    return cipher_suite.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Расшифровывает строку."""
    if not encrypted_data:
        return ""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()


def encrypt_json(data: Dict[str, Any]) -> str:
    """Шифрует словарь."""
    if not data:
        return ""
    return encrypt_data(json.dumps(data, ensure_ascii=False))


def decrypt_json(encrypted_data: str) -> Dict[str, Any]:
    """Расшифровывает словарь."""
    if not encrypted_data:
        return {}
    return json.loads(decrypt_data(encrypted_data))


def encrypt_list(data: List[float]) -> str:
    """Шифрует список чисел."""
    if not data:
        return ""
    return encrypt_data(json.dumps(data))


def decrypt_list(encrypted_data: str) -> list:
    if not encrypted_data:
        return []

    decrypted = decrypt_data(encrypted_data)

    try:
        data = json.loads(decrypted)
    except json.JSONDecodeError:
        # если вдруг это строка вида "[0.1, 0.2]"
        data = json.loads(decrypted.strip())

    # если после загрузки всё ещё строка — грузим ещё раз
    if isinstance(data, str):
        data = json.loads(data)

    return [float(x) for x in data]
