import logging

import common.logger_config  # noqa: F401 - настраивает логгер
import asyncio

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

from common.config import CERT_PATH, KEY_PATH, NLU_MODE, PORT
from nlu_server.nlu_engine import NLUEngine
from nlu_server.ollama_engine import OLLAMAEngine

logger = logging.getLogger("SERVER")

nlu = NLUEngine(match_threshold=75.0)
ollama: OLLAMAEngine = None


class CallRequest(BaseModel):
    text: str
    nlu_schema: dict


def heavy(payload: CallRequest) -> dict:
    if NLU_MODE == "nlu":
        return nlu.parse(payload.text, payload.nlu_schema)
    elif NLU_MODE == "llama":
        return ollama.generate(payload.text, payload.nlu_schema)

    result = nlu.parse(payload.text, payload.nlu_schema)
    if result.get("intent", "unknown") == "unknown":
        result = ollama.generate(payload.text, payload.nlu_schema)
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ollama
    # В режиме "nlu" Ollama не нужна (её нет в Docker-образе)
    if NLU_MODE != "nlu":
        logger.info("Запуск FastAPI сервера... Инициализация Ollama.")
        ollama = OLLAMAEngine()
    else:
        logger.info("Запуск FastAPI сервера в режиме NLU без Ollama.")

    yield

    logger.info("Остановка FastAPI сервера... Очистка ресурсов.")
    if ollama:
        ollama.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/call")
async def call(payload: CallRequest):
    result = await asyncio.to_thread(heavy, payload)
    return {"result": result}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="debug",
        ssl_keyfile=KEY_PATH,
        ssl_certfile=CERT_PATH
    )

