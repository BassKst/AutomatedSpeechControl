import logging

import requests

from common.config import CERT_PATH, PORT, API_HOST
logger = logging.getLogger(__name__)


def remote_call(text: str, nlu_schema: dict) -> dict:
    try:
        r = requests.post(
            f"https://{API_HOST}:{PORT}/call",
            json={
                "text": text,
                "nlu_schema": nlu_schema
            },
            verify=CERT_PATH,
            timeout=120
        )

        r.raise_for_status()  # Бросит ошибку, если сервер ответит 500

        return r.json()["result"]

    except requests.exceptions.ConnectionError:
        logger.error("Не удалось установить соединение с сервером")
        return None


    except requests.exceptions.Timeout:
        logger.error("Сервер не ответил вовремя")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса: {e}")
        return None

