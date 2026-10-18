import asyncio

from bot import handle_update
from config import BotConfig
from risk_reference import risk_command_response


class _Response:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self):
        pass


class _Session:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response()


def _config():
    return BotConfig(
        telegram_bot_token="fake-token",
        openai_api_key="fake-key",
        openai_model="example",
        system_prompt="Test",
        poll_timeout=1,
    )


def test_risk_index_has_topic_commands_and_clear_safety_label():
    output = risk_command_response("/risk")
    assert "trident" in output
    assert "leverage" in output
    assert "للمحاكاة فقط" in output


def test_risk_topic_replies_with_source_pages():
    output = risk_command_response("/risk@AtlasBot leverage")
    assert "34-35" in output
    assert "Risk Management tut V3.pdf" in output
    assert risk_command_response("/risk unknown") is not None
    assert risk_command_response("hello") is None


def test_bot_handles_risk_command_without_calling_openai():
    session = _Session()
    update = {"message": {"chat": {"id": 123}, "text": "/risk trident"}}
    asyncio.run(handle_update(session, _config(), update))
    assert len(session.calls) == 1
    url, data = session.calls[0]
    assert url.endswith("/sendMessage")
    assert data["json"]["chat_id"] == 123
    assert "27-29" in data["json"]["text"]
