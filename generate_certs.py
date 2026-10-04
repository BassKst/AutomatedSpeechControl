"""Создаёт самоподписанный сертификат для NLU-сервиса в certs/."""

import datetime
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

PROJECT_ROOT = Path(__file__).resolve().parent
CERTS_DIR = PROJECT_ROOT / "certs"
KEY_FILE = CERTS_DIR / "server.key"
CERT_FILE = CERTS_DIR / "server.crt"


def generate_self_signed_cert():
    print("Генерация RSA ключа...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    print("Создание сертификата для localhost...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        # Сертификат будет годен 1 год
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(KEY_FILE, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Ключ не зашифрован, поэтому доступ только владельцу
    os.chmod(KEY_FILE, 0o600)

    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Успешно! Файлы server.key и server.crt созданы в папке {CERTS_DIR}.")


if __name__ == "__main__":
    generate_self_signed_cert()
