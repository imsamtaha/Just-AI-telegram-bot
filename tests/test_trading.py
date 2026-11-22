import asyncio
from unittest.mock import AsyncMock

import pytest
import trading_tools as t


def test_position_size():
    reply = asyncio.run(t.position_size(None, '10000 1 100 95'))
    assert 'Risk budget: 100\n' in reply
    assert 'Units: 20\n' in reply
    assert 'Notional at entry: 2000' in reply


@pytest.mark.parametrize('text', ['10000 1 100 100', 'nan 1 100 95', '10000 101 100 95', '-1 1 100 95', '1 2'])
def test_invalid_position_inputs(text):
    assert 'Usage:' in asyncio.run(t.position_size(None, text))


@pytest.mark.parametrize('text', ['100 95 110', '100 105 90'])
def test_rr_long_short(text):
    reply = asyncio.run(t.reward_risk(None, text))
    assert 'Reward/risk: 2R' in reply
    assert '33.33333333%' in reply


def test_rr_wrong_target():
    assert 'Usage:' in asyncio.run(t.reward_risk(None, '100 95 90'))


def candles():
    return [[i*3600, 1, 100, i+1, i+1, 1] for i in range(21)]


def test_closed_candles_sorted_and_incomplete_ignored():
    close, sma, rsi, end = t.indicators(list(reversed(candles())), 3600, 20*3600+1)
    assert (close, sma, rsi, end) == (20, 10.5, 100, 72000)


def test_flat_rsi_and_missing_data():
    rows = [[i*3600, 1, 1, 1, 1, 1] for i in range(20)]
    assert t.indicators(rows, 3600, 100000)[2] == 50
    with pytest.raises(ValueError):
        t.indicators(rows[:-1], 3600, 100000)
    rows[-1][0] += 3600
    with pytest.raises(ValueError):
        t.indicators(rows, 3600, 100000)


def test_pair_validation():
    assert t.pair('btc-usd') == 'BTC-USD'
    with pytest.raises(ValueError):
        t.pair('../secrets')


def test_quote_source_and_staleness(monkeypatch):
    monkeypatch.setattr(t, 'fetch_json', AsyncMock(return_value={'price':'100', 'time':'2020-01-01T00:00:00Z'}))
    reply = asyncio.run(t.quote(None, 'BTC-USD'))
    assert 'BTC-USD: 100 USD' in reply
    assert 'STALE' in reply and 'Coinbase' in reply


def test_technical_data(monkeypatch):
    monkeypatch.setattr(t, 'fetch_json', AsyncMock(return_value=candles()))
    monkeypatch.setattr(t.time, 'time', lambda: 20*3600+1)
    reply = asyncio.run(t.technical(None, 'BTC-USD 1h'))
    assert 'SMA20: 10.5' in reply
    assert 'RSI14 (simple averages' in reply
