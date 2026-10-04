import json
import logging
import re
import subprocess
import sys

import psutil
import requests
import time

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — модуль NLU для голосового ассистента.

Твоя задача:
— определить intent
— извлечь entities ТОЛЬКО если они явно присутствуют в тексте
— если сущность не указана пользователем — ставь null

Запрещено:
— угадывать значения
— подставлять значения по умолчанию
— выводить текст вне JSON

Формат ответа СТРОГО:
{
  "intent": string,
  "entities": object,
  "msg": string
}

Правила:
• если intent не найден → "intent": "unknown"
• отсутствующие сущности → null
• msg ВСЕГДА на русском языке
• msg короткий (3–6 слов), в действительном залоге"""


class OLLAMAEngine:
    def __init__(self, model="llama3.1:8b", host="http://localhost:11434"):
        self.model = model
        self.host = host
        self.proc = None

        self._start_server()
        self._wait_until_ready()
        # self._warmup() Пока не нужно

    # ---------- server control ----------

    def _start_server(self):
        # CREATE_NEW_PROCESS_GROUP есть только в Windows
        popen_kwargs = {}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        self.proc = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **popen_kwargs
        )

    def _wait_until_ready(self, timeout=15):
        start = time.time()
        while time.time() - start < timeout:
            try:
                requests.get(f"{self.host}/api/tags", timeout=0.5)
                return
            except Exception:
                time.sleep(0.3)
        raise RuntimeError("Ollama server did not start")

    def _warmup(self, nlu_schema: dict):
        self.generate("hi", nlu_schema)

    # ---------- main API ----------

    def build_prompt(self, text: str, nlu_schema: dict):
        lines = []

        lines.append("INTENTS:")
        for intent, data in nlu_schema.items():
            canonical = data["intent_corpus"][0]
            lines.append(f"{intent}: \"{canonical}\"")

        lines.append("\nENTITIES (все поля обязательны, если нет в тексте — null):")
        for intent, data in nlu_schema.items():
            if not data["entity_corpus"]:
                continue
            lines.append(f"{intent}:")
            for corpus in data["entity_corpus"]:
                keys = list(corpus["data"].keys())
                lines.append(f"  {corpus['name']}: {keys}")

        lines.append("\nUSER TEXT:")

        lines.append(text)

        lines.append("""
Ответь ТОЛЬКО JSON.
Если intent не найден — intent = "unknown".
msg должен быть коротким (3–6 слов).
""")

        return "\n".join(lines)

    def generate(self, text: str, nlu_schema: dict) -> dict:
        logger.info("Generating with text: " + text)
        prompt = self.build_prompt(text, nlu_schema)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "temperature": 0.1
        }

        r = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=120
        )

        r.raise_for_status()

        raw = r.json()["message"]["content"]
        logger.info("Raw result: " + raw)

        result = self.safe_parse_llm_json(raw)
        result = self.normalize_entities(result, nlu_schema)
        result.update({'confidence': '1.0', 'text': text})
        return result

    def safe_parse_llm_json(self, raw: str) -> dict:
        FALLBACK = {
            "intent": "unknown",
            "entities": {},
            "msg": "Команда не распознана"
        }

        try:
            # иногда модель может добавить мусор до/после JSON — вырежем аккуратно
            match = re.search(r"{.*}", raw, re.S)
            if not match:
                return FALLBACK

            cleaned = match.group()

            data = json.loads(cleaned)

            # базовая валидация структуры
            if not isinstance(data, dict):
                return FALLBACK

            if "intent" not in data or "entities" not in data or "msg" not in data:
                return FALLBACK

            if not isinstance(data["entities"], dict):
                return FALLBACK

            return data

        except Exception:
            return FALLBACK

    def normalize_entities(self, data, nlu_schema: dict):
        intent = data.get("intent")

        if intent not in nlu_schema:
            return data

        expected_entities = {c["name"] for c in nlu_schema[intent]["entity_corpus"]}

        fixed = {}
        for name in expected_entities:
            fixed[name] = data["entities"].get(name, None)

        data["entities"] = fixed
        return data

    # ---------- graceful shutdown ----------

    def unload_model(self):
        """Принудительно выгружает модель из памяти (RAM/VRAM)"""
        logger.info("Выгружаем модель Ollama из видеопамяти...")
        try:
            payload = {
                "model": self.model,
                "keep_alive": 0  # Магический параметр: 0 секунд удержания в памяти
            }
            requests.post(f"{self.host}/api/chat", json=payload, timeout=5)
            logger.info("Видеопамять свободна.")
        except Exception as e:
            logger.critical(f"Не удалось выгрузить модель: {e}")

    def shutdown(self):
        """Полностью убивает процесс Ollama и всех его дочерних процессов"""
        if not self.proc:
            return

        self.unload_model()  # Сначала освобождаем память

        logger.info("Останавливаем сервер Ollama...")
        try:
            # Используем psutil, чтобы убить дерево процессов (Ollama любит плодить процессы)
            parent = psutil.Process(self.proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            self.proc.wait(timeout=5)
            logger.info("Процесс Ollama успешно завершен.")
        except psutil.NoSuchProcess:
            pass  # Процесс уже мертв
        except Exception as e:
            logger.critical(f"Ошибка при остановке Ollama: {e}")
