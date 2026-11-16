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
