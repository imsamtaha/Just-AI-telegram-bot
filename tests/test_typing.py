import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest
import bot


def test_typing_action_payload():
    class Response:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        def raise_for_status(self):
            pass
    class Session:
        def post(self, url, **kwargs):
            assert url == 'https://test/sendChatAction'
            assert kwargs['json'] == {'chat_id': 123, 'action': 'typing'}
            assert kwargs['timeout'].total == 3
            return Response()
    asyncio.run(bot.send_typing(Session(), SimpleNamespace(telegram_api_base='https://test'), 123))


def test_typing_refresh_and_cleanup(monkeypatch):
    async def run():
        calls = []
        second = asyncio.Event()
        gate = asyncio.Event()
        async def send(*args):
            calls.append(args[-1])
            if len(calls) == 2:
                second.set()
        async def sleep(delay):
            assert delay == 4
            if len(calls) >= 2:
                await gate.wait()
        monkeypatch.setattr(bot, 'send_typing', send)
        monkeypatch.setattr(bot.asyncio, 'sleep', sleep)
        async with bot.typing_indicator(None, None, 123):
            await asyncio.wait_for(second.wait(), 1)
        assert calls == [123, 123]
    asyncio.run(run())


@pytest.mark.parametrize('failure', [aiohttp.ClientError(), asyncio.TimeoutError()])
def test_typing_failure_is_nonfatal(failure):
    class Session:
        def post(self, *args, **kwargs):
            raise failure
    asyncio.run(bot.send_typing(Session(), SimpleNamespace(telegram_api_base='test'), 1))


@pytest.mark.parametrize('outcome', ['success', 'failure', 'cancel'])
def test_handler_cleans_typing_task(monkeypatch, outcome):
    async def run():
        started = asyncio.Event()
        stopped = asyncio.Event()
        async def typing(*args):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        async def answer(*args):
            await started.wait()
            if outcome == 'failure':
                raise aiohttp.ClientError()
            if outcome == 'cancel':
                raise asyncio.CancelledError()
            return 'Answer'
        monkeypatch.setattr(bot, 'send_typing', typing)
        monkeypatch.setattr(bot, 'call_openai', answer)
        sender = AsyncMock()
        monkeypatch.setattr(bot, 'send_message', sender)
        update = {'message': {'chat': {'id': 1, 'type': 'private'}, 'text': 'Hello'}}
        if outcome == 'cancel':
            with pytest.raises(asyncio.CancelledError):
                await bot.handle_update(None, SimpleNamespace(system_prompt='Helpful'), update)
            sender.assert_not_called()
        else:
            await bot.handle_update(None, SimpleNamespace(system_prompt='Helpful'), update)
            sender.assert_awaited_once()
        assert stopped.is_set()
    asyncio.run(run())
