#!/usr/bin/env bash
# Stage the bot on a VM; never changes Telegram webhook or starts polling.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_dir"
if ! command -v docker >/dev/null 2>&1; then
  echo 'Install Docker Engine and Compose v2 first. See server/aws/README.md.' >&2
  exit 1
fi
sudo docker compose version >/dev/null
sudo systemctl enable --now docker
sudo install -d -m 700 /etc/justai
if ! sudo test -f /etc/justai/bot.env; then
  sudo install -m 600 server/.env.example /etc/justai/bot.env
  echo 'Private configuration template created. Edit it with sudo nano /etc/justai/bot.env, then rerun this script.'
  echo 'No webhook or live bot was changed.'
  exit 2
fi
sudo chmod 600 /etc/justai/bot.env
sudo docker compose -p justai -f server/compose.yaml config --quiet
sudo docker compose -p justai -f server/compose.yaml build
# Validate configuration locally inside the image, without calling Telegram or AI.
sudo docker compose -p justai -f server/compose.yaml run --rm --no-deps bot node --input-type=module -e 'import {loadConfig} from "./server/config.mjs"; loadConfig(); console.log("Private environment validated; credentials were not printed.");'
echo 'Staging complete. The existing Telegram bot is still active.'
echo 'See server/aws/README.md for the explicit takeover and start commands.'
