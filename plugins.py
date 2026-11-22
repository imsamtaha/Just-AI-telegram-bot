"""Explicit command plugins. No shell execution, arbitrary URLs, or extra keys."""
import ast
import math
import operator
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiohttp


@dataclass(frozen=True)
class Plugin:
    description: str
    handler: Callable[..., Awaitable[str]]


PLUGINS: dict[str, Plugin] = {}


def register(command, description):
    def decorate(handler):
        if command in PLUGINS:
            raise ValueError(f'Duplicate plugin: {command}')
        PLUGINS[command] = Plugin(description, handler)
        return handler
    return decorate


def plugin_help():
    return 'Built-in plugins:\n' + '\n'.join(f'{name} — {p.description}' for name, p in PLUGINS.items())


def calculate(expression):
    if not expression or len(expression) > 200:
        raise ValueError('Use an arithmetic expression up to 200 characters.')
    tree = ast.parse(expression, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 50:
        raise ValueError('Expression is too complex.')
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            result = float(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            result = value if isinstance(node.op, ast.UAdd) else -value
        elif isinstance(node, ast.BinOp) and type(node.op) in binary:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError('Exponent must be between -100 and 100.')
            result = binary[type(node.op)](left, right)
        else:
            raise ValueError('Only numbers, parentheses, + - * / % and ** are supported.')
        if not isinstance(result, (int, float)) or not math.isfinite(result) or abs(result) > 1e100:
            raise ValueError('Result is outside the supported range.')
        return result
    return evaluate(tree.body)


@register('/calc', 'arithmetic: /calc (2500 * 0.02) / 5')
async def calculator(session, argument):
    try:
        return f'{calculate(argument):.12g}'
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, TypeError):
        return 'Invalid expression. Use numbers, parentheses, + - * / % or **; avoid huge values and division by zero.'


@register('/time', 'local time: /time Asia/Beirut (default UTC)')
async def world_time(session, argument):
    name = argument or 'UTC'
    if len(name) > 100:
        return 'Use an IANA timezone, for example /time Asia/Beirut.'
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return 'Unknown timezone. Try /time Asia/Beirut or /time Europe/London.'
    return datetime.now(zone).strftime('%Y-%m-%d %H:%M:%S %Z (%z)')


async def fetch_json(session, url, params):
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
        response.raise_for_status()
        return await response.json()


@register('/weather', 'current weather: /weather Beirut (public Open-Meteo API)')
async def weather(session, argument):
    if not argument or len(argument) > 120:
        return 'Usage: /weather <city up to 120 characters>'
    places = await fetch_json(session, 'https://geocoding-api.open-meteo.com/v1/search',
                              {'name': argument, 'count': 1, 'language': 'en', 'format': 'json'})
    results = places.get('results', [])
    if not results:
        return 'City not found. Try a nearby city or a more specific name.'
    place = results[0]
    data = await fetch_json(session, 'https://api.open-meteo.com/v1/forecast',
        {'latitude': place['latitude'], 'longitude': place['longitude'],
         'current': 'temperature_2m,apparent_temperature,wind_speed_10m', 'timezone': 'auto'})
    current, units = data['current'], data['current_units']
    return (f"{place['name']}, {place.get('country', '')}\n"
            f"Temperature: {current['temperature_2m']} {units['temperature_2m']}\n"
            f"Feels like: {current['apparent_temperature']} {units['apparent_temperature']}\n"
            f"Wind: {current['wind_speed_10m']} {units['wind_speed_10m']}\n"
            f"As of {current['time']} ({data.get('timezone', 'local time')})\n"
            'Source: Open-Meteo; first matching location.')


async def run_plugin(command, session, argument):
    try:
        return await PLUGINS[command].handler(session, argument)
    except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError, ArithmeticError):
        return 'This plugin is temporarily unavailable. Try again later.'
