# Just AI on tgcloud

This is a JavaScript port for the tgcloud V8 runtime, not a way to run Python
on tgcloud. The `@tgcloud/cli` 0.2.0 bundled SDK reference and public platform
capabilities were inspected on 2026-11-23. The CLI login on your phone is not
available to the development workspace. No cloud deployment has been performed.

## What moves

- Claude/OpenAI replies with the selected model, base instructions, all existing
  AI skills, and recent private-chat context.
- Six recent conversation turns and 20 explicit notes, persisted in cloud SQLite.
- `/remember`, `/memory`, `/forget`, `/skills`, `/plugins`, `/tradingtools`, `/atlas`.
- Calculator, world time, weather, Coinbase crypto quotes, closed-candle SMA20 and
  simple-average RSI14, linear position sizing and reward/risk.
- One initial typing action, split long replies, duplicate-event suppression and
  a five-minute per-chat lease to avoid concurrent context overwrites.

## Important differences

**There is no documented scheduler/background-worker API in the current SDK.**
Follow-ups are saved but are checked only when their owner next messages the bot.
The bot tells the user this at creation and in help. They are NOT unattended
scheduled notifications. Continue using the Python bot if exact scheduled delivery
is essential; a verified external scheduler would be needed to restore it here.

No timers are assumed in the V8 runtime. Typing is sent once before an AI call;
Telegram may clear it after five seconds. It is not refreshed continuously.

Existing local Python SQLite data is NOT imported. This cloud app starts with
new memory and reminders. Do not run Python long polling against this bot while
its tgcloud webhook is active. Do not call deleteWebhook after deploying.

Tool outputs are not automatically sent to AI; paste them into your next analysis
request. Market data is crypto only; no live orders or authenticated broker access.
The calculator and risk tools use bounded JavaScript floating-point numbers; they
are estimates, not exact decimal financial accounting.

A request received while another request for the same chat is running gets a
busy reply and must be resent. Interrupted requests may hold the lease for five
minutes. Last 100 completed event IDs are retained per chat. Delivery is not
exactly-once: a crash after send but before a DB commit can duplicate an answer.
A reminder claimed for sending is not automatically retried after a send/write
failure; `/followups` shows `sending` or `uncertain`. Cancel and recreate it if
needed. This avoids silently retrying a message that may already have arrived.

## Configure credentials locally

The SDK currently documents no runtime secret-store API. `scripts/configure.mjs`
reads a local `.env` and generates `tgcloud/lib/private_config.js`, ignored by Git.
That server-side module is uploaded to tgcloud with the code. **It is not an
encrypted secret vault**: app administrators with CLI access can read deployed
source. Never commit it, serve it as static content, paste it into chat, or share
backups containing it. Use a dedicated provider key and rotate it if exposed.
No normal Telegram bot token is needed in the cloud app: `sdk.api` supplies Bot API
access. The separate CLI access token stays in the existing tgcloud login.

## Install into your existing starter project (on your phone)

First stop the Python bot with Ctrl+C (or stop its tmux/PM2 service). Keep your
existing `~/JustAI_chatbot` directory and CLI login. In the Python repository:

```bash
cd ~/Just-AI-telegram-bot
git fetch origin
git switch codex/tgcloud-migration
node cloud/scripts/install.mjs ~/JustAI_chatbot
cd ~/JustAI_chatbot
npm install
nano .env
```

Set `AI_PROVIDER=claude`, `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`, or select
OpenAI with its corresponding variables. Use a valid key; previous HTTP 401
failures need to be fixed independently of migration. Do not source this file as
shell code: the configuration script parses simple NAME=value lines itself.

The installer backs up the starter code in an ignored `justai-backup-*` folder,
leaves `.tgcloud/` untouched, and refuses to overwrite a custom message handler.
It preserves your package settings, adding justai scripts and pinning CLI 0.2.0.
It does not deploy, migrate, or change webhook settings.

Then configure, inspect, deploy code, and apply the cloud database schema:

```bash
chmod 600 .env
npm run justai:configure
npx tgcloud status
npx tgcloud push
npx tgcloud migrate
npx tgcloud webhook
```

`push` and `migrate` are separate: **run both**. Review the migration preview;
only `justai_*` tables/indexes should be added. No table drops are required.
`push` activates tgcloud's webhook; memory commands will need the migration to
finish before they work. Do not use `--force` to bypass unexpected differences.
`npx tgcloud webhook sync` repairs a webhook mismatch if the CLI reports one.

Test in a private chat: `/start`, `/remember I prefer Arabic`, `/memory`, then a
normal AI message. Try `/calc 2+2`, `/quote BTC-USD`, and `/size 10000 1 100 95`.
For follow-ups, send `/followup 1m Test`, wait a minute, then send `/followups`;
the overdue reminder is delivered during that new message, not while idle.
Close Termux and verify a new `/calc 2+2` reply to confirm cloud execution.

Subsequent configuration changes: edit `.env`, rerun `npm run justai:configure`,
and `npx tgcloud push`. Updating `.env` alone does not update deployed settings.

## Rollback

Before push, compare against the ignored starter backup. To restore the starter,
copy its `tgcloud/` back, remove only the migration's new modules, inspect
`npx tgcloud status`, then push. Do not delete cloud tables; they may hold memory.
To return to Python, stop using cloud delivery and explicitly disable its webhook
before starting exactly one Python polling process. Keep the old Python database.

## Validation

Run `npm test` in this directory with Node 22.13+ (Node 24 recommended); the
SQLite integration tests use `node:sqlite`. CLI deployment itself supports Node
18+, but the tests require a newer Node. Tests cover memory isolation, bounds,
leases, reminder claims, AI payloads, deduplication, arithmetic, indicators and
failure handling. They do not substitute for `push`, `migrate` and a real message
on tgcloud. No live AI/Telegram credentials are needed for tests.
