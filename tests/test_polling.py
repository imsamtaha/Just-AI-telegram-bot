import asyncio
from types import SimpleNamespace
import pytest
from bot import check_polling, PollingBlocked

class Response:
    def __init__(self, payload): self.payload = payload
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    def raise_for_status(self): pass
    async def json(self): return self.payload

@pytest.mark.parametrize('payload', [
    {'ok': True, 'result': {'url': 'https://example.test/private-webhook'}},
    {'ok': False}, {'ok': True, 'result': None},
])
def test_existing_webhook_or_unknown_state_blocks_polling(payload):
    session = SimpleNamespace(get=lambda url: Response(payload))
    with pytest.raises(PollingBlocked) as error:
        asyncio.run(check_polling(session, SimpleNamespace(telegram_api_base='test')))
    assert 'private-webhook' not in str(error.value)

def test_absent_webhook_allows_polling():
    session = SimpleNamespace(get=lambda url: Response({'ok': True, 'result': {'url': ''}}))
    asyncio.run(check_polling(session, SimpleNamespace(telegram_api_base='test')))
