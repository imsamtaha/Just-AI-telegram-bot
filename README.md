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

> `OPENAI_MODEL` is required rather than hard-coded so deployments do not silently depend on a stale or unavailable model alias.

## Run the full-stack web app locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
set -a && . ./.env && set +a
uvicorn web_app:app --reload
```

Open <http://127.0.0.1:8000> to use the browser chat tester. The web app requires `OPENAI_API_KEY` and `OPENAI_MODEL`; it does not require `TELEGRAM_BOT_TOKEN` unless you also run `bot.py`.

## ATLAS Risk Guide (read-only)

The bot has a page-indexed, paraphrased reference to the uploaded `Risk Management tut V3.pdf` under `knowledge/risk_management_v3.json`. The original PDF is **not** stored or publicly distributed by this repository.

In Telegram, send `/risk` to display the topic index, or `/risk trident`, `/risk reward`, `/risk sizing`, `/risk leverage`, `/risk drawdown`, `/risk management`, `/risk candles`, `/risk structure`, or `/risk foundation` for a short Arabic study explanation with source-page references. This command returns deterministic text and does not call OpenAI or connect to a broker. Telegram polling must be running with a configured bot token for the commands to reach users.

The reference never changes ATLAS trade rules, creates orders, or approves live execution. See the source's caveats in the JSON document.

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
