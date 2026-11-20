import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest
import bot
from bot import memory_command
from memory import Memory
from claude_client import create_claude_response
from openai_client import create_openai_response


@pytest.fixture
def memory(tmp_path):
    store = Memory(tmp_path / 'memory.sqlite3')
    yield store
    store.close()


def test_restart_bounds_isolation_and_forget(tmp_path):
    path = tmp_path / 'state.sqlite3'
    m = Memory(path)
    for i in range(10):
        m.remember_turn('a', f'q{i}', f'a{i}')
    m.save_note('a', 'Prefers Arabic')
    m.set_offset(23)
    rid = m.schedule('a', 1, 'review', 100)
    m.close()
    m = Memory(path)
    assert m.offset() == 23
    assert len(m.history('a')) == 12
    assert m.history('a')[0]['content'] == 'q4'
    assert m.notes('a') == ['Prefers Arabic']
    assert m.history('b') == [] and m.notes('b') == []
    assert not m.cancel('b', rid)
    m.forget('a')
    assert m.history('a') == [] and m.notes('a') == []
    assert len(m.pending('a')) == 1
    m.close()


def test_note_limit(memory):
    for i in range(30):
        memory.save_note('a', str(i))
    assert len(memory.notes('a')) == 20


def test_reminder_commands_and_validation(memory):
    assert 'Usage:' in memory_command(memory, 'a', 1, '/followup', 'tomorrow hello')
    assert '1 minute' in memory_command(memory, 'a', 1, '/followup', '0m hi')
    assert 'scheduled' in memory_command(memory, 'a', 1, '/followup', '1m review plan')
    assert 'review plan' in memory_command(memory, 'a', 1, '/followups', '')
    rid = memory.pending('a')[0]['id']
    assert 'not found' in memory_command(memory, 'b', 2, '/cancel', str(rid))
    assert 'cancelled' in memory_command(memory, 'a', 1, '/cancel', str(rid))
    assert memory.pending('a') == []


def test_reminder_delivery_retry_and_completion(memory, monkeypatch):
    rid = memory.schedule('a', 1, 'review', 0)
    sender = AsyncMock(side_effect=RuntimeError('network'))
    monkeypatch.setattr(bot, 'send_message', sender)
    asyncio.run(bot.deliver_followups(None, None, memory))
    assert len(memory.pending('a')) == 1
    assert not memory.due(0)
    for _ in range(4):
        memory.retry(rid, now=0)
    assert memory.due(100) == []  # Five failed attempts stop retrying.
    memory.schedule('a', 1, 'success', 0)
    sender.side_effect = None
    asyncio.run(bot.deliver_followups(None, None, memory))
    assert memory.pending('a') == []


def test_private_context_and_group_isolation(memory, monkeypatch):
    memory.save_note('1', 'Prefers Arabic')
    memory.remember_turn('1', 'my name is Sam', 'Hello Sam')
    ai = AsyncMock(return_value='Hello again')
    monkeypatch.setattr(bot, 'call_openai', ai)
    monkeypatch.setattr(bot, 'send_message', AsyncMock())
    config = SimpleNamespace(system_prompt='Helpful')
    update = {'message': {'chat': {'id': 1, 'type': 'private'}, 'text': 'What is my name?'}}
    asyncio.run(bot.handle_update(None, config, update, memory))
    assert 'Prefers Arabic' in ai.call_args.args[3]
    assert ai.call_args.args[4][0]['content'] == 'my name is Sam'
    update['message']['chat']['type'] = 'group'
    asyncio.run(bot.handle_update(None, config, update, memory))
    assert ai.call_args.args[4] is None
    assert 'Prefers Arabic' not in ai.call_args.args[3]
    update['message']['text'] = '/memory'
    ai.reset_mock()
    asyncio.run(bot.handle_update(None, config, update, memory))
    ai.assert_not_called()


def test_failed_ai_not_saved(memory, monkeypatch):
    monkeypatch.setattr(bot, 'call_openai', AsyncMock(side_effect=RuntimeError()))
    monkeypatch.setattr(bot, 'send_message', AsyncMock())
    asyncio.run(bot.handle_update(None, SimpleNamespace(system_prompt='Helpful'),
        {'message': {'chat': {'id': 1, 'type': 'private'}, 'text': 'Hello'}}, memory))
    assert not memory.history('1')


class Response:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    def raise_for_status(self):
        pass
    async def json(self):
        return {'output_text': 'ok', 'content': [{'type': 'text', 'text': 'ok'}]}


class Session:
    def post(self, url, **kwargs):
        self.payload = kwargs['json']
        return Response()


@pytest.mark.parametrize('client,key', [(create_claude_response, 'messages'), (create_openai_response, 'input')])
def test_providers_receive_history(client, key):
    history = [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': 'hello'}]
    session = Session()
    asyncio.run(client(session, 'key', 'model', 'prompt', 'next', history))
    assert session.payload[key] == history + [{'role': 'user', 'content': 'next'}]


@pytest.mark.parametrize('status', [401, 409])
def test_polling_stops_without_token_leak(status, caplog):
    class Failure(Response):
        def raise_for_status(self):
            raise aiohttp.ClientResponseError(None, (), status=status, message='secret-token')
    class PollSession:
        def get(self, *args, **kwargs):
            return Failure()
    asyncio.run(bot.polling_loop(PollSession(), SimpleNamespace(poll_timeout=30, telegram_api_base='secret-token'), None))
    assert str(status) in caplog.text
    assert 'secret-token' not in caplog.text


def test_emoji_chunks_preserve_content(monkeypatch):
    class Sender:
        def __init__(self):
            self.chunks = []
        def post(self, url, **kwargs):
            self.chunks.append(kwargs['json']['text'])
            return Response()
    sender = Sender()
    text = '😀' * 3000
    asyncio.run(bot.send_message(sender, SimpleNamespace(telegram_api_base='test'), 1, text))
    assert ''.join(sender.chunks) == text
    assert all(len(c.encode('utf-16-le')) // 2 <= 4096 for c in sender.chunks)
