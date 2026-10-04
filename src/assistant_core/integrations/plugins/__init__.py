import time
from ..base import BaseIntegration
from ..entity_corpus import EntityCorpus


class TemplateIntegration(BaseIntegration):

    @property
    def intent_name(self) -> str:
        return "template_integration"

    @property
    def intent_corpus(self):
        return [
            "Шаблон плагина",
            "Шаблон интеграции"
        ]

    @property
    def entity_corpus(self):
        return [EntityCorpus.region, EntityCorpus.number]

    @property
    def is_long_running(self) -> bool:
        return True

    @property
    def access_level(self) -> int:
        return 10

    def execute(self, entities: dict, context: dict) -> dict:
        region = entities.get("region", "UNKNOWN")
        number = entities.get("number", "UNKNOWN")

        # Эмуляция запроса
        time.sleep(10)

        return {
            "status": "success",
            "message": f"Шаблон интеграции с номером {number} в {region}",
            "raw_log": "HTTP 200"
        }
