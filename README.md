# AutomatedSpeechControl

Voice-controlled infrastructure assistant. Speak a command, and the system
identifies **who** is speaking by voice, resolves **what** they want with a
two-tier NLU pipeline, checks **whether they are allowed** to do it, and then
provisions real infrastructure through Terraform and Ansible — announcing the
result back by synthesised speech.

[![CI](https://github.com/BassKst/AutomatedSpeechControl/actions/workflows/ci.yml/badge.svg)](https://github.com/BassKst/AutomatedSpeechControl/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Highlights

- **Hexagonal architecture.** The application core knows nothing about
  microphones, Telegram, or HTTP. Everything touches the core through the
  `IAssistantChannel` port and the `BaseIntegration` plugin contract.
- **Voice biometrics with RBAC.** Speakers are identified by a Resemblyzer
  embedding; the matched user's role carries an `access_level` that is compared
  against the level each integration requires.
- **Encrypted biometric storage.** Voice embeddings are Fernet-encrypted at
  rest and decrypted only into an in-memory cache.
- **Two-tier NLU.** Fast deterministic fuzzy matching (rapidfuzz) with an
  optional Ollama/LLM fallback for phrasings the corpus does not cover.
- **Plugin auto-discovery.** Drop a `BaseIntegration` subclass into
  `integrations/plugins/` and it is registered, exposed to the NLU schema, and
  access-controlled automatically.
- **Real deployment automation.** The `deploy_node` plugin drives
  `terraform apply` against Hetzner Cloud and configures the resulting VM with
  an Ansible playbook.
- **TLS between services.** The assistant talks to the NLU microservice over
  HTTPS with certificate verification.

## How a request flows

```
speech -> Vosk ASR -> wake-word filter -> VoiceAuthenticator (who?)
       -> NLU service (what?) -> RBAC check (allowed?)
       -> Integration plugin (do it) -> LogParser (explain failures)
       -> Silero TTS (speak the result) -> ExecutionLog (audit trail)
```

Long-running integrations are dispatched to a `ThreadPoolExecutor` so the
assistant keeps listening while Terraform works.

## Architecture

```
+-------------------------------------------------------------------+
|                          Driving adapters                         |
|   LocalAudioChannel (mic + speakers)    TelegramChannel (scaffold)|
+---------------------------------+---------------------------------+
                                  |  IAssistantChannel  (port)
                                  |  listen/reply/interrupt/close
+---------------------------------v---------------------------------+
|                     AssistantApplication  (core)                  |
|                                                                   |
|  1. VoiceAuthenticator   speaker ID -> user + access_level        |
|  2. nlu_client           HTTPS -> nlu_server (intent, entities)   |
|  3. IntegrationManager   plugin registry + RBAC gate              |
|  4. LogParser            raw log -> short spoken diagnosis        |
|  5. db_service           ExecutionLog audit trail                 |
+------------+-----------------------------------+------------------+
             |                                   |
+------------v--------------+   +----------------v------------------+
|      Driven adapters      |   |      Integrations (plugins)       |
|  ASREngine      (Vosk)    |   |  check_load    deploy_node        |
|  TTSEngine      (Silero)  |   +----------------+------------------+
|  encryption_service       |                    | subprocess
|  audio_utils    (librosa) |   +----------------v------------------+
+---------------------------+   | Terraform (Hetzner) -> Ansible    |
                                | -> VPN node (Remnawave + Docker)  |
                                +-----------------------------------+
```

### Module map

| Path | Responsibility |
| --- | --- |
| `main.py` | Composition root — wires engines, channel and core by hand |
| `src/assistant_core/` | Application core: orchestration, ASR, TTS, NLU client, biometrics, log analysis |
| `src/assistant_core/interfaces.py` | The `IAssistantChannel` port and the `UserRequest` DTO |
| `src/assistant_core/integrations/` | Plugin base class, registry, entity corpora, plugins |
| `src/assistant_core/database/` | SQLAlchemy models and the persistence service |
| `src/channels/` | Driving adapters (local audio; Telegram is a scaffold) |
| `src/common/` | Cross-cutting config, logging, encryption, audio helpers |
| `src/nlu_server/` | Standalone FastAPI NLU microservice (fuzzy + Ollama) |
| `src/voice_biometrics/` | Interactive CLI for enrolling users and roles |
| `alembic/` | Database migrations |
| `scripts/` | Operational helpers (e.g. Vosk model download) |
| `tests/` | Pytest suite |

## Security model

| Concern | Approach |
| --- | --- |
| Speaker authentication | Cosine similarity between a live Resemblyzer embedding and encrypted stored profiles, with a configurable threshold |
| Authorisation | Role-based `access_level` compared against each integration's required level before execution |
| Biometrics at rest | Fernet symmetric encryption (`common/encryption_service.py`); embeddings never stored in plaintext |
| Service transport | HTTPS with explicit certificate verification (`verify=CERT_PATH`) |
| Secrets | `.env` is gitignored; only `.env.example` is committed. The whole `certs/` directory is gitignored as well, and both files are produced locally by `generate_certs.py` |
| Audit | Every request is written to `execution_logs` with user, transcript, entities, intent, status and response |

See [Known limitations](#known-limitations--roadmap) for an honest list of what
is **not** yet hardened — notably that the NLU endpoint has no authentication
of its own and that biometric matching has no liveness/anti-spoofing check.

## Getting started

### Prerequisites

- **Python 3.11+**
- **PortAudio** headers, required to build `PyAudio`:
  - Debian/Ubuntu: `sudo apt-get install portaudio19-dev python3-pyaudio`
  - macOS: `brew install portaudio`
  - Windows: wheels are published on PyPI, no extra steps
- **ffmpeg** (used by `librosa`/`soundfile` for some formats)
- Optional, only for the LLM NLU fallback: **[Ollama](https://ollama.com)** with
  `ollama pull llama3.1:8b`
- Optional, only for the `deploy_node` plugin: **Terraform** and **Ansible**

### Installation

```bash
git clone https://github.com/BassKst/AutomatedSpeechControl.git
cd AutomatedSpeechControl

python -m venv .venv
# Windows:  .venv\Scripts\activate
source .venv/bin/activate

# Core + tests only (fast; no torch/vosk/librosa):
pip install -e ".[dev]"

# Full local stack (audio pipeline + NLU service + enrollment CLI):
pip install -e ".[all]"
```

The dependency extras keep the install small for the common cases:

| Extra | Installs | Needed for |
| --- | --- | --- |
| *(none)* | dotenv, SQLAlchemy, alembic, cryptography, requests, numpy, scipy | Core, migrations, tests |
| `audio` | vosk, PyAudio, sounddevice, soundfile, librosa, torch, Resemblyzer | Running the local voice assistant |
| `nlu` | fastapi, uvicorn, rapidfuzz, psutil | Running the NLU microservice |
| `enrollment` | pyperclip | The voice-enrollment CLI |
| `scheduler` | APScheduler | `common/scheduler.py` |
| `dev` | pytest, ruff, black | Tests and linting |
| `all` | everything above except `dev` | Full local stack |

### Configure the environment

```bash
cp src/common/.env.example src/common/.env
```

Generate a Fernet key for `ENCRYPTION_KEY` (this is **not** the same thing as a
hex token):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

| Variable | Example | Purpose |
| --- | --- | --- |
| `ENCRYPTION_KEY` | *(Fernet key)* | Encrypts voice embeddings at rest |
| `WAKE_WORD` | `ассистент` | Phrase that must precede a command |
| `SAMPLE_RATE` | `16000` | Audio sample rate shared by ASR and biometrics |
| `TOP_DB` | `10` | Silence-trim threshold (dB) |
| `VOSK_MODEL_PATH` | `models/vosk-model-small-ru-0.22` | Acoustic model location |
| `NLU_MODE` | `nlu` \| `llama` \| `both` | Fuzzy only, LLM only, or fuzzy-then-LLM |
| `API_HOST` / `PORT` | `localhost` / `8000` | NLU service address (must match the TLS cert) |
| `IGNORE_WHEN_SPEAKING` | `False` | Deaf mode while TTS is playing |
| `IGNORE_UNAUTHORIZED` | `False` | Reject unidentified speakers outright |
| `INTERRUPT_TTS` | `True` | Allow barge-in to stop speech |

### Download the acoustic model

Models are not committed to git:

```bash
python scripts/download_vosk_model.py
```

### Generate TLS certificates

```bash
python generate_certs.py     # writes certs/server.key and certs/server.crt
```

The generated certificate is self-signed for `localhost`, so `API_HOST` must be
`localhost` for certificate verification to succeed.

### Create the database schema

```bash
alembic upgrade head
```

### Enroll a voice profile

Roles and users are managed through an interactive CLI:

```bash
python -m voice_biometrics.main
```

Create a role first (its `access_level` gates integrations), then create a user
and record three phrases to build their embedding.

### Run

Start the NLU service, then the assistant:

```bash
python src/nlu_server/server.py     # terminal 1
python main.py                      # terminal 2
```

Say the wake word followed by a command, for example
*«ассистент, проверь нагрузку на сервер два в германии»*.
Say **«стоп»**, **«отмена»** or **«отключись»** to shut down.

## Writing your own integration

Create a file in `src/assistant_core/integrations/plugins/` and subclass
`BaseIntegration`. Discovery, NLU-schema registration and access control are
automatic — no registry edits required.

```python
from assistant_core.integrations.base import BaseIntegration
from assistant_core.integrations.entity_corpus import Corpus, EntityCorpus


class RestartServiceIntegration(BaseIntegration):
    @property
    def intent_name(self) -> str:
        return "restart_service"          # must be unique across plugins

    @property
    def intent_corpus(self) -> list[str]:
        return ["перезапусти сервис", "рестартни службу"]

    @property
    def entity_corpus(self) -> list[Corpus]:
        return [EntityCorpus.region]

    @property
    def is_long_running(self) -> bool:
        return True                       # dispatched to a worker thread

    @property
    def access_level(self) -> int:
        return 10                         # required RBAC level

    def execute(self, entities: dict, context: dict) -> dict:
        return {"status": "success", "message": "Сервис перезапущен"}
```

Returning `{"status": "error", "raw_log": "..."}` routes `raw_log` through
`LogParser`, which converts raw SSH/API output into a short spoken diagnosis.

## Deployment automation

The `deploy_node` plugin shells out to the manifests under
`src/assistant_core/integrations/automation/`:

1. **Terraform** (`terraform/`) provisions a Hetzner Cloud server from `region`
   and `node_name`, exported as `TF_VAR_*`.
2. **Ansible** (`ansible/deploy_node.yml`) installs Docker, renders a Remnawave
   node compose file and environment, and applies UFW rules.

`hcloud_token` is a sensitive Terraform variable and is not stored in the
repository; supply it as `TF_VAR_hcloud_token` or via a backend.

## Development

### Tests

```bash
pip install -e ".[dev]"
pytest                 # 145 tests
pytest -k log_parser   # single area
```

The suite targets dependency-light, deterministic modules (configuration
loading, log analysis, entity corpora, port contracts, plugin base class,
encryption round-trips) so it runs in about a second without audio hardware or
ML models. `tests/conftest.py` injects a throwaway `ENCRYPTION_KEY` before any
project import, so tests never touch your real key.

### Linting and formatting

```bash
ruff check .          # gated in CI
ruff check . --fix    # apply safe fixes
black .               # formatter (configured, not yet CI-gated)
```

Ruff uses a correctness-focused rule set (`E, W, F, B, C4, SIM, RUF`).
Import-sorting (`I`) and pyupgrade (`UP`) are deliberately disabled for now:
enabling them reformats every file and belongs in a dedicated commit.
`RUF001-003` are disabled because the codebase is intentionally
Russian-language and those rules flag every Cyrillic look-alike character.

The same ruff run plus a few repository-hygiene checks are available as
pre-commit hooks:

```bash
pip install pre-commit
pre-commit install            # run automatically on every commit
pre-commit run --all-files    # run on demand
```

`check-added-large-files` and `detect-private-key` are the two that matter
here: they stop an accidentally committed Vosk model or TLS private key before
it reaches the remote. `black` is intentionally **not** a hook yet - the
codebase is not formatted with it, so adding it would produce a repo-wide diff
(roadmap item 4).

### Continuous integration

`.github/workflows/ci.yml` runs four jobs on every push to `main` and on every
pull request:

| Job | What it does |
| --- | --- |
| `lint` | `ruff check .` |
| `test` | `pytest` on Python 3.11, 3.12 and 3.13 |
| `package` | builds wheel + sdist and asserts all five `src/` packages are present |
| `docker` | builds the NLU image, generates throwaway certificates, starts the container and waits for a TLS response on `/docs` |

The `package` job guards against the regression where `src/` subpackages
without `__init__.py` were silently dropped from the wheel; the `docker` job
catches startup failures that neither unit tests nor the build can see.

### Docker

The NLU microservice ships with a `Dockerfile` and a `docker-compose.yaml`:

```bash
python generate_certs.py      # once - the image contains no certificates
docker compose up --build nlu # build and run
docker compose logs -f nlu    # follow the logs
docker compose down           # stop
```

Plain Docker works too:

```bash
docker build -t asc-nlu .
docker run --rm -p 8000:8000 -v "$PWD/certs:/app/certs:ro" -e NLU_MODE=nlu asc-nlu
```

Certificates are never baked into the image (`.dockerignore` excludes `certs/`);
they are mounted read-only at `/app/certs`, which is exactly where
`common/config.py` looks for `CERT_PATH`, so the path resolves identically
inside and outside the container. The image runs as a non-root user and has a
`HEALTHCHECK` that probes `/docs` over TLS.

The assistant itself (`main.py`) is deliberately **not** containerised: it needs
a microphone, speakers and the Vosk model, so it runs on the host and talks to
the service at `https://localhost:8000`.

## Project layout

```
.
├── main.py                     # composition root
├── generate_certs.py           # self-signed TLS cert generator
├── pyproject.toml              # metadata, dependencies, pytest/ruff/black config
├── Dockerfile                  # NLU microservice image
├── docker-compose.yaml         # local run for the NLU service
├── CHANGELOG.md                # release notes
├── alembic.ini  alembic/       # migrations
├── .github/workflows/ci.yml    # lint, test matrix, wheel check, docker smoke test
├── .pre-commit-config.yaml     # ruff + repo hygiene hooks
├── certs/                      # TLS material (gitignored, generated locally)
├── models/                     # Vosk models (gitignored, see scripts/)
├── scripts/                    # operational helpers
├── tests/                      # pytest suite
└── src/
    ├── assistant_core/         # application core
    │   ├── database/           # SQLAlchemy models + persistence
    │   └── integrations/       # plugin framework + automation manifests
    ├── channels/               # driving adapters
    ├── common/                 # config, logging, encryption, audio
    ├── nlu_server/             # FastAPI NLU microservice
    └── voice_biometrics/       # enrollment CLI
```

## Known limitations & roadmap

This is a working portfolio project, not a production system. The gaps below
are documented deliberately rather than hidden. Items that have since been
fixed are tracked in the [CHANGELOG](CHANGELOG.md).

**Correctness**
- The `deploy_node` path has never been exercised end-to-end. Entity validation
  tests key *presence* instead of truthiness, so a missing `region` reaches
  `None.lower()`; corpus region codes (`NL`, `DE`) do not match hcloud location
  names (`nbg1`, `fsn1`); Terraform does not expand `~/.ssh/id_rsa.pub`; and no
  `subprocess.run` call has a timeout.
- `TelegramChannel` is a scaffold, not a working adapter: it satisfies the
  `IAssistantChannel` contract and can be instantiated, but there is no
  `python-telegram-bot` client, bot token or message queue behind it.
- `voice_biometrics` leaks DB sessions (`get_session()` hands out a session
  nobody closes).
- Entity extraction scores short synonyms against the whole utterance with
  `partial_ratio`, so `"раз"` (number 1) matches inside `"разверни"`.

**Security**
- The NLU `/call` endpoint has no authentication and binds `0.0.0.0`.
- The Ansible `secret_key` is passed on the command line (visible in `ps`) and
  rendered into a world-readable `.env` on the target host.
- Entity values from the LLM path are not validated against the corpus
  whitelist before reaching Jinja templates.
- Biometric matching has no liveness or anti-spoofing check.
- `generate_certs.py` writes the private key unencrypted. Permissions are now
  restricted to `0600`, but there is no passphrase protection. On Windows
  `os.chmod` only toggles the read-only bit, so real protection there depends
  on the directory ACL.

**Architecture**
- `assistant_core/__init__.py` eagerly imports the SQLAlchemy `Base`, coupling
  even pure-logic modules to the database stack.
- `common/scheduler.py` is unused, depends on `apscheduler`, and dispatches via
  `locals()`.
- The `Command` and `Settings` models are unused; RBAC levels live in plugin
  code, duplicating the `commands` table.
- Logging is configured as an import side effect, clears existing root
  handlers, and emits raw ANSI codes unconditionally.
- `alembic/env.py` still appends `os.getcwd()` to `sys.path` even though
  `alembic.ini` already sets `prepend_sys_path = .`; the redundant hack is what
  forces the `E402` ruff exclusion.

**Planned next**
1. Fix the crash-level defects in the `deploy_node` path (validation,
   region-code mapping, subprocess timeouts).
2. Harden the security items above; authenticate the NLU service.
3. Extend test coverage to the NLU engine, plugin manager and database layer.
4. Enable ruff `I`/`UP`, format the codebase with `black` and gate both in CI.
5. Implement or remove the Telegram channel; wire up or archive the scheduler.
6. Add Terraform remote state with locking.
7. Record a short demo (voice command -> provisioned node) for the README.

## License

[MIT](LICENSE)
