import logging
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)


class NLUEngine:
    """
    Модуль семантического анализа на базе нечеткого поиска (Fuzzy String Matching).
    """

    def __init__(self, match_threshold: float = 75.0):
        self.match_threshold = match_threshold

    def _extract_entities(self, text: str, entity_corpus_schema: list) -> dict:
        entities = {}
        text = text.lower()

        for corpus in entity_corpus_schema:
            entity_type = corpus["name"]
            mapping = corpus["data"]

            best_score = 0
            best_value = None
            best_synonym = None

            for sys_value, synonyms in mapping.items():
                match = process.extractOne(
                    query=text,
                    choices=synonyms,
                    scorer=fuzz.partial_ratio
                )

                if match:
                    found_synonym, score, _ = match
                    if score > best_score:
                        best_score = score
                        best_value = sys_value
                        best_synonym = found_synonym

            threshold = 85 if len(text) < 20 else 80

            if best_score >= threshold:
                entities[entity_type] = best_value
                logger.info(f"[ENTITY MATCH] {entity_type} -> {best_value} (via '{best_synonym}', score={best_score})")
            else:
                entities[entity_type] = None

        return entities

    def fuzzy_set(self, text: str, nlu_schema: dict) -> dict:
        """
        Нечеткий поиск с помощью алгоритма Левенштейна
        """
        text_lower = text.lower().strip()

        result = {
            "text": text_lower,
            "intent": "unknown",
            "entities": {},
            "confidence": 0.0,
            "msg": None
        }

        best_intent = "unknown"
        highest_score = 0.0

        for intent_name, intent_data in nlu_schema.items():
            phrases = intent_data.get("intent_corpus", [])
            if not phrases:
                continue

            match = process.extractOne(
                query=text_lower,
                choices=phrases,
                scorer=fuzz.token_set_ratio
            )

            if match:
                score = match[1]
                if score > highest_score:
                    highest_score = score
                    best_intent = intent_name

        if highest_score >= self.match_threshold:
            entity_corpus = nlu_schema[best_intent].get("entity_corpus",[])

            result.update({
                "intent": best_intent,
                "confidence": round(highest_score, 2),
                "entities": self._extract_entities(text_lower, entity_corpus),
                "msg": "Готово"
            })
            logger.info(f"NLU: Распознано '{best_intent}' с уверенностью {highest_score}%")

        else:
            logger.warning(f"NLU: Команда не распознана. Лучшее совпадение: {best_intent} ({highest_score}%)")

        return result

    def parse(self, text: str, nlu_schema: dict) -> dict:
        return self.fuzzy_set(text, nlu_schema)
