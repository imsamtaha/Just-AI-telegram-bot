import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest
import bot
import plugins
from creative_modes import parse_creative_command, build_creative_prompt, skills_help


@pytest.mark.parametrize('expression,result', [('2500*0.02/5', 10), ('-(3+2)**2', -25), ('2**3', 8)])
def test_calculator(expression, result):
    assert plugins.calculate(expression) == result


@pytest.mark.parametrize('expression', ['__import__("os").system("id")', '[1,2]', '9**999999', '1/0', '1e300', 'True'])
def test_calculator_rejects_unsafe_or_invalid(expression):
    reply = asyncio.run(plugins.calculator(None, expression))
    assert 'Invalid expression' in reply


def test_timezones():
    assert 'UTC' in asyncio.run(plugins.world_time(None, 'UTC'))
    assert 'Unknown timezone' in asyncio.run(plugins.world_time(None, '../etc/passwd'))


def test_skills():
    mode, text = parse_creative_command('/risk@JustAIBot Review my plan')
    assert (mode, text) == ('risk', 'Review my plan')
    assert 'READY-TO-USE PROMPT' not in build_creative_prompt(mode, text)
    assert '/translate' in skills_help()


def test_weather(monkeypatch):
    calls = []
    async def fetch(session, url, params):
        calls.append((url, params))
        if 'geocoding' in url:
            return {'results': [{'name': 'Beirut', 'country': 'Lebanon', 'latitude': 33.9, 'longitude': 35.5}]}
        return {'timezone': 'Asia/Beirut', 'current': {'temperature_2m': 22, 'apparent_temperature': 23,
            'wind_speed_10m': 5, 'time': '2026-11-21T12:00'},
            'current_units': {'temperature_2m': '°C', 'apparent_temperature': '°C', 'wind_speed_10m': 'km/h'}}
    monkeypatch.setattr(plugins, 'fetch_json', fetch)
    result = asyncio.run(plugins.weather(None, 'Beirut'))
    assert '22 °C' in result and 'Asia/Beirut' in result and 'Open-Meteo' in result
    assert calls[1][1]['latitude'] == 33.9


def test_weather_failure(monkeypatch):
    monkeypatch.setattr(plugins, 'fetch_json', AsyncMock(side_effect=aiohttp.ClientError()))
    assert 'temporarily unavailable' in asyncio.run(plugins.run_plugin('/weather', None, 'Beirut'))


def test_plugins_bypass_ai(monkeypatch):
    ai = AsyncMock()
    sender = AsyncMock()
    monkeypatch.setattr(bot, 'call_openai', ai)
    monkeypatch.setattr(bot, 'send_message', sender)
    asyncio.run(bot.handle_update(None, SimpleNamespace(),
        {'message': {'chat': {'id': 1}, 'text': '/calc@JustAIBot 2+2'}}))
    ai.assert_not_called()
    assert sender.call_args.args[3] == '4'


def test_skill_keeps_base_prompt(monkeypatch):
    ai = AsyncMock(return_value='Your plan')
    monkeypatch.setattr(bot, 'call_openai', ai)
    monkeypatch.setattr(bot, 'send_message', AsyncMock())
    asyncio.run(bot.handle_update(None, SimpleNamespace(system_prompt='Base rules'),
        {'message': {'chat': {'id': 1}, 'text': '/plan Launch a store'}}))
    assert ai.call_args.args[3].startswith('Base rules')
    assert ai.call_args.args[2] == 'Launch a store'
