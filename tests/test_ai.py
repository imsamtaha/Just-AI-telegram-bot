import asyncio
import aiohttp
import pytest
from claude_client import create_claude_response
from config import load_assistant_config
from openai_client import create_openai_response


class Response:
    def __init__(self, data):
        self.data = data
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    def raise_for_status(self):
        pass
    async def json(self):
        return self.data


class Session:
    def __init__(self, data):
        self.data = data
    def post(self, url, **kwargs):
        self.url, self.request = url, kwargs
        return Response(self.data)


def test_claude_config_without_openai(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'claude')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test')
    monkeypatch.setenv('ANTHROPIC_MODEL', 'test-model')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    config = load_assistant_config()
    assert config.ai_provider == 'claude'
    assert config.openai_model == 'test-model'


def test_invalid_provider(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'unknown')
    with pytest.raises(RuntimeError, match='AI_PROVIDER'):
        load_assistant_config()


def test_claude_request_and_text_blocks():
    session = Session({'content': [{'type': 'thinking'}, {'type': 'text', 'text': 'Hello'}]})
    assert asyncio.run(create_claude_response(session, 'key', 'model', 'system', 'hi')) == 'Hello'
    assert session.request['headers']['anthropic-version'] == '2023-06-01'
    assert session.request['json']['messages'] == [{'role': 'user', 'content': 'hi'}]
    assert session.request['json']['system'] == 'system'


def test_openai_rest_output_blocks():
    session = Session({'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'Actual REST output'}]}]})
    assert asyncio.run(create_openai_response(session, 'key', 'model', 'system', 'hi')) == 'Actual REST output'
