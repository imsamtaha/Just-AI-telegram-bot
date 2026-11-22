"""Read-only public crypto data and deterministic trading calculations."""
import math
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from plugins import fetch_json, register


API = 'https://api.exchange.coinbase.com/products'


def pair(value):
    value = value.upper()
    if not re.fullmatch(r'[A-Z0-9]{2,12}-[A-Z0-9]{2,12}', value):
        raise ValueError('Use a Coinbase pair such as BTC-USD.')
    return value


def positive(value):
    number = Decimal(value)
    if not number.is_finite() or not 0 < number <= Decimal('1e15'):
        raise ValueError('Use positive finite numbers up to 1e15.')
    return number


def fmt(value):
    return f'{value:.8f}'.rstrip('0').rstrip('.')


@register('/size', 'position size: /size equity risk_percent entry stop')
async def position_size(session, argument):
    try:
        equity, risk_percent, entry, stop = map(positive, argument.split())
        if risk_percent > 100 or entry == stop:
            raise ValueError()
        budget = equity * risk_percent / 100
        units = budget / abs(entry - stop)
        return (f"Direction: {'long' if stop < entry else 'short'}\n"
                f'Risk budget: {fmt(budget)}\nUnits: {fmt(units)}\n'
                f'Notional at entry: {fmt(units * entry)}\n'
                'Assumes a linear instrument and a stop filled at the specified price. '
                'Equity, entry and stop must use the same quote currency. '
                'Excludes fees, slippage and gaps; no leverage or contract multiplier applied.')
    except (InvalidOperation, ValueError):
        return 'Usage: /size 10000 1 100 95 — equity, risk % (0–100), entry, stop. Entry and stop must differ.'


@register('/rr', 'reward/risk: /rr entry stop target')
async def reward_risk(session, argument):
    try:
        entry, stop, target = map(positive, argument.split())
        if not (stop < entry < target or target < entry < stop):
            raise ValueError()
        risk, reward = abs(entry - stop), abs(target - entry)
        return (f"Direction: {'long' if stop < entry else 'short'}\n"
                f'Risk per unit: {fmt(risk)}\nReward per unit: {fmt(reward)}\n'
                f'Reward/risk: {fmt(reward / risk)}R\n'
                f'Break-even win rate before costs: {fmt(risk / (risk + reward) * 100)}%\n'
                'Assumes full wins/losses at target/stop; excludes costs and slippage.')
    except (InvalidOperation, ValueError):
        return 'Usage: /rr 100 95 110. Long: stop < entry < target. Short: target < entry < stop.'


@register('/quote', 'public crypto quote: /quote BTC-USD (Coinbase)')
async def quote(session, argument):
    try:
        symbol = pair(argument.strip())
    except ValueError as exc:
        return str(exc)
    data = await fetch_json(session, f'{API}/{symbol}/ticker', {})
    price = positive(str(data['price']))
    timestamp = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('Missing timestamp timezone')
    stale = (datetime.now(timezone.utc) - timestamp).total_seconds() > 300
    return (f'{symbol}: {fmt(price)} {symbol.split("-")[1]}\n'
            f"Last trade: {timestamp.astimezone(timezone.utc):%Y-%m-%d %H:%M:%S UTC}\n"
            + ('STALE: last trade is older than five minutes.\n' if stale else '') +
            'Source: Coinbase Exchange ticker; last trade price, not a guaranteed execution price.')


def indicators(rows, seconds, now):
    # Coinbase candles are [start, low, high, open, close, volume], newest first.
    closed = {}
    for row in rows:
        stamp = int(row[0])
        if stamp + seconds > now:
            continue
        values = [float(v) for v in row[1:6]]
        if len(values) != 5 or not all(math.isfinite(v) for v in values):
            raise ValueError('Invalid candles')
        low, high, opening, close, volume = values
        if not 0 < low <= min(opening, close) <= max(opening, close) <= high or volume < 0:
            raise ValueError('Invalid candles')
        closed[stamp] = close
    samples = sorted(closed.items())[-20:]
    if len(samples) < 20:
        raise ValueError('Need 20 closed candles')
    if any(b[0] - a[0] != seconds for a, b in zip(samples, samples[1:])):
        raise ValueError('Missing candles')
    prices = [p for _, p in samples]
    changes = [b - a for a, b in zip(prices[-15:], prices[-14:])]
    gains = sum(max(change, 0) for change in changes)
    losses = sum(max(-change, 0) for change in changes)
    rsi = 50 if gains == losses == 0 else 100 if losses == 0 else 100 - 100 / (1 + gains / losses)
    return prices[-1], sum(prices) / 20, rsi, samples[-1][0] + seconds


@register('/technical', 'closed-candle indicators: /technical BTC-USD 1h (5m, 15m, 1h, 1d)')
async def technical(session, argument):
    try:
        symbol, interval = argument.split()
        symbol = pair(symbol)
        seconds = {'5m': 300, '15m': 900, '1h': 3600, '1d': 86400}[interval]
    except (ValueError, KeyError):
        return 'Usage: /technical BTC-USD 1h — supported intervals: 5m, 15m, 1h, 1d.'
    rows = await fetch_json(session, f'{API}/{symbol}/candles', {'granularity': seconds})
    try:
        close, sma, rsi, end = indicators(rows, seconds, time.time())
    except (ValueError, TypeError, IndexError, OverflowError):
        return 'Insufficient or invalid continuous closed-candle data. Try another pair or interval.'
    timestamp = datetime.fromtimestamp(end, timezone.utc)
    stale = time.time() - end > seconds * 2
    return (f'{symbol} / {interval}\nLast closed price: {close:.8g}\nSMA20: {sma:.8g}\n'
            f'RSI14 (simple averages, not Wilder smoothing): {rsi:.2f}\n'
            f'Last candle closed: {timestamp:%Y-%m-%d %H:%M UTC}\n' +
            ('STALE DATA\n' if stale else '') +
            'Source: Coinbase Exchange; 20 continuous closed candles. Indicators are descriptive, not buy/sell signals.')
