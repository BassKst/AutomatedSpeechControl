"""Тесты модуля анализа системных логов (assistant_core.log_parser).

Формализуют демонстрационный блок ``if __name__ == "__main__"`` из
``log_parser.py`` в виде воспроизводимых проверок и расширяют его
граничными случаями: пустой журнал, неизвестная ошибка, независимость
от регистра, экранирование метасимволов в регулярных выражениях и
приоритет сигнатур при совпадении нескольких семейств.
"""

import logging
import re

import pytest

from assistant_core.log_parser import LogParser

EMPTY_LOG_MESSAGE = "Журнал ошибок пуст."
UNKNOWN_LOG_MESSAGE = (
    "Произошла неизвестная системная ошибка. Рекомендуется ручная проверка логов."
)

FIREWALL = "Ошибка соединения. Порт заблокирован файрволом."
TIMEOUT = "Таймаут операции. Сервер не отвечает."
AUTH = "Ошибка аутентификации. Проверьте SSH ключи."
DISK = "Недостаточно места на диске сервера."
VPN = "Служба VPN не запущена или упала."
MISSING_DATA = "Не предоставлены необходимые данные."

ALL_DIAGNOSES = {FIREWALL, TIMEOUT, AUTH, DISK, VPN, MISSING_DATA}


@pytest.fixture
def parser() -> LogParser:
    return LogParser()


# Каждый элемент - реалистичный фрагмент лога и ожидаемый диагноз.
# Покрыты ВСЕ 18 паттернов из LogParser.error_signatures.
SAMPLE_LOGS = [
    # --- Семейство: файрвол / недоступность порта ---
    ("ssh: connect to host 10.0.0.5 port 22: Connection refused", FIREWALL),
    ("ping: send packet: No route to host", FIREWALL),
    ("kernel: [UFW DROP] IN=eth0 OUT= SRC=10.0.0.1 DST=10.0.0.5", FIREWALL),
    ("iptables: Permission denied. (you must be root)", FIREWALL),
    # --- Семейство: таймаут ---
    ("ssh: connect to host node-1 port 22: Connection timed out", TIMEOUT),
    ("TimeoutError: [Errno 110] Operation timed out", TIMEOUT),
    (
        "requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.example.com', "
        "port=443): Max retries exceeded with url: /deploy",
        TIMEOUT,
    ),
    # --- Семейство: аутентификация ---
    ("root@10.0.0.5: Permission denied (publickey,password).", AUTH),
    ("fatal: Authentication failed for 'https://git.example.com/repo.git/'", AUTH),
    ("Invalid password for user 'deploy'", AUTH),
    # --- Семейство: диск ---
    ("tar: /var/log/app.log: write error: No space left on device", DISK),
    ("cp: cannot create regular file '/opt/app/node': Disk quota exceeded", DISK),
    # --- Семейство: VPN-служба ---
    ("systemd: vpn-service.service: Failed with result 'exit-code'.", VPN),
    (
        "systemd: vpn-service.service: Main process exited, "
        "code=exited, status=1/FAILURE",
        VPN,
    ),
    ("* vpn-service.service - VPN Tunnel\n     Active: failed (Result: exit-code)", VPN),
    # --- Семейство: не предоставлены данные ---
    ("Validation error: NoIP provided for target node", MISSING_DATA),
    ("Validation error: NoRG specified in request payload", MISSING_DATA),
    ("Validation error: NoNB specified in request payload", MISSING_DATA),
]


@pytest.mark.parametrize(("raw_log", "expected"), SAMPLE_LOGS)
def test_known_signature_returns_diagnosis(parser, raw_log, expected):
    assert parser.analyze_error_log(raw_log) == expected


def test_samples_cover_every_signature_family(parser):
    """Страховка от появления новой сигнатуры без теста на неё."""
    assert set(parser.error_signatures) == ALL_DIAGNOSES


def test_samples_cover_every_pattern(parser):
    """Каждый паттерн из error_signatures проверен хотя бы одним сэмплом."""
    covered = {
        (diagnosis, pattern)
        for raw_log, _ in SAMPLE_LOGS
        for diagnosis, patterns in parser.error_signatures.items()
        for pattern in patterns
        if re.search(pattern, raw_log, re.IGNORECASE)
    }
    declared = {
        (diagnosis, pattern)
        for diagnosis, patterns in parser.error_signatures.items()
        for pattern in patterns
    }
    assert declared - covered == set()


def test_empty_log(parser):
    assert parser.analyze_error_log("") == EMPTY_LOG_MESSAGE


def test_whitespace_only_log_is_treated_as_unknown(parser):
    """ХАРАКТЕРИЗАЦИЯ: строка из пробелов непуста, поэтому ветка
    ``if not raw_log`` не срабатывает и возвращается неизвестная ошибка."""
    assert parser.analyze_error_log("   \n\t ") == UNKNOWN_LOG_MESSAGE


def test_unknown_log(parser):
    raw_log = "Error 500: Database synchronization sequence failed at step 4."
    assert parser.analyze_error_log(raw_log) == UNKNOWN_LOG_MESSAGE


@pytest.mark.parametrize(
    "raw_log",
    ["CONNECTION REFUSED", "connection refused", "CoNnEcTiOn ReFuSeD"],
)
def test_matching_is_case_insensitive(parser, raw_log):
    assert parser.analyze_error_log(raw_log) == FIREWALL


def test_multiline_log_is_scanned_entirely(parser):
    raw_log = (
        "May 14 12:00:01 node-de-1 ansible: Starting deployment\n"
        "May 14 12:00:02 node-de-1 kernel: [UFW DROP] IN=eth0\n"
        "May 14 12:00:03 node-de-1 ansible: task failed\n"
    )
    assert parser.analyze_error_log(raw_log) == FIREWALL


def test_first_matching_family_wins(parser):
    """Сигнатуры перебираются в порядке объявления словаря, поэтому лог
    с признаками и файрвола, и таймаута диагностируется как файрвол."""
    raw_log = "Connection refused, later followed by TimeoutError"
    assert parser.analyze_error_log(raw_log) == FIREWALL


def test_escaped_dot_in_vpn_pattern_is_literal(parser):
    r"""Паттерн ``vpn-service\.service: Failed`` требует настоящую точку,
    а не любой символ."""
    raw_log = "systemd: vpn-serviceXservice: Failed with result 'exit-code'."
    assert parser.analyze_error_log(raw_log) == UNKNOWN_LOG_MESSAGE


def test_escaped_paren_in_auth_pattern_is_literal(parser):
    r"""Паттерн ``Permission denied \(publickey`` срабатывает только при
    наличии именно ``publickey``."""
    assert parser.analyze_error_log("Permission denied (password).") == UNKNOWN_LOG_MESSAGE


def test_signature_values_are_tuples_of_str(parser):
    assert parser.error_signatures, "словарь сигнатур не должен быть пустым"
    for diagnosis, patterns in parser.error_signatures.items():
        assert isinstance(diagnosis, str) and diagnosis
        assert isinstance(patterns, tuple) and patterns
        assert all(isinstance(p, str) and p for p in patterns)


def test_diagnosis_is_logged(parser, caplog):
    with caplog.at_level(logging.WARNING, logger="assistant_core.log_parser"):
        parser.analyze_error_log("Connection refused")

    assert "Найдена сигнатура ошибки" in caplog.text


def test_unknown_diagnosis_is_logged(parser, caplog):
    with caplog.at_level(logging.WARNING, logger="assistant_core.log_parser"):
        parser.analyze_error_log("totally unrelated failure")

    assert "Неизвестная ошибка в логе" in caplog.text
