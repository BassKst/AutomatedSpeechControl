# Runtime image for the NLU microservice (src/nlu_server).
#
# Build:  docker build -t asc-nlu .
# Run:    docker run --rm -p 8000:8000 -v "$PWD/certs:/app/certs:ro" \
#             -e NLU_MODE=nlu asc-nlu
# Or use the compose file:  docker compose up nlu
#
# TLS certificates are NOT baked into the image (.dockerignore excludes certs/).
# They are mounted read-only at /app/certs - deliberately the same location
# common/config.py computes for CERT_PATH (BASE_DIR/certs/server.crt), so the
# `verify=CERT_PATH` used by assistant_core/nlu_client.py resolves identically
# inside and outside the container.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy metadata first so dependency installation is cached across source edits.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[nlu]"

# PROJECT_ROOT is mandatory here. `pip install` copies the packages into
# site-packages, so common/config.py would otherwise walk up from
# /usr/local/lib/python3.11/site-packages/common/, never find pyproject.toml
# and raise ConfigError at import time - the container could not start at all.
#
# The remaining variables are read at import time by common/config.py and the
# ones marked required have no default, so each needs a container value.
# Override at runtime as needed.
#
# ENCRYPTION_KEY is intentionally absent: nlu_server never imports
# common.encryption_service, and secrets must not be baked into an image.
ENV PROJECT_ROOT=/app \
    NLU_MODE=nlu \
    API_HOST=0.0.0.0 \
    PORT=8000 \
    SAMPLE_RATE=16000 \
    TOP_DB=10 \
    WAKE_WORD=ассистент \
    VOSK_MODEL_PATH=models/vosk-model-small-ru-0.22

EXPOSE 8000

# Run unprivileged: the service only needs to read /app and /app/certs.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# The certificate is self-signed, so it fails the default trust check. The
# healthcheck probes service availability, not the certificate chain (that is
# the client's job via verify=CERT_PATH), hence the unverified context.
# An unhandled exception exits non-zero, which Docker already reads as failure.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import ssl, sys, urllib.request as u; ctx = ssl._create_unverified_context(); r = u.urlopen('https://127.0.0.1:8000/docs', timeout=4, context=ctx); sys.exit(0 if r.status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "nlu_server.server:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--ssl-keyfile", "/app/certs/server.key", \
     "--ssl-certfile", "/app/certs/server.crt"]
