import time
from ..base import BaseIntegration
from ..entity_corpus import EntityCorpus


class CheckLoadIntegration(BaseIntegration):

    @property
    def intent_name(self) -> str:
        return "check_load"

    @property
    def intent_corpus(self):
        return [
            "проверь нагрузку на сервер",
            "проверить нагрузку",
            "скажи нагрузку",
            "какая нагрузка",
            "выведи состояние"
        ]

    @property
    def entity_corpus(self):
        return [EntityCorpus.region, EntityCorpus.number]

    @property
    def is_long_running(self) -> bool:
        return True

    @property
    def access_level(self) -> int:
        return 0

    def execute(self, entities: dict, context: dict) -> dict:
        region = entities.get("region", "UNKNOWN")
        number = entities.get("number", "UNKNOWN")

        if not region:
            return {"status": "error", "message": "Не предоставлен регион", "raw_log": "NoRG"}

        if not number:
            return {"status": "error", "message": "Не предоставлен номер сервера", "raw_log": "NoNB"}

        self.logger.info(f"Проверяю нагрузку на сервер {number} в {region}...")

        # Эмуляция запроса
        time.sleep(10)

        return {
            "status": "success",
            "message": f"Сервер {number} в {region} имеет среднюю нагрузку",
            "raw_log": "HTTP 200"
        }
