import asyncio
from types import SimpleNamespace

import pytest

from telegram_client import TelegramAPIError, TelegramClient, split_message


class Response:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        return self.data


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_split_message_respects_utf16_limit_and_preserves_text():
    text = "a" * 4095 + "😀" + "b" * 4096
    chunks = split_message(text)
    assert "".join(chunks) == text
    assert all(len(chunk.encode("utf-16-le")) // 2 <= 4096 for chunk in chunks)


def test_send_text_sends_markup_only_with_first_chunk():
    session = Session([Response({"ok": True, "result": True}), Response({"ok": True, "result": True})])
    client = TelegramClient(session, "https://api.telegram.org/bot-token", retries=0)
    markup = {"inline_keyboard": [[{"text": "Open", "url": "https://example.test"}]]}

    asyncio.run(client.send_text(12, "x" * 5000, markup))

    assert [call[1]["json"]["text"] for call in session.calls] == ["x" * 4096, "x" * 904]
    assert session.calls[0][1]["json"]["reply_markup"] == markup
    assert "reply_markup" not in session.calls[1][1]["json"]


def test_telegram_api_retries_rate_limit_using_retry_after():
    delays = []
    session = Session([
        Response({"ok": False, "error_code": 429, "description": "Too Many Requests", "parameters": {"retry_after": 2}}),
        Response({"ok": True, "result": [{"update_id": 9}]})
    ])
    client = TelegramClient(session, "https://api.telegram.org/bot-token", retries=1, sleep=lambda delay: _record_delay(delays, delay))

    updates = asyncio.run(client.get_updates(timeout=20, offset=8))

    assert updates == [{"update_id": 9}]
    assert delays == [2.0]
    assert session.calls[0][1]["params"]["offset"] == 8
    assert len(session.calls) == 2


async def _record_delay(delays, delay):
    delays.append(delay)


def test_permanent_telegram_error_is_not_retried():
    session = Session([Response({"ok": False, "error_code": 401, "description": "Unauthorized"})])
    client = TelegramClient(session, "https://api.telegram.org/bot-token", retries=3)

    with pytest.raises(TelegramAPIError) as error:
        asyncio.run(client.get_updates(timeout=10))

    assert error.value.status == 401
    assert len(session.calls) == 1


def test_invalid_update_response_is_rejected():
    session = Session([Response({"ok": True, "result": {"not": "a list"}})])
    client = TelegramClient(session, "https://api.telegram.org/bot-token", retries=0)

    with pytest.raises(TelegramAPIError, match="invalid result"):
        asyncio.run(client.get_updates(timeout=10))
