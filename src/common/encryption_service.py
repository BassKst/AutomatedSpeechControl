# common/encryption_service.py
import json
import secrets
from typing import List, Dict, Any

from cryptography.fernet import Fernet

from common.config import ENCRYPTION_KEY

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def generate_secret_key() -> str:
    return secrets.token_hex(32)

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
