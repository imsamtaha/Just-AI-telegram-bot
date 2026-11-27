# AWS Lightsail: continuous chat and automatic reminders

Use the same always-on Special Edition runtime prepared for Azure. No additional
AWS SDK, public web server, provider keys, or separate scheduler is required.
AWS resources have not been created by this repository or by the assistant.

## 1. Create or identify the server

In AWS Lightsail, create a Linux/Unix **OS Only → Ubuntu 24.04 LTS** instance.
Use a suitable region and instance plan for your budget. Attach a static IPv4
address. In networking, restrict SSH (TCP 22) to your own IP where possible; the
bot needs outbound HTTPS only, so no bot-specific inbound HTTP port is needed.
Use persistent instance storage, enable snapshots/backups, and do not stop the
instance when you want continuous service.

Open the Lightsail browser SSH terminal. The Ubuntu login is normally `ubuntu`.
If you already have an instance, use it rather than creating a duplicate.
The public IP/hostname identifies the server; a public SSH key alone does not.
Keep SSH private keys and API secrets on your device/server, never in chat.

Optional discovery from AWS CloudShell, which is already authenticated to your
account (select the region containing the instance):

```bash
aws lightsail get-instances --query 'instances[].{Name:name,IP:publicIpAddress,State:state.name,User:username}' --output table
```

## 2. Stage the package on the instance

Install Git, Docker Engine and Compose v2 using the official Ubuntu instructions:
https://docs.docker.com/engine/install/ubuntu/ . Verify:

```bash
docker --version
sudo docker compose version
```

Then, in the **AWS instance terminal** (not Termux):

```bash
git clone --branch codex/aws-continuous-reminders https://github.com/imsamtaha/Just-AI-telegram-bot.git
cd Just-AI-telegram-bot
bash server/aws/prepare.sh
```

On the first run the script creates a root-only private environment template and
stops with instructions. Edit it:

```bash
sudo nano /etc/justai/bot.env
bash server/aws/prepare.sh
```

Set TELEGRAM_BOT_TOKEN, AI_PROVIDER and the matching provider API key/model. The
normal Telegram bot token is required, not the tgcloud app CLI token. Use newly
rotated credentials for previously exposed keys. The preparation script does not
read configuration back into its output, change a webhook, or start polling. It
preserves an existing bot.env instead of overwriting it and checks the configured
values inside the built image without contacting Telegram or AI.

## 3. Review state migration before switching

The original tgcloud database stays unchanged. Existing memory, login sessions
and pending reminders are **not automatically imported** into the VM volume.
Plan a data transfer before cutover if those records must be retained; otherwise
customers must log in again and recreate pending reminders. Do not delete the
old database. The runtime retains the same Special Edition features, but that
does not mean its old data has already moved.

## 4. Explicit takeover and activation

Stop any other Python/Node polling instance first. The following one-time command
switches delivery away from tgcloud by deleting its webhook without dropping
pending Telegram updates. Run it only after preparation and configuration succeed:

```bash
sudo docker compose -p justai -f server/compose.yaml run --rm --no-deps bot node server/bot.mjs --takeover
sudo docker compose -p justai -f server/compose.yaml up -d
sudo docker compose -p justai -f server/compose.yaml ps
sudo docker compose -p justai -f server/compose.yaml logs --tail 30 bot
```

Expected log: `JUST AI Special Edition is polling; automatic reminder worker active.`
The restart policy and enabled Docker service keep the container running after
SSH disconnects and instance reboots. There must be exactly **one** polling bot.
Do not push/sync tgcloud again while AWS is active: it restores the webhook and
causes a Telegram 409 conflict. No live takeover was performed during development.

## 5. Confirm automatic delivery

In Telegram, open @JustAI_chatbot, log in, and send:

```text
/home
/followup 1m Test the AWS reminder
```

Send nothing else: the reminder should arrive around a minute later, while your
login session is active. Close SSH and repeat. Reboot the instance and verify
pending reminders survive. Arabic `/ذكرني ١د جرّب تذكير AWS` also works.

The worker checks every five seconds. Network outages, rate limits and an
in-progress request can delay delivery; it is not an exact-time SLA. Logout or
session expiry pauses delivery until the customer logs in again. Ambiguous
sends are marked uncertain to avoid blind duplicates. See ../README.md for
storage, failed-send statuses, backups, updates and rollback.

## Rollback

Stop AWS polling first:

```bash
sudo docker compose -p justai -f server/compose.yaml stop bot
```

Then, in the original linked project on your phone:

```bash
cd ~/JustAI_chatbot
npx tgcloud webhook sync
npx tgcloud webhook
```

New AWS memory/reminders are not automatically copied back. Keep the named data
volume: do not run `down -v`. Protect disk snapshots and backups as private data.

## Validation

The runtime package has 116 passing automated tests, a successful image build,
and a non-root/read-only container SQLite/reminder smoke test from its Azure
preparation. This AWS addition changes setup/docs only; its script is syntax
checked. No AWS account, instance, SSH session, real API credentials or live
reminder send was accessed. Actual activation requires your instance address,
an authorized connection and successful end-to-end Telegram verification.
