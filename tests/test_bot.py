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

import bot
from bot import process_updates, send_message
from config import (
    AssistantConfig,
    BotConfig,
    load_assistant_config,
    load_bot_config,
    positive_int_env,
)
from openai_client import (
    FALLBACK_RESPONSE,
    OPENAI_RESPONSES_URL,
    _extract_output_text,
    create_openai_response,
)


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
        self.payload = None
        self.url = None
        self.response = FakeResponse()

    def post(self, url, json):
        self.url = url
        self.payload = json
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

    config = load_bot_config()

    assert config == BotConfig(
        telegram_bot_token="telegram-token",
        openai_api_key="openai-key",
        openai_model="example-model",
        system_prompt="Be helpful",
        poll_timeout=10,
    )


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_positive_int_env_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("POLL_TIMEOUT", value)

    with pytest.raises(RuntimeError, match="POLL_TIMEOUT must be a positive integer"):
        positive_int_env("POLL_TIMEOUT", 30)


def test_send_message_truncates_telegram_payload():
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
    assert session.payload == {"chat_id": 123, "text": "x" * 4096}
    assert session.response.status_checked


def test_process_updates_continues_after_failure(monkeypatch):
    processed = []

    async def fake_handle_update(session, config, update):
        processed.append(update["update_id"])
        if update["update_id"] == 1:
            raise RuntimeError("Telegram rejected the reply")

    monkeypatch.setattr(bot, "handle_update", fake_handle_update)
    config = BotConfig("key", "model", "prompt", "token", 30)

    offset = asyncio.run(
        process_updates(object(), config, [{"update_id": 1}, {"update_id": 2}])
    )

    assert processed == [1, 2]
    assert offset == 3


class FakeJsonResponse(FakeResponse):
    async def json(self):
        return {
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Hello "},
                        {"type": "output_text", "text": "from AI"},
                    ],
                },
            ]
        }


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


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (None, None),
        ({}, None),
        ({"output": "not-a-list"}, None),
        ({"output": [None, {"type": "reasoning"}]}, None),
        ({"output": [{"type": "message", "content": "bad"}]}, None),
        (
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "refusal", "refusal": "No"},
                            {"type": "output_text", "text": None},
                        ],
                    }
                ]
            },
            None,
        ),
        (
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "one"}],
                    },
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": " two"}],
                    },
                ]
            },
            "one two",
        ),
    ],
)
def test_extract_output_text_handles_raw_response_variants(payload, expected):
    assert _extract_output_text(payload) == expected


class EmptyJsonResponse(FakeResponse):
    async def json(self):
        return {"output": []}


def test_create_openai_response_uses_fallback_without_text():
    session = FakeOpenAISession()
    session.response = EmptyJsonResponse()

    reply = asyncio.run(
        create_openai_response(session, "key", "model", "prompt", "hello")
    )

    assert reply == FALLBACK_RESPONSE
