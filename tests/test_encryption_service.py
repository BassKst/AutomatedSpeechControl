import json
import string

import pytest
from cryptography.fernet import Fernet, InvalidToken

from common.encryption_service import (
    decrypt_data,
    decrypt_json,
    decrypt_list,
    encrypt_data,
    encrypt_json,
    encrypt_list,
    generate_fernet_key,
    generate_secret_key,
)


def test_encrypt_decrypt_roundtrip_ascii():
    assert decrypt_data(encrypt_data("hello world")) == "hello world"


def test_encrypt_decrypt_roundtrip_cyrillic():
    original = "Разверни узел в Нидерландах"
    assert decrypt_data(encrypt_data(original)) == original


def test_ciphertext_differs_from_plaintext():
    ciphertext = encrypt_data("secret value")

    assert "secret value" not in ciphertext


def test_ciphertext_is_non_deterministic():
    assert encrypt_data("same input") != encrypt_data("same input")


@pytest.mark.parametrize(
    ("encrypt", "decrypt", "empty"),
    [
        (encrypt_data, decrypt_data, ""),
        (encrypt_json, decrypt_json, ""),
        (encrypt_list, decrypt_list, ""),
    ],
)
def test_empty_input_short_circuits(encrypt, decrypt, empty):
    assert encrypt(empty) == ""
    assert decrypt("") in ("", {}, [])


def test_encrypt_json_roundtrip():
    payload = {"region": "NL", "number": 2, "note": "узел в Нидерландах"}

    assert decrypt_json(encrypt_json(payload)) == payload


def test_encrypt_json_preserves_unicode_without_escaping():
    ciphertext = encrypt_json({"city": "амстердам"})

    raw = json.dumps({"city": "амстердам"}, ensure_ascii=False)
    assert decrypt_data(ciphertext) == raw


def test_encrypt_json_nested_structures():
    payload = {"a": [1, 2, {"b": None}], "c": {"d": True}}

    assert decrypt_json(encrypt_json(payload)) == payload


def test_encrypt_list_roundtrip():
    embedding = [0.123456, -0.987654, 0.0]

    assert decrypt_list(encrypt_list(embedding)) == embedding


def test_decrypt_list_coerces_to_float():
    result = decrypt_list(encrypt_list([1, 2, 3]))

    assert result == [1.0, 2.0, 3.0]
    assert all(isinstance(x, float) for x in result)


def test_decrypt_list_handles_double_encoded_json():
    double_encoded = encrypt_data(json.dumps(json.dumps([1.5, 2.5])))

    assert decrypt_list(double_encoded) == [1.5, 2.5]


def test_decrypt_data_rejects_foreign_ciphertext():
    other_cipher = Fernet(Fernet.generate_key())
    foreign_token = other_cipher.encrypt(b"secret").decode()

    with pytest.raises(InvalidToken):
        decrypt_data(foreign_token)


def test_decrypt_data_rejects_garbage():
    with pytest.raises(InvalidToken):
        decrypt_data("not-a-valid-token")


def test_generate_secret_key_format():
    key = generate_secret_key()

    assert len(key) == 64
    assert all(c in string.hexdigits for c in key)


def test_generate_secret_key_is_unique():
    assert generate_secret_key() != generate_secret_key()


def test_generate_secret_key_is_not_a_fernet_key():
    with pytest.raises(ValueError):
        Fernet(generate_secret_key().encode())


def test_generate_fernet_key_is_accepted_by_fernet():
    key = generate_fernet_key()

    cipher = Fernet(key.encode())
    assert cipher.decrypt(cipher.encrypt(b"payload")) == b"payload"


def test_generate_fernet_key_format():
    key = generate_fernet_key()

    # 32 байта в base64 = 44 символа
    assert len(key) == 44
    assert key.endswith("=")
    assert all(c in string.ascii_letters + string.digits + "-_=" for c in key)


def test_generate_fernet_key_is_unique():
    assert generate_fernet_key() != generate_fernet_key()


def test_generate_fernet_key_differs_from_secret_key():
    assert len(generate_fernet_key()) != len(generate_secret_key())
