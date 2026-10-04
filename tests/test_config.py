from pathlib import Path

import pytest

from common import config
from common.config import (
    ConfigError,
    env_bool,
    env_int,
    env_str,
    find_project_root,
    resolve_project_path,
)

MISSING = "ASC_TEST_DEFINITELY_UNSET_VARIABLE"


def test_env_str_reads_value(monkeypatch):
    monkeypatch.setenv(MISSING, "значение")
    assert env_str(MISSING) == "значение"


def test_env_str_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv(MISSING, raising=False)
    assert env_str(MISSING, default="fallback") == "fallback"


def test_env_str_treats_empty_as_unset(monkeypatch):
    monkeypatch.setenv(MISSING, "")
    assert env_str(MISSING, default="fallback") == "fallback"


def test_env_str_required_raises_config_error(monkeypatch):
    monkeypatch.delenv(MISSING, raising=False)
    with pytest.raises(ConfigError, match=MISSING):
        env_str(MISSING, required=True)


def test_env_int_parses_value(monkeypatch):
    monkeypatch.setenv(MISSING, "16000")
    assert env_int(MISSING) == 16000


def test_env_int_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv(MISSING, raising=False)
    assert env_int(MISSING, default=8000) == 8000


def test_env_int_required_raises_config_error(monkeypatch):
    monkeypatch.delenv(MISSING, raising=False)
    with pytest.raises(ConfigError, match=MISSING):
        env_int(MISSING, required=True)


def test_env_int_rejects_non_numeric_with_clear_message(monkeypatch):
    monkeypatch.setenv(MISSING, "шестнадцать")
    with pytest.raises(ConfigError) as excinfo:
        env_int(MISSING, required=True)

    message = str(excinfo.value)
    assert MISSING in message
    assert "шестнадцать" in message


def test_env_int_rejects_float_string(monkeypatch):
    monkeypatch.setenv(MISSING, "16000.5")
    with pytest.raises(ConfigError, match=MISSING):
        env_int(MISSING)


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "True", "yes", "YES", "on", " on "])
def test_env_bool_truthy_values(monkeypatch, raw):
    monkeypatch.setenv(MISSING, raw)
    assert env_bool(MISSING) is True


@pytest.mark.parametrize("raw", ["0", "false", "FALSE", "no", "off", "", "anything-else"])
def test_env_bool_falsy_values(monkeypatch, raw):
    monkeypatch.setenv(MISSING, raw)
    assert env_bool(MISSING) is False


def test_env_bool_default_when_unset(monkeypatch):
    monkeypatch.delenv(MISSING, raising=False)
    assert env_bool(MISSING) is False
    assert env_bool(MISSING, default=True) is True


def test_find_project_root_locates_marker(tmp_path, monkeypatch):
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    assert find_project_root(start=nested) == tmp_path.resolve()


def test_find_project_root_is_bounded_and_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    nested = tmp_path / "deep"
    nested.mkdir()

    with pytest.raises(ConfigError, match="PROJECT_ROOT"):
        find_project_root(start=nested, marker="no-such-marker-file.toml", max_depth=3)


def test_find_project_root_stops_at_filesystem_root(tmp_path, monkeypatch):
    monkeypatch.delenv("PROJECT_ROOT", raising=False)

    with pytest.raises(ConfigError):
        find_project_root(
            start=tmp_path, marker="no-such-marker-file.toml", max_depth=10_000
        )


def test_project_root_override_is_honoured(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    assert find_project_root(marker="no-such-marker-file.toml") == tmp_path.resolve()


def test_project_root_override_validates_existence(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path / "does-not-exist"))
    with pytest.raises(ConfigError, match="PROJECT_ROOT"):
        find_project_root()


def test_base_dir_is_the_project_root():
    assert isinstance(config.BASE_DIR, Path)
    assert (config.BASE_DIR / "pyproject.toml").is_file()


def test_cert_path_is_anchored_to_base_dir():
    expected_cert_path = str(config.BASE_DIR / "certs" / "server.crt")
    assert expected_cert_path == config.CERT_PATH


def test_key_path_is_anchored_to_base_dir():
    expected_key_path = str(config.BASE_DIR / "certs" / "server.key")
    assert expected_key_path == config.KEY_PATH


def test_vosk_model_path_is_absolute_when_set():
    if config.VOSK_MODEL_PATH is not None:
        assert Path(config.VOSK_MODEL_PATH).is_absolute()


def test_resolve_project_path_anchors_relative_to_base_dir():
    expected = (config.BASE_DIR / "models" / "test-model").resolve()
    assert resolve_project_path("models/test-model") == expected


def test_resolve_project_path_keeps_absolute_paths():
    absolute = config.BASE_DIR / "models" / "vosk-model-small-ru-0.22"
    assert resolve_project_path(str(absolute)) == absolute.resolve()


def test_numeric_settings_are_ints():
    assert isinstance(config.SAMPLE_RATE, int)
    assert isinstance(config.TOP_DB, int)
    assert isinstance(config.PORT, int)


def test_env_file_path_is_explicit():
    expected_env_file = Path(config.__file__).resolve().parent / ".env"
    assert expected_env_file == config.ENV_FILE
