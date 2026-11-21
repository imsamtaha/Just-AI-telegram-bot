import asyncio
import logging
import os
import re
import time
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

import aiohttp

from claude_client import create_claude_response
from config import BotConfig, load_bot_config
from creative_modes import build_creative_prompt, creative_help, parse_creative_command
from memory import Memory
from openai_client import create_openai_response
from telegram_client import TelegramClient, TelegramAPIError

ATLAS_DASHBOARD_LABEL = "Open ATLAS dashboard"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


async def call_openai(
    session: aiohttp.ClientSession,
    config: BotConfig,
    user_text: str,
    system_prompt: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> str:
    create_response = create_claude_response if config.ai_provider == "claude" else create_openai_response
    return await create_response(
        session=session,
        api_key=config.openai_api_key,
        model=config.openai_model,
        system_prompt=system_prompt or config.system_prompt,
        user_text=user_text,
        history=history,
    )


async def send_message(
    session: aiohttp.ClientSession,
    config: BotConfig,
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    client = TelegramClient(session, config.telegram_api_base)
    await client.send_text(chat_id, text, reply_markup)


def is_atlas_command(text: str) -> bool:
    """Recognize /atlas, including Telegram's /atlas@botname group syntax."""
    parts = text.strip().split(maxsplit=1)
    command = parts[0].split("@", maxsplit=1)[0].lower() if parts else ""
    return command == "/atlas"


async def handle_update(
    session: aiohttp.ClientSession,
    config: BotConfig,
    update: dict[str, Any],
    memory: Memory | None = None,
) -> None:
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
        help_text = (
            creative_help()
            + "\n/atlas — open the ATLAS dashboard"
            + "\n/remember <fact> — save a note"
            + "\n/memory — show saved notes"
            + "\n/forget — clear notes and conversation"
            + "\n/followup <delay> <text> — schedule a reminder"
            + "\n/followups — list reminders"
            + "\n/cancel <id> — cancel a reminder"
        )
        await send_message(session, config, chat_id, help_text)
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
        reminders = memory.followups(owner)
        return "\n".join(
            f"#{reminder['id']} — {datetime.fromtimestamp(reminder['due'], timezone.utc):%Y-%m-%d %H:%M UTC} — {reminder['status']} — {reminder['content']}"
            for reminder in reminders
        ) or "No pending follow-ups."
    if command == "/cancel":
        if not argument.isdigit():
            return "Usage: /cancel <id>"
        return "Follow-up cancelled." if memory.cancel(owner, int(argument)) else "Follow-up not found."
    return "Unknown command."


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
        try:
            await deliver_followups(session, config, memory)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Follow-up worker iteration failed")
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
    client = TelegramClient(session, config.telegram_api_base)
    offset = memory.offset() if memory else None
    while True:
        try:
            updates = await client.get_updates(timeout=config.poll_timeout, offset=offset)
        except TelegramAPIError as exc:
            if exc.status in {401, 409}:
                LOGGER.error("Telegram %s: check the token, stop duplicate bots, and check webhook settings.", exc.status)
                return
            LOGGER.error("Telegram polling failed: %s", exc)
            await asyncio.sleep(5)
            continue

        # Process chats concurrently but preserve per-chat ordering. Only commit
        # the contiguous successful prefix so a failed update is replayed.
        chats: dict[int, list[dict[str, Any]]] = {}
        for update in updates:
            message = update.get("message") or update.get("edited_message") or {}
            chat_id = message.get("chat", {}).get("id", 0)
            chats.setdefault(chat_id, []).append(update)

        successful: set[int] = set()
        limit = asyncio.Semaphore(8)

        async def process_chat(chat_updates: list[dict[str, Any]]) -> None:
            async with limit:
                for update in chat_updates:
                    try:
                        await handle_update(session, config, update, memory)
                    except Exception:
                        LOGGER.error("Update processing failed: %s", update.get("update_id"))
                        break
                    successful.add(update["update_id"])

        await asyncio.gather(*(process_chat(chat_updates) for chat_updates in chats.values()))
        for update in updates:
            update_id = update["update_id"]
            if update_id not in successful:
                break
            offset = update_id + 1

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
