# Changelog

Все значимые изменения проекта документируются здесь.
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added

- `docker-compose.yaml` для локального запуска NLU-микросервиса.
- `.gitattributes`: нормализация переводов строк и явная маркировка бинарных
  файлов (аудио, изображения, БД). Индекс уже хранился в LF, поэтому правило
  не меняет содержимое, а лишь фиксирует поведение для CI и других ОС.
- `.pre-commit-config.yaml`: ruff и немодифицирующие проверки
  (`check-added-large-files`, `detect-private-key`, `check-toml`, `check-yaml`).
- `common.encryption_service.generate_fernet_key()` - генератор ключа,
  пригодного для `ENCRYPTION_KEY` (32 url-safe base64-байта).
- `.gitignore`: добавлены `models/`, `certs/`, `*.crt`, `*.cer`, `*.der`,
  `*.egg`, `.tox/`, `.python-version`, `.venv*/`.
- Метаданные пакета: `authors`, `keywords`, `classifiers`, `[project.urls]`.

### Changed

- Дистрибутив переименован `diplom_speech_helper` -> `automated_speech_control`
  в соответствии с именем репозитория. Каталоги пакетов в `src/` не изменились.
- `Dockerfile`: сертификаты монтируются в `/app/certs` вместо `/certs`, чтобы
  путь совпадал с `config.CERT_PATH` (`BASE_DIR/certs/server.crt`).
- `generate_secret_key()` задокументирована как генератор секрета для внешних
  систем (VPN-узел), а не ключа шифрования.

### Fixed

- `Dockerfile`: добавлен `PROJECT_ROOT=/app`. Без него `common/config.py`
  искал `pyproject.toml` обходом вверх от `site-packages/common/`, не находил
  и бросал `ConfigError` при импорте - контейнер не запускался вовсе.
- `Dockerfile`: `HEALTHCHECK` обращался к `https://127.0.0.1:8000/docs` со
  строгой проверкой сертификата. Самоподписанный сертификат всегда давал
  `CERTIFICATE_VERIFY_FAILED`, поэтому контейнер был перманентно `unhealthy`.
  Проверка переведена на контекст без верификации цепочки доверия.
- `nlu_server/ollama_engine.py`: флаг `CREATE_NEW_PROCESS_GROUP` существует
  только в Windows и на Linux/macOS ронял запуск Ollama с `AttributeError`.
  Флаг теперь применяется условно по `sys.platform`.
- `channels/telegram_channel.py`: добавлен недостающий `close()`, из-за которого
  ABC не позволял инстанцировать канал. Строковый литерал, стоявший после
  импорта и не являвшийся docstring, перемещён в начало модуля.
- `generate_certs.py`: приватный ключ теперь записывается с правами `0600`.
- `voice_biometrics/main.py`: скриптовый импорт `from voice_utils import ...`
  заменён на пакетный `from voice_biometrics.voice_utils import ...`. Костыль
  `PYTHONPATH=src:src/voice_biometrics` больше не нужен.
- Удалены временные файлы `_diag.txt`, `_fix.txt`, `_v.txt`, `_verify.txt`
  и локальные кэши (`.pytest_cache`, `.ruff_cache`, `*.egg-info`, `cache/`).
- `certs/server.crt` исключён из отслеживания git: оба файла сертификата
  генерируются локально и не должны храниться в репозитории.

## [0.1.0] - 2026-10-04

### Added

- Первый снимок проекта: ядро ассистента (ASR на Vosk, TTS на Silero,
  голосовая биометрия на Resemblyzer с шифрованием эмбеддингов),
  NLU-микросервис на FastAPI (rapidfuzz + Ollama), плагин-фреймворк
  интеграций с RBAC, миграции Alembic, автоматизация деплоя
  на Terraform (Hetzner Cloud) и Ansible.
- Набор тестов на независимых от железа модулях и `AGENTS.md`.

[Unreleased]: https://github.com/BassKst/AutomatedSpeechControl/commits/main
[0.1.0]: https://github.com/BassKst/AutomatedSpeechControl/releases/tag/v0.1.0
