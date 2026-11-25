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

Send `/atlas` in Telegram to open [ATLAS Intelligence](https://justai-atlas.online/). Telegram chat is available as soon as you open the bot. The dashboard website manages access to its private pages. In groups, use `/atlas@YourBotName`. A link from the dashboard can use `https://t.me/YourBotName?start=atlas` to open the same menu in a private chat.

If an existing deployment sets `ATLAS_DASHBOARD_URL` to the previous address, update that variable to `https://justai-atlas.online/` and restart the bot on its configured host.

## Creative tools in Telegram

Open `/creative` for the command list. Use `/video` for cut plans, `/copyedit`
to revise text, `/brand` for identity systems, and `/storyboard` for shot lists.
Add your brief after the command. Photo and video modes produce editing
instructions for use on your own media.

### Lebanese Arabic

Send `/start` and choose **لبناني** or **English**. You can also switch using
`/ar` or `/en`. The choice is saved in private chats. Arabic commands work
with or without a slash, for example `برمجة راجع هالكود` or `مهارات`.
The assistant uses conversational Lebanese and can mirror Arabizi.

### Coding, personal assistance, and saved prompts

- `/coding Review this Python function` or `برمجة راجع هذه الدالة`
- `/personal Plan my week` or `مساعد رتّب أسبوعي`
- `/addskill editor Rewrite in plain language` saves or updates a private prompt.
- `/skill editor <task>` activates that prompt for one request.
- `/skills` lists saved prompts by name. `/delskill editor` deletes one.

Prompts can be written in Arabic or English. Up to 20 private skills are stored
in the bot's existing SQLite database and survive restarts when its data disk
persists. Use `/delskill` to remove a saved prompt.

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
