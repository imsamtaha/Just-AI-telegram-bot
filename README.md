# Just AI Telegram Bot

A full-stack web app and Telegram bot that share the same OpenAI Responses API integration. Use the web UI to test the assistant, then run the Telegram long-polling bot for users.

## Configuration

Copy `.env.example` to `.env` and set these variables:

| Variable | Description |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather. Required only for Telegram bot mode. |
| `OPENAI_API_KEY` | OpenAI API key. Required for web chat and Telegram replies. |
| `OPENAI_MODEL` | Required OpenAI model to use. Choose a currently available model for your account. |
| `BOT_SYSTEM_PROMPT` | System-level behavior instructions for the assistant. |
| `POLL_TIMEOUT` | Telegram long-poll timeout in seconds. |
| `ATLAS_DASHBOARD_URL` | Optional URL opened by the `/atlas` Telegram command. Defaults to the ATLAS dashboard. |

> `OPENAI_MODEL` is required rather than hard-coded so deployments do not silently depend on a stale or unavailable model alias.

## ATLAS dashboard command

Send `/atlas` in Telegram to get a button linking to the ATLAS dashboard. The link opens the existing dashboard; its own sign-in and access requirements still apply. The bot does not fetch or disclose dashboard or account data. In groups, `/atlas@YourBotName` is also supported.

## Run the full-stack web app locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
set -a && . ./.env && set +a
uvicorn web_app:app --reload
```

Open <http://127.0.0.1:8000> to use the browser chat tester. The web app requires `OPENAI_API_KEY` and `OPENAI_MODEL`; it does not require `TELEGRAM_BOT_TOKEN` unless you also run `bot.py`.

## Run the Telegram bot locally

```bash
set -a && . ./.env && set +a
python bot.py
```

## Deploy the web app with Docker

Build the image:

```bash
docker build -t just-ai-telegram-bot .
```

Run the web container:

```bash
docker run --env-file .env -p 8000:8000 --restart unless-stopped just-ai-telegram-bot
```

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Serves the web chat UI. |
| `GET` | `/api/status` | Reports whether required environment variables are present. |
| `POST` | `/api/chat` | Sends `{ "message": "..." }` to the configured assistant and returns `{ "reply": "..." }`. |

## Claude API and performance

To use Claude for both Telegram and the web UI, set `AI_PROVIDER=claude`,
`ANTHROPIC_API_KEY`, and `ANTHROPIC_MODEL` to a model available in your Anthropic
account. OpenAI credentials are not required in Claude mode. Restart the process
after changing configuration. `AI_PROVIDER=openai` remains the default.

The web server reuses an HTTP connection pool across requests. Telegram processes
up to eight chats concurrently within each polling batch, preserving ordering
within each chat. Delivery failures are isolated so one failed reply does not stop
polling. OpenAI REST response content blocks are now parsed correctly.

This repository is a chat assistant with an ATLAS dashboard link. It does not
retrieve live prices, connect to a brokerage, or execute trades.

## Persistent Telegram memory and follow-ups

The Telegram bot retains the last six successful conversation turns in private
chats and sends that context to the configured Claude or OpenAI provider. Groups
and the public web tester remain stateless. The bot follows the user's language;
no live prices, account access, or trading execution are added.

| Command | Purpose |
| --- | --- |
| `/remember I prefer Arabic and short answers` | Save a note (20 latest notes, up to 1000 characters each). |
| `/memory` | Inspect your saved notes. |
| `/forget` | Delete your notes and recent chat context. |
| `/followup 30m Review my trading journal` | Schedule a follow-up after a delay. |
| `/followup 2h Check my plan` | Schedule a follow-up in two hours. |
| `/followups` | List follow-ups, IDs, status, and times in UTC. |
| `/cancel 3` | Remove your follow-up with ID 3. |

Follow-ups are explicit, one-time reminders, not autonomous market monitoring.
Use `m`, `h`, or `d`, from one minute to 365 days. Up to 50 pending reminders per
private chat are allowed. Keep the bot running with network access: a background
worker checks every five seconds, including during AI calls. Overdue reminders
are delivered when the bot restarts. Failed deliveries retry after 60 seconds,
up to five attempts; `/followups` shows exhausted reminders as `failed`.
`/forget` leaves reminders intact; cancel them separately.

Set `BOT_MEMORY_PATH` (default `data/bot.sqlite3`) to a persistent local disk.
The database is not encrypted; it contains private conversation text and is
created with owner-only file permissions. Database files and logs are excluded
from Git and Docker build context. Use one process and one database per bot token.
Do not expose private data through backups. A process crash between a Telegram
send and a database commit can cause a reminder to be delivered again; delivery
is not exactly-once. Normal restarts retain the Telegram update offset.

### Update and run on Termux

After this change is merged into main, stop your current bot with Ctrl+C, then:

```bash
cd ~/Just-AI-telegram-bot
git pull --ff-only origin main
source .venv/bin/activate
set -a
source .env
set +a
python bot.py
```

No additional Python packages are needed for memory; SQLite ships with Python.
Android may suspend Termux: disable battery optimization for Termux and consider
`termux-wake-lock`. Reliable unattended delivery needs an always-running host.
Telegram 401 and 409 errors now stop polling with a token-free diagnostic; fix
credentials or duplicate polling/webhook configuration before restarting.
Ctrl+C shuts down the reminder worker and HTTP session cleanly.

For Docker bot mode, mount storage and override the default web command:

```bash
docker run --env-file .env -v just-ai-data:/app/data --restart unless-stopped just-ai-telegram-bot python bot.py
```

Run checks with `python -m pytest -q`. Tests use fake provider/Telegram calls;
no real API keys or outgoing reminders are required.

## Skills and plugins

Send `/skills` to browse AI skills: `/writer`, `/translate`, `/coder`, `/plan`,
`/tutor`, `/summarize`, `/trading`, and `/risk`, alongside existing creative modes.
Follow a command with your brief, e.g. `/translate Translate to Arabic: Hello`.
Skills use the selected Claude/OpenAI model, base instructions, and private-chat
memory. They produce text; they do not execute code or trades, generate image
files, browse the web, or access accounts. A valid provider API key is required.

Send `/plugins` to see explicit utility commands:

- `/calc (2500 * 0.02) / 5` — bounded arithmetic, without eval or shell access.
- `/time Asia/Beirut` — timezone-aware current time; defaults to UTC.
- `/weather Beirut` — current weather from Open-Meteo's public geocoding and
  forecast endpoints, with location and observation time. First matching city
  is used. City search text and coordinates are sent to Open-Meteo. Check its
  service terms before commercial use; outages and rate limits may apply.

Utility commands bypass the AI provider and do not enter conversation memory.
The current startup configuration still requires AI credentials. Commands with
Telegram's `@BotName` suffix are recognized. Python needs system timezone data
(e.g. `tzdata` on Ubuntu) for named timezones.

`plugins.py` contains an explicit registry. Developers can add an async handler
with `@register('/command', 'description')`; handlers receive the pooled HTTP
session and command arguments and return text. This is a built-in plugin
framework, not a marketplace or a bridge to ChatGPT connected apps. No third-party
code is dynamically downloaded or executed. External account integrations need
separate authentication and implementation.

AI replies also retain the typing indicator from the previous upgrade.

## Trading tools

`/tradingtools` lists commands. Tools run without an AI request:

| Command | Purpose |
| --- | --- |
| `/quote BTC-USD` | Coinbase Exchange last-trade price and timestamp; flags trades older than five minutes. |
| `/technical BTC-USD 1h` | SMA20 and RSI14 using simple averages over closed, continuous candles. Supports 5m, 15m, 1h, 1d. |
| `/size 10000 1 100 95` | Equity, risk percent, entry, stop → risk budget, units and notional. |
| `/rr 100 95 110` | Entry, stop, target → reward/risk and break-even win rate before costs. |

Public market data supports Coinbase crypto pairs only; availability and API rate
limits apply. No stock/forex feed, broker credentials, orders, or automated trading
are added. Technical calculations exclude the forming candle and flag stale data.
RSI uses simple averages, not Wilder smoothing; values may differ from charts.
Sizing assumes linear instruments with identical quote currency for equity and
prices. It ignores fees, slippage, gaps, leverage and contract multipliers.

AI commands `/technicalanalyst`, `/tradeplan`, `/journal`, and `/backtest` provide
analysis of supplied data, conditional plans, journal review, and backtest design.
They require a working AI key and cannot automatically call these tools, execute
code, store a full journal, or fetch prices. Paste tool results into your analysis
request. Existing `/trading` and `/risk` remain available. No live signals or
backtest results are fabricated.

## tgcloud migration

A serverless JavaScript port and installer are available in [cloud/README.md](cloud/README.md).
It includes AI, cloud memory, skills and tools, but tgcloud's documented SDK has
no scheduler: cloud follow-ups are checked on the next incoming message. Read
that guide before replacing Python polling or deploying the cloud app.

## Continuous chat and automatic scheduled reminders on Azure

The Special Edition can run as an always-on Node/Docker service on an Azure
Ubuntu VM, retaining the existing JavaScript skills, private login and menus.
See [server/README.md](server/README.md) for deployment, persistent storage,
explicit webhook takeover, validation and rollback. Unlike tgcloud, its worker
can deliver reminders without a new incoming message. Existing tgcloud state
is not automatically imported; plan migration before cutover.
