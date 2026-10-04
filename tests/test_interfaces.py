import dataclasses

import pytest

from assistant_core.interfaces import IAssistantChannel, UserRequest

EXPECTED_ABSTRACT_METHODS = {"listen", "reply", "interrupt", "close"}


class _RecordingChannel(IAssistantChannel):
    def __init__(self, requests=()):
        self._requests = list(requests)
        self.replies = []
        self.interrupts = 0
        self.closed = False

    def listen(self):
        yield from self._requests

    def reply(self, text: str) -> None:
        self.replies.append(text)

    def interrupt(self) -> None:
        self.interrupts += 1

    def close(self) -> None:
        self.closed = True


def test_channel_is_abstract():
    assert issubclass(IAssistantChannel, object)
    assert set(IAssistantChannel.__abstractmethods__) == EXPECTED_ABSTRACT_METHODS

    with pytest.raises(TypeError):
        IAssistantChannel()


def test_incomplete_channel_cannot_be_instantiated():
    class IncompleteChannel(IAssistantChannel):
        # без interrupt()
        def listen(self):
            yield UserRequest(text="привет", raw_audio=b"")

        def reply(self, text: str) -> None:
            pass

        def close(self) -> None:
            pass

    with pytest.raises(TypeError) as excinfo:
        IncompleteChannel()

    assert "interrupt" in str(excinfo.value)


def test_concrete_channel_satisfies_contract():
    first = UserRequest(text="разверни узел", raw_audio=b"\x00\x01")
    second = UserRequest(text="проверь нагрузку", raw_audio=b"\x02")
    channel = _RecordingChannel([first, second])

    assert isinstance(channel, IAssistantChannel)
    assert list(channel.listen()) == [first, second]


def test_listen_is_lazy_generator():
    channel = _RecordingChannel([UserRequest(text="тест", raw_audio=b"")])
    stream = channel.listen()

    assert hasattr(stream, "__next__")
    assert next(stream).text == "тест"


def test_reply_interrupt_and_close_are_wired():
    channel = _RecordingChannel()

    channel.reply("Готово")
    channel.interrupt()
    channel.close()

    assert channel.replies == ["Готово"]
    assert channel.interrupts == 1
    assert channel.closed is True


def test_user_request_is_dataclass_with_expected_fields():
    assert dataclasses.is_dataclass(UserRequest)
    assert {f.name for f in dataclasses.fields(UserRequest)} == {
        "text",
        "raw_audio",
        "meta",
    }


def test_user_request_meta_defaults_to_none():
    request = UserRequest(text="привет", raw_audio=b"audio")

    assert request.meta is None


def test_user_request_accepts_meta():
    meta = {"telegram_user_id": 123}
    request = UserRequest(text="привет", raw_audio=b"audio", meta=meta)

    assert request.meta == meta


def test_user_request_requires_text_and_audio():
    with pytest.raises(TypeError):
        UserRequest(text="привет")
    with pytest.raises(TypeError):
        UserRequest(raw_audio=b"audio")


def test_user_request_equality_is_structural():
    left = UserRequest(text="привет", raw_audio=b"a", meta={"k": 1})
    right = UserRequest(text="привет", raw_audio=b"a", meta={"k": 1})
    other = UserRequest(text="пока", raw_audio=b"a", meta={"k": 1})

    assert left == right
    assert left != other
