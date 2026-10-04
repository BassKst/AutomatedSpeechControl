"""Тесты базового класса интеграций (assistant_core.integrations.base).

``BaseIntegration`` задаёт контракт плагина и значения по умолчанию для
``is_long_running`` и ``access_level``. От этих значений зависит поведение
диспетчера: долгая задача уходит в отдельный поток, а уровень доступа
участвует в авторизации голосовой команды.
"""

import pytest

from assistant_core.integrations.base import BaseIntegration
from assistant_core.integrations.entity_corpus import Corpus, EntityCorpus
from assistant_core.integrations.plugins import TemplateIntegration

EXPECTED_ABSTRACT_MEMBERS = {"intent_name", "intent_corpus", "entity_corpus", "execute"}


class _MinimalIntegration(BaseIntegration):
    """Реализация без переопределения необязательных свойств."""

    @property
    def intent_name(self) -> str:
        return "minimal"

    @property
    def intent_corpus(self) -> list[str]:
        return ["минимальная интеграция"]

    @property
    def entity_corpus(self) -> list[Corpus]:
        return [EntityCorpus.region]

    def execute(self, entities: dict, context: dict) -> dict:
        return {"status": "success", "message": f"{entities}|{context}"}


def test_base_integration_is_abstract():
    assert set(BaseIntegration.__abstractmethods__) == EXPECTED_ABSTRACT_MEMBERS

    with pytest.raises(TypeError):
        BaseIntegration()


def test_incomplete_integration_cannot_be_instantiated():
    class NoExecute(BaseIntegration):
        @property
        def intent_name(self) -> str:
            return "broken"

        @property
        def intent_corpus(self) -> list[str]:
            return []

        @property
        def entity_corpus(self) -> list:
            return []

    with pytest.raises(TypeError) as excinfo:
        NoExecute()

    assert "execute" in str(excinfo.value)


def test_default_is_not_long_running():
    assert _MinimalIntegration().is_long_running is False


def test_default_access_level_is_zero():
    assert _MinimalIntegration().access_level == 0


def test_logger_is_named_after_concrete_class():
    """Имя логгера берётся из self.__class__.__name__, поэтому в логах
    виден конкретный плагин, а не BaseIntegration."""
    assert _MinimalIntegration().logger.name == "_MinimalIntegration"


def test_execute_receives_entities_and_context():
    integration = _MinimalIntegration()

    result = integration.execute({"region": "NL"}, {"user": "admin"})

    assert result["status"] == "success"
    assert "NL" in result["message"]
    assert "admin" in result["message"]


def test_optional_properties_can_be_overridden():
    class LongRunningAdminIntegration(_MinimalIntegration):
        @property
        def is_long_running(self) -> bool:
            return True

        @property
        def access_level(self) -> int:
            return 50

    integration = LongRunningAdminIntegration()

    assert integration.is_long_running is True
    assert integration.access_level == 50


# --- Шаблон плагина из integrations/plugins/__init__.py ---
# execute() у TemplateIntegration содержит time.sleep(10), поэтому здесь
# проверяются только метаданные, без вызова execute().


def test_template_integration_metadata():
    template = TemplateIntegration()

    assert template.intent_name == "template_integration"
    assert template.intent_corpus == ["Шаблон плагина", "Шаблон интеграции"]
    assert template.entity_corpus == [EntityCorpus.region, EntityCorpus.number]


def test_template_integration_is_long_running_and_restricted():
    template = TemplateIntegration()

    assert template.is_long_running is True
    assert template.access_level == 10


def test_template_integration_is_a_base_integration():
    assert isinstance(TemplateIntegration(), BaseIntegration)
