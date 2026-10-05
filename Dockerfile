# NLU-микросервис. Сертификаты монтируются в /app/certs:
#   docker run --rm -p 8000:8000 -v "$PWD/certs:/app/certs:ro" asc-nlu

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[nlu]"

# Пакет установлен в site-packages, поэтому корень проекта задаётся явно
ENV PROJECT_ROOT=/app \
    NLU_MODE=nlu \
    API_HOST=0.0.0.0 \
    PORT=8000 \
    SAMPLE_RATE=16000 \
    TOP_DB=10 \
    WAKE_WORD=ассистент \
    VOSK_MODEL_PATH=models/vosk-model-small-ru-0.22

EXPOSE 8000

RUN useradd --create-home --uid 10001 appuser
USER appuser

# Сертификат самоподписанный, поэтому проверка без верификации цепочки
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import ssl, sys, urllib.request as u; ctx = ssl._create_unverified_context(); r = u.urlopen('https://127.0.0.1:8000/docs', timeout=4, context=ctx); sys.exit(0 if r.status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "nlu_server.server:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--ssl-keyfile", "/app/certs/server.key", \
     "--ssl-certfile", "/app/certs/server.crt"]
