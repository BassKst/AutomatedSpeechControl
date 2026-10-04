import pytest

from assistant_core.integrations.entity_corpus import Corpus, EntityCorpus

CORPUS_NAMES = ("region", "number", "provider", "vpn_type", "cpu", "ram")


def corpora():
    return [(name, getattr(EntityCorpus, name)) for name in CORPUS_NAMES]


def test_corpus_stores_name_and_data():
    data = {"A": ["a1", "a2"]}
    corpus = Corpus("test", data)

    assert corpus.name == "test"
    assert corpus.data is data


def test_every_declared_attribute_is_covered_by_tests():
    declared = {
        attr
        for attr in vars(EntityCorpus)
        if not attr.startswith("_") and isinstance(getattr(EntityCorpus, attr), Corpus)
    }
    assert declared == set(CORPUS_NAMES)


@pytest.mark.parametrize(("name", "corpus"), corpora())
def test_corpus_name_matches_attribute(name, corpus):
    assert corpus.name == name


@pytest.mark.parametrize(("name", "corpus"), corpora())
def test_corpus_structure_is_well_formed(name, corpus):
    assert isinstance(corpus.data, dict) and corpus.data

    for canonical, synonyms in corpus.data.items():
        assert isinstance(canonical, str) and canonical.strip(), name
        assert isinstance(synonyms, list) and synonyms, canonical
        for synonym in synonyms:
            assert isinstance(synonym, str) and synonym.strip(), canonical


@pytest.mark.parametrize(("name", "corpus"), corpora())
def test_synonyms_are_unambiguous_within_corpus(name, corpus):
    seen = {}
    for canonical, synonyms in corpus.data.items():
        for synonym in synonyms:
            key = synonym.strip().lower()
            assert key not in seen, (
                f"{name}: синоним {synonym!r} встречается у "
                f"{seen.get(key)!r} и {canonical!r}"
            )
            seen[key] = canonical


def test_region_codes_are_expected_iso_codes():
    assert set(EntityCorpus.region.data) == {"NL", "DE", "FI", "US"}
    assert all(len(code) == 2 and code.isupper() for code in EntityCorpus.region.data)


@pytest.mark.parametrize("name", ["number", "cpu", "ram"])
def test_numeric_corpora_use_digit_keys(name):
    corpus = getattr(EntityCorpus, name)
    assert all(key.isdigit() for key in corpus.data), name


@pytest.mark.parametrize("name", ["provider", "vpn_type"])
def test_identifier_corpora_use_lowercase_keys(name):
    corpus = getattr(EntityCorpus, name)
    assert all(key == key.lower() and key.isidentifier() for key in corpus.data), name


@pytest.mark.parametrize(
    ("corpus_name", "synonym", "expected"),
    [
        ("region", "нидерландах", "NL"),
        ("region", "хельсинки", "FI"),
        ("region", "американском сервере", "US"),
        ("provider", "хетзнер", "hetzner"),
        ("provider", "диджитал оушен", "digitalocean"),
        ("vpn_type", "реалити", "vless_reality"),
        ("vpn_type", "шедоусокс", "shadowsocks"),
        ("number", "первую", "1"),
        ("ram", "8 гигов", "8"),
        ("cpu", "четырехядерный", "4"),
    ],
)
def test_reverse_lookup_resolves_synonym(corpus_name, synonym, expected):
    corpus = getattr(EntityCorpus, corpus_name)
    lookup = {
        s.strip().lower(): canonical for canonical, syns in corpus.data.items() for s in syns
    }

    assert lookup[synonym] == expected
