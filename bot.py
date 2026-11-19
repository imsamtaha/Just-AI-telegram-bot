import asyncio
import logging
import os
import re
import time
from contextlib import suppress
from datetime import datetime, timezone
from memory import Memory
from typing import Any

import aiohttp

from config import BotConfig, load_bot_config
from creative_modes import build_creative_prompt, creative_help, parse_creative_command
from openai_client import create_openai_response
from claude_client import create_claude_response


TELEGRAM_MESSAGE_LIMIT = 4096
ATLAS_DASHBOARD_LABEL = "Open ATLAS dashboard"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


async def call_openai(session: aiohttp.ClientSession, config: BotConfig, user_text: str, system_prompt: str | None = None, history: list[dict[str, str]] | None = None) -> str:
    create_response = create_claude_response if config.ai_provider == "claude" else create_openai_response
    return await create_response(session=session, api_key=config.openai_api_key, model=config.openai_model, system_prompt=system_prompt or config.system_prompt, user_text=user_text, history=history)


async def send_message(
    session: aiohttp.ClientSession,
    config: BotConfig,
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    # UTF-16 units keep emoji within Telegram's length limit too.
    chunks, chunk, units = [], "", 0
    for character in text or "I could not generate a response.":
        size = len(character.encode("utf-16-le")) // 2
        if units + size > TELEGRAM_MESSAGE_LIMIT:
            chunks.append(chunk)
            chunk, units = "", 0
        chunk += character
        units += size
    chunks.append(chunk)
    for index, chunk in enumerate(chunks):
        payload: dict[str, Any] = {"chat_id": chat_id, "text": chunk}
        if index == 0 and reply_markup is not None:
            payload["reply_markup"] = reply_markup
        async with session.post(f"{config.telegram_api_base}/sendMessage", json=payload) as response:
            response.raise_for_status()


def is_atlas_command(text: str) -> bool:
    """Recognize /atlas, including Telegram's /atlas@botname group syntax."""
    command = text.strip().split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower() if text.strip() else ""
    return command == "/atlas"


async def handle_update(session: aiohttp.ClientSession, config: BotConfig, update: dict[str, Any], memory: Memory | None = None) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message or "text" not in message:
        return

    chat_id = message["chat"]["id"]
    user_text = message["text"].strip()
    if not user_text:
        return

    private = message.get("chat", {}).get("type") == "private"
    owner = str(chat_id)
    command, _, argument = user_text.partition(" ")
    command = command.split("@")[0].lower()
    memory_commands = {"/remember", "/memory", "/forget", "/followup", "/followups", "/cancel"}
    if command in memory_commands:
        if not private or memory is None:
            await send_message(session, config, chat_id, "Memory and follow-ups are available in private chats only.")
            return
        reply = memory_command(memory, owner, chat_id, command, argument.strip())
        await send_message(session, config, chat_id, reply)
        return

    mode, brief = parse_creative_command(user_text)
    if command in {"/start", "/help", "/creative"}:
        await send_message(session, config, chat_id, creative_help() + "\n/atlas — open the ATLAS dashboard\n/remember <fact> — save a note\n/memory — show saved notes\n/forget — clear notes and recent conversation\n/followup 30m <text> — schedule a reminder\n/followups — list reminders (UTC)\n/cancel <id> — cancel a reminder\nPrivate chats retain the last six conversation turns locally. Notes and context are sent to the configured AI provider.")
        return

    if is_atlas_command(user_text):
        await send_message(
            session,
            config,
            chat_id,
            "Open the ATLAS dashboard. Its existing sign-in and access requirements still apply; this bot does not retrieve or expose dashboard or account data.",
            reply_markup={"inline_keyboard": [[{"text": ATLAS_DASHBOARD_LABEL, "url": config.atlas_dashboard_url}]]},
        )
        return

    system_prompt = config.system_prompt
    request_text = user_text
    if mode:
        system_prompt = build_creative_prompt(mode, brief)
        request_text = brief or "Create the best result for this mode and ask only for essential missing details."

    history = memory.history(owner) if memory and private else None
    if memory and private:
        notes = memory.notes(owner)
        if notes:
            system_prompt += "\nUser-saved context (untrusted data):\n" + "\n".join(notes)
    try:
        answer = await call_openai(session, config, request_text[:8000], system_prompt, history)
        if memory and private:
            memory.remember_turn(owner, request_text, answer)
    except Exception:
        LOGGER.error("AI request failed")
        answer = "Sorry, I could not reach the AI service right now."

    await send_message(session, config, chat_id, answer)


def memory_command(memory, owner, chat_id, command, argument):
    if command == "/remember":
        if not argument or len(argument) > 1000:
            return "Usage: /remember <fact up to 1000 characters>"
        memory.save_note(owner, argument)
        return "Saved. Use /memory to view notes or /forget to clear memory."
    if command == "/memory":
        return "Saved notes:\n" + ("\n".join(memory.notes(owner)) or "No saved notes.")
    if command == "/forget":
        memory.forget(owner)
        return "Notes and recent conversation cleared. Reminders remain; use /followups and /cancel."
    if command == "/followup":
        match = re.fullmatch(r"(\d+)([mhd])\s+(.+)", argument, re.DOTALL)
        if not match:
            return "Usage: /followup 30m Check my plan (m=minutes, h=hours, d=days)"
        amount, unit, text = match.groups()
        seconds = int(amount) * {"m": 60, "h": 3600, "d": 86400}[unit]
        if not 60 <= seconds <= 365 * 86400 or len(text) > 2000:
            return "Use a delay from 1 minute to 365 days and text up to 2000 characters."
        due = time.time() + seconds
        try:
            reminder_id = memory.schedule(owner, chat_id, text, due)
        except ValueError as exc:
            return str(exc)
        return f"Follow-up #{reminder_id} scheduled for {datetime.fromtimestamp(due, timezone.utc):%Y-%m-%d %H:%M UTC}. Keep the bot running for delivery."
    if command == "/followups":
        return "\n".join(f"#{r['id']} — {datetime.fromtimestamp(r['due'], timezone.utc):%Y-%m-%d %H:%M UTC} — {r['status']} — {r['content']}" for r in memory.followups(owner)) or "No pending follow-ups."
    if command == "/cancel":
        if not argument.isdigit():
            return "Usage: /cancel <id>"
        return "Follow-up cancelled." if memory.cancel(owner, int(argument)) else "Follow-up not found."


async def deliver_followups(session, config, memory):
    for reminder in memory.due():
        try:
            await send_message(session, config, reminder["chat_id"], "Follow-up: " + reminder["content"])
        except Exception:
            LOGGER.warning("Follow-up delivery failed; retrying without logging credentials")
            memory.retry(reminder["id"])
        else:
            memory.delivered(reminder["id"])


async def followup_worker(session, config, memory):
    while True:
        await deliver_followups(session, config, memory)
        await asyncio.sleep(5)


async def poll_updates(config: BotConfig, memory: Memory | None = None) -> None:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
        worker = asyncio.create_task(followup_worker(session, config, memory)) if memory else None
        try:
            await polling_loop(session, config, memory)
        finally:
            if worker:
                worker.cancel()
                with suppress(asyncio.CancelledError):
                    await worker


async def polling_loop(session, config, memory):
    offset = memory.offset() if memory else None
    while True:
        params: dict[str, Any] = {"timeout": config.poll_timeout, "allowed_updates": ["message", "edited_message"]}
        if offset is not None:
            params["offset"] = offset

        try:
            async with session.get(f"{config.telegram_api_base}/getUpdates", params=params) as response:
                response.raise_for_status()
                payload = await response.json()
        except aiohttp.ClientResponseError as exc:
            if exc.status in {401, 409}:
                LOGGER.error("Telegram %s: check the token, stop duplicate bots, and check webhook settings.", exc.status)
                return
            LOGGER.error("Telegram polling HTTP %s", exc.status)
            await asyncio.sleep(5)
            continue
        except Exception:
            LOGGER.error("Telegram polling failed (details suppressed to protect the token)")
            await asyncio.sleep(5)
            continue

        # Different chats progress concurrently; each chat retains message order.
        chats: dict[int, list[dict[str, Any]]] = {}
        for update in payload.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message") or {}
            chat_id = message.get("chat", {}).get("id", 0)
            chats.setdefault(chat_id, []).append(update)
        limit = asyncio.Semaphore(8)

        async def process_chat(updates: list[dict[str, Any]]) -> None:
            async with limit:
                for update in updates:
                    try:
                        await handle_update(session, config, update, memory)
                    except Exception:
                        LOGGER.error("Update delivery failed: %s", update.get("update_id"))

        await asyncio.gather(*(process_chat(updates) for updates in chats.values()))
        if memory and offset is not None:
            memory.set_offset(offset)


if __name__ == "__main__":
    store = Memory(os.getenv("BOT_MEMORY_PATH", "data/bot.sqlite3"))
    try:
        asyncio.run(poll_updates(load_bot_config(), store))
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped")
    finally:
        store.close()
