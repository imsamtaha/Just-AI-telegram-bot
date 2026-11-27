# Azure VM: continuous Special Edition chat and automatic reminders

This runs the same JavaScript Special Edition core as the tgcloud bot, using
Node 24, local persistent SQLite and Telegram long polling. It does not downgrade
to the separate Python bot. Bilingual menus, consumer login, Lebanese Arabic,
Trader analysis modes, market/creative tools and AI briefings are retained.

The background worker checks due reminders every five seconds without another
incoming message. The VM, Docker service and network must remain running. Delays
can occur during outages, API limits, or an in-progress request holding the
same user's lock. This is best-effort delivery, not an exact-time SLA.

## Before cutover

- Use one non-Spot Ubuntu VM (24.04 LTS recommended). Disable Azure auto-shutdown.
- Allow SSH only from your own IP. No public HTTP port is required: polling uses
  outbound HTTPS. Keep SSH private keys on your device; never send them in chat.
- Install Docker Engine and Compose v2 using the current official Ubuntu guide:
  https://docs.docker.com/engine/install/ubuntu/ . Enable the Docker service.
- Never run multiple polling instances for the same bot token, and never run
  tgcloud webhook delivery alongside the VM poller.
- Existing tgcloud memory, sessions and reminders are **not automatically copied**.
  They remain untouched in the old cloud database. Plan any data migration before
  cutover; otherwise users must log in again and recreate pending reminders on
  the VM. Do not delete the old data or claim an automatic migration occurred.

## Stage on the VM (does not change Telegram delivery)

Connect with your existing SSH credentials. Then:

```bash
sudo systemctl enable --now docker
git clone --branch codex/azure-continuous-reminders https://github.com/imsamtaha/Just-AI-telegram-bot.git
cd Just-AI-telegram-bot
sudo install -d -m 700 /etc/justai
sudo install -m 600 server/.env.example /etc/justai/bot.env
sudo nano /etc/justai/bot.env
sudo docker compose -p justai -f server/compose.yaml build
```

Set the normal TELEGRAM_BOT_TOKEN (not tgcloud's app CLI token), AI_PROVIDER,
and the corresponding provider API key/model in the private environment file.
Use replacement keys for any credentials previously exposed. No API key is
baked into the image or committed. Existing `private_config.js` is not used.
Do not repeat `install ... bot.env` after configuring it: that overwrites it
with placeholders. Later edits use `sudo nano /etc/justai/bot.env`.

## Controlled activation

First stop any Python/PM2/other polling instance. Build and configure the VM
before doing the next step. The bot refuses to start if a webhook is active.
Only this explicit one-time command disables it, preserving pending updates:

```bash
sudo docker compose -p justai -f server/compose.yaml run --rm --no-deps bot node server/bot.mjs --takeover
sudo docker compose -p justai -f server/compose.yaml up -d
sudo docker compose -p justai -f server/compose.yaml ps
sudo docker compose -p justai -f server/compose.yaml logs --tail 30 bot
```

Expected log: `JUST AI Special Edition is polling; automatic reminder worker active.`
Docker's `unless-stopped` policy and enabled Docker service keep it running after
SSH disconnects and VM reboots. A stopped/deallocated Azure VM cannot run it.
Do not run `npx tgcloud push` or `webhook sync` after cutover: that reactivates
webhook delivery and causes polling conflicts. On HTTP 401/409 the poller stops
and prints a token-free diagnostic; fix credentials or the duplicate deployment
rather than ignoring a restart loop.

## Verify end to end

1. Open @JustAI_chatbot. `/start`, choose Arabic/English, then log in.
2. Send a normal AI message and test `/home` and `/calc 2+2`.
3. Send `/followup 1m Test automatic reminder` (or `/ذكرني ١د جرّب التذكير`).
4. Send **nothing else**. The reminder should arrive around a minute later.
5. Disconnect SSH; repeat to verify the VM is serving it independently.
6. Reboot the VM and verify the container restarts and pending reminders persist.

Sessions last 30 days. Logout/expiry pauses automatic reminders until the user
logs in again; overdue reminders can then be delivered. Cancel with `/cancel`
or `/الغاء`. Actual delivery is not guaranteed if Telegram blocks the bot.

## Delivery semantics

The worker atomically claims a due reminder under the same per-user lease used
by chat handlers, then sends it. Concurrent ticks and cancellations cannot
claim the same pending row twice. Successful delivery deletes it.

Telegram 429 responses return the reminder to pending with the indicated retry
delay (5–3600 seconds). Known 400/403 errors mark it failed. Network/ambiguous
server failures are marked uncertain instead of risking an automatic duplicate.
An interrupted `sending` record becomes uncertain at service startup. Inspect
`/followups`, cancel/recreate uncertain reminders as appropriate. A crash between
send and commit means exactly-once delivery cannot be promised.

The worker catches operational errors and continues on the next tick. Persistent
SQLite and offsets survive restarts. Old Telegram updates are deduplicated using
the existing recent event-ID window, not an unlimited event archive.

## Storage, backup and maintenance

The named Docker volume `justai_justai_data` stores `/data/bot.sqlite3` and its WAL.
Do not use `docker compose down -v` unless you deliberately intend to delete
memory, sessions and reminders. Keep the volume on persistent managed VM storage;
configure Azure disk/VM backups. Do not place it on a temporary/ephemeral disk.
The process runs as an unprivileged user with a read-only application filesystem;
only /data and temporary storage are writable. SQLite data is not app-encrypted;
protect the VM/disks and backups. Operators can access it, as stated in bot privacy.

For updates, commit/backup first and review changes:

```bash
git pull --ff-only origin codex/azure-continuous-reminders
sudo docker compose -p justai -f server/compose.yaml up -d --build
```

Keep the compose project name `justai` so the same persistent volume is reused.
For a consistent offline SQLite backup, stop the container, copy the entire data
volume (including any WAL), then restart. Treat backups as private customer data.

## Rollback to tgcloud

```bash
sudo docker compose -p justai -f server/compose.yaml stop bot
```

Then, in the original linked project on your phone:

```bash
cd ~/JustAI_chatbot
npx tgcloud webhook sync
npx tgcloud webhook
```

This restores tgcloud delivery but does not transfer the newer VM data back.
The old tgcloud version still only checks reminders on incoming messages.

## Validation and limits

```bash
node --test server/tests/*.test.mjs
cd cloud && npm test
```

Runtime tests use real local SQLite and fake Telegram sends. Docker builds and a
non-root/read-only container smoke test validate local storage and reminder
execution. No Azure VM, live bot, credentials or Telegram cutover was accessed
during development. The owner's VM address, SSH username and an authorized SSH
connection are still required before deploying. Cloud service costs and actual
availability remain the owner's Azure configuration.
