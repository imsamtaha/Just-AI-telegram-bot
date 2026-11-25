import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


class FakeClientSession:
    pass


class FakeClientTimeout:
    def __init__(self, total):
        self.total = total


sys.modules.setdefault(
    "aiohttp",
    SimpleNamespace(ClientSession=FakeClientSession, ClientTimeout=FakeClientTimeout),
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot import handle_update, send_message
from config import AssistantConfig, BotConfig, DEFAULT_ATLAS_DASHBOARD_URL, load_assistant_config, load_bot_config


class FakeResponse:
    def __init__(self) -> None:
        self.status_checked = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        self.status_checked = True


class FakeSession:
    def __init__(self) -> None:
        self.payloads = []
        self.payload = None
        self.url = None
        self.response = FakeResponse()

    def post(self, url, json):
        self.url = url
        self.payload = json
        self.payloads.append(json)
        return self.response


def test_load_assistant_config_requires_model(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_MODEL"):
        load_assistant_config()


def test_load_assistant_config_does_not_require_telegram_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "example-model")
    monkeypatch.setenv("BOT_SYSTEM_PROMPT", "Be helpful")

    assert load_assistant_config() == AssistantConfig(
        openai_api_key="openai-key",
        openai_model="example-model",
        system_prompt="Be helpful",
    )


def test_load_bot_config_reads_environment(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "example-model")
    monkeypatch.setenv("BOT_SYSTEM_PROMPT", "Be helpful")
    monkeypatch.setenv("POLL_TIMEOUT", "10")
    monkeypatch.setenv("ATLAS_DASHBOARD_URL", "https://example.test/atlas")

    config = load_bot_config()

    assert config == BotConfig(
        telegram_bot_token="telegram-token",
        openai_api_key="openai-key",
        openai_model="example-model",
        system_prompt="Be helpful",
        poll_timeout=10,
        atlas_dashboard_url="https://example.test/atlas",
    )


def test_send_message_splits_telegram_payload():
    session = FakeSession()
    config = BotConfig(
        telegram_bot_token="telegram-token",
        openai_api_key="openai-key",
        openai_model="example-model",
        system_prompt="Be helpful",
        poll_timeout=30,
    )

    asyncio.run(send_message(session, config, chat_id=123, text="x" * 5000))

    assert session.url == "https://api.telegram.org/bottelegram-token/sendMessage"
    assert [len(p["text"]) for p in session.payloads] == [4096, 904]
    assert "".join(p["text"] for p in session.payloads) == "x" * 5000
    assert session.response.status_checked


@pytest.mark.parametrize("command", ["/atlas", "/start atlas", "Atlas dashboard", "Open Atlas dashboard"])
def test_atlas_command_sends_dashboard_link_without_openai(command):
    session = FakeSession()
    config = BotConfig(
        telegram_bot_token="telegram-token",
        openai_api_key="openai-key",
        openai_model="example-model",
        system_prompt="Be helpful",
        poll_timeout=30,
    )

    asyncio.run(handle_update(session, config, {"message": {"chat": {"id": 123}, "text": command}}))

    assert session.payload["chat_id"] == 123
    assert "ATLAS Intelligence" in session.payload["text"]
    assert "sign in" not in session.payload["text"].lower()
    assert "sign-in" not in session.payload["text"].lower()
    assert session.payload["reply_markup"] == {
        "inline_keyboard": [[{"text": "Open ATLAS dashboard", "url": DEFAULT_ATLAS_DASHBOARD_URL}]]
    }
    assert DEFAULT_ATLAS_DASHBOARD_URL == "https://justai-atlas.online/"
    assert session.response.status_checked


def test_atlas_command_supports_group_bot_suffix_and_configured_url():
    session = FakeSession()
    config = BotConfig(
        telegram_bot_token="telegram-token",
        openai_api_key="openai-key",
        openai_model="example-model",
        system_prompt="Be helpful",
        poll_timeout=30,
        atlas_dashboard_url="https://example.test/atlas",
    )

    asyncio.run(handle_update(session, config, {"message": {"chat": {"id": 123}, "text": "/atlas@JustAIBot"}}))

    assert session.payload["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://example.test/atlas"


from openai_client import OPENAI_RESPONSES_URL, create_openai_response


class FakeJsonResponse(FakeResponse):
    async def json(self):
        return {"output_text": "Hello from AI"}


class FakeOpenAISession(FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self.headers = None
        self.response = FakeJsonResponse()

    def post(self, url, **kwargs):
        self.url = url
        self.payload = kwargs["json"]
        self.headers = kwargs["headers"]
        return self.response


def test_create_openai_response_builds_responses_payload():
    session = FakeOpenAISession()

    reply = asyncio.run(
        create_openai_response(
            session=session,
            api_key="openai-key",
            model="example-model",
            system_prompt="Be helpful",
            user_text="Hello",
        )
    )

    assert reply == "Hello from AI"
    assert session.url == OPENAI_RESPONSES_URL
    assert session.headers == {"Authorization": "Bearer openai-key"}
    assert session.payload == {
        "model": "example-model",
        "instructions": "Be helpful",
        "input": "Hello",
    }


@pytest.mark.parametrize("command", ["/start", "/help", "/creative"])
def test_telegram_help_lists_creative_tools_without_openai(command):
    session = FakeSession()
    config = BotConfig("openai-key", "example-model", "Be helpful", "telegram-token", 30)
    update = {"message": {"chat": {"id": 123, "type": "private"}, "text": command}}

    asyncio.run(handle_update(session, config, update))

    for option in ("/video", "/copyedit", "/brand", "/storyboard", "/plugins"):
        assert option in session.payload["text"]


def test_plugins_menu_links_to_requested_tools_without_openai():
    session = FakeSession()
    config = BotConfig("openai-key", "example-model", "Be helpful", "telegram-token", 30)
    update = {"message": {"chat": {"id": 123}, "text": "/plugins@JustAIBot"}}

    asyncio.run(handle_update(session, config, update))

    buttons = session.payload["reply_markup"]["inline_keyboard"]
    assert buttons == [[{"text": "Canva", "url": "https://www.canva.com/"},
                        {"text": "tldraw", "url": "https://www.tldraw.com/"}]]
