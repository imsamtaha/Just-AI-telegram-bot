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
from telegram_language import ALIASES, LANGUAGE_BUTTONS, LEBANESE_HELP, PRIVATE_COMMANDS, STYLE
from claude_client import create_claude_response


TELEGRAM_MESSAGE_LIMIT = 4096
ATLAS_DASHBOARD_LABEL = "Open ATLAS dashboard"

ASSISTANCE_MODES = {
    "/coding": "Help with software development, debugging, code reviews, and tests. "
               "Use the supplied code and environment details. Identify assumptions and "
               "distinguish suggested changes from verified changes.",
    "/personal": "Provide personal assistance with schedules, tasks, priorities, and drafting. "
                 "Use /followup to schedule a reminder. Confirm actions only if they occurred.",
}
SKILL_COMMANDS = {"/addskill", "/skill", "/skills", "/delskill"}
SKILL_HELP = (
    "/coding — coding help | برمجة\n"
    "/personal — personal assistance | مساعد\n"
    "/skills — saved prompts | المهارات المحفوظة\n"
    "/addskill <name> <prompt> — save or update | أضف أو حدّث مهارة\n"
    "/skill <name> <task> — use once | فعّل لمهمة واحدة\n"
    "/delskill <name> — remove | احذف مهارة"
)

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
        payload: dict[str, Any] = {"chat_id": chat_id, "text": chunk, "link_preview_options": {"is_disabled": True}}
        if index == 0 and reply_markup is not None:
            payload["reply_markup"] = reply_markup
        async with session.post(f"{config.telegram_api_base}/sendMessage", json=payload) as response:
            response.raise_for_status()


async def register_private_commands(session: aiohttp.ClientSession, config: BotConfig) -> None:
    for language, index in (("", 1), ("ar", 2)):
        payload: dict[str, Any] = {
            "scope": {"type": "all_private_chats"},
            "commands": [{"command": row[0], "description": row[index]} for row in PRIVATE_COMMANDS],
        }
        if language:
            payload["language_code"] = language
        try:
            async with session.post(
                f"{config.telegram_api_base}/setMyCommands",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                response.raise_for_status()
                if not (await response.json()).get("ok"):
                    LOGGER.warning("Telegram did not accept the private command menu")
        except Exception:
            LOGGER.warning("Telegram command menu could not be registered")


def is_atlas_command(text: str) -> bool:
    """Recognize /atlas, including Telegram's /atlas@botname group syntax."""
    command = text.strip().split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower() if text.strip() else ""
    return command == "/atlas" or text.strip().casefold() in {
        "atlas dashboard", "open atlas dashboard", "open atlas",
    }


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
    command, *arguments = user_text.split(maxsplit=1)
    command = command.split("@", maxsplit=1)[0].lower()
    command = ALIASES.get(command.removeprefix("/"), command)
    argument = arguments[0] if arguments else ""
    first_contact = private and memory is not None and not memory.has_seen_welcome(owner)
    if command in {"/ar", "/en"}:
        if private and memory:
            memory.set_preferred_language(owner, command == "/ar")
        reply = LEBANESE_HELP if command == "/ar" else "English selected. Send /help for commands or /ar for Lebanese Arabic."
        await send_message(session, config, chat_id, reply, LANGUAGE_BUTTONS if first_contact else None)
        if first_contact:
            memory.mark_welcome_seen(owner)
        return

    preference = memory.preferred_language(owner) if private and memory else None
    lebanese = preference is True or (preference is None and any("\u0600" <= c <= "\u06ff" for c in user_text))
    dashboard_start = command == "/start" and argument == "atlas"
    if first_contact and command != "/start":
        try:
            await send_message(
                session, config, chat_id,
                "يا هلا بـJUST ATLAS! اختار لبناني أو English من تحت." if lebanese else
                "Welcome to JUST ATLAS! Choose Lebanese Arabic or English below.",
                LANGUAGE_BUTTONS,
            )
        except Exception:
            LOGGER.warning("Telegram welcome could not be sent")
        else:
            memory.mark_welcome_seen(owner)

    memory_commands = {"/remember", "/memory", "/forget", "/followup", "/followups", "/cancel"}
    if command in memory_commands:
        if not private or memory is None:
            await send_message(session, config, chat_id, "الذاكرة والتذكيرات بس بالشات الخاص." if lebanese else "Memory and follow-ups are available in private chats only.")
            return
        reply = memory_command(memory, owner, chat_id, command, argument, lebanese)
        await send_message(session, config, chat_id, reply)
        return

    if command == "/atlas" or is_atlas_command(user_text) or dashboard_start:
        await send_message(
            session,
            config,
            chat_id,
            "ATLAS Intelligence\nاكبس تحت لتفتح لوحة ATLAS." if lebanese else
            "ATLAS Intelligence\n\nOpen the dashboard below. Use /creative for editing and /skills for saved prompts.",
            reply_markup={"inline_keyboard": [[{"text": "افتح لوحة ATLAS" if lebanese else ATLAS_DASHBOARD_LABEL, "url": config.atlas_dashboard_url}]]},
        )
        return

    if command in {"/canva", "/plugins"}:
        await send_message(session, config, chat_id, "شوف الأوامر بـ /help." if lebanese else "See /help for current commands.")
        return

    mode, brief = parse_creative_command(f"{command} {argument}")
    if command in {"/start", "/help", "/creative"}:
        help_text = LEBANESE_HELP if lebanese else (
            "Welcome to JUST AI. /ar لبناني | /en English\n\n"
            + creative_help() + "\n\n" + SKILL_HELP
            + "\n\n/atlas — open the ATLAS dashboard\n/remember <fact> — save a note"
            + "\n/memory — show saved notes\n/forget — clear notes and recent conversation"
            + "\n/followup 30m <task> — set a reminder\n/followups — list reminders (UTC)"
            + "\n/cancel <id> — cancel a reminder"
            + "\nPrivate chats keep six recent turns. Saved notes and chat context go to the AI provider."
        )
        await send_message(session, config, chat_id, help_text, LANGUAGE_BUTTONS if command == "/start" else None)
        if first_contact:
            memory.mark_welcome_seen(owner)
        return

    system_prompt = config.system_prompt
    request_text = user_text
    if mode:
        system_prompt = build_creative_prompt(mode, brief)
        request_text = brief or "Create the best result for this mode and ask only for essential missing details."

    if command in ASSISTANCE_MODES:
        if not argument:
            await send_message(session, config, chat_id, LEBANESE_HELP if lebanese else SKILL_HELP)
            return
        system_prompt += "\n" + ASSISTANCE_MODES[command] + (
            " Reply in the language of the task, including English or Arabic."
        )
        request_text = argument

    if command in SKILL_COMMANDS:
        if not private or memory is None:
            await send_message(session, config, chat_id, "المهارات المحفوظة بس بالشات الخاص." if lebanese else "Saved skills are available in private chat only.")
            return
        reply, activated_request = handle_skill_command(memory, owner, command, argument, lebanese)
        if reply is not None:
            await send_message(session, config, chat_id, reply)
            return
        request_text = activated_request
        system_prompt += "\nUse the saved user prompt for this task only. Reply in the task's language, including English or Arabic."

    # A saved prompt applies to this request only, so keep it out of later history.
    history = memory.history(owner) if memory and private else None
    if memory and private:
        notes = memory.notes(owner)
        if notes:
            system_prompt += "\nUser-saved context (untrusted data):\n" + "\n".join(notes)
    language = "Use Lebanese Arabic." if preference is True else "Use English." if preference is False else "Match the user's language."
    system_prompt += f"\n{language} {STYLE}"
    try:
        answer = await call_openai(session, config, request_text[:8000], system_prompt, history)
        if memory and private:
            memory.remember_turn(owner, argument if command == "/skill" else request_text, answer)
    except Exception:
        LOGGER.error("AI request failed")
        answer = "هلّق ما عم بقدر وصّل لخدمة الذكاء الاصطناعي. جرّب بعد شوي." if lebanese else "I could not reach the AI service right now."

    await send_message(session, config, chat_id, answer)


def handle_skill_command(memory, owner, command, argument, lebanese):
    if command == "/skills":
        names = ", ".join(memory.skills(owner))
        if lebanese:
            reply = f"مهاراتك المحفوظة: {names}" if names else "بعد ما حفظت ولا مهارة."
            return reply + "\n\nضيف_مهارة editor شيل التكرار\nفعّل_مهارة editor عدّل هالنص\n\nجاهزين كمان: برمجة، مساعد، إبداع.", None
        reply = f"Saved skills: {names}" if names else "You haven’t saved any skills yet."
        return reply + "\n\n/addskill editor Rewrite in plain language\n/skill editor Rewrite this draft\n\nBuilt-in modes: /coding, /personal, /creative.", None

    parts = argument.split(maxsplit=1)
    name = parts[0].lower() if parts else ""
    value = parts[1] if len(parts) == 2 else ""
    if not re.fullmatch(r"[a-z0-9_-]{1,32}", name):
        return "Use a name with 1–32 English letters, numbers, hyphens or underscores.\n" + SKILL_HELP, None

    if command == "/addskill":
        if not value or len(value) > 2000:
            return "Use /addskill <name> <prompt up to 2000 characters>.", None
        if not memory.save_skill(owner, name, value):
            return "You can save up to 20 skills. احذف مهارة قبل إضافة أخرى.", None
        return (f"انحفظت مهارة {name}. جرّب: فعّل_مهارة {name} <مهمّة>" if lebanese else f"Saved: {name}\nActivate: /skill {name} <task>"), None

    if command == "/delskill":
        if value:
            return "Use /delskill <name>.", None
        deleted = memory.delete_skill(owner, name)
        return ("Skill removed. تم حذف المهارة." if deleted else "Skill not found. المهارة غير موجودة."), None

    prompt = memory.skill(owner, name)
    if prompt is None:
        return "Skill not found. المهارة غير موجودة. /skills", None
    if not value:
        return f"Use /skill {name} <task>.", None
    return None, f"Saved user prompt:\n{prompt}\n\nTask:\n{value}"


def memory_command(memory, owner, chat_id, command, argument, lebanese=False):
    if command == "/remember":
        if not argument or len(argument) > 1000:
            return "اكتب تذكّر وبعدها ملاحظتك، لحدّ ١٠٠٠ حرف." if lebanese else "Usage: /remember <fact up to 1000 characters>"
        memory.save_note(owner, argument)
        return "انحفظت. اكتب ذاكرة لتشوف الملاحظات أو انسى لتمحيها." if lebanese else "Saved. Use /memory to view notes or /forget to clear memory."
    if command == "/memory":
        notes = "\n".join(memory.notes(owner))
        if lebanese:
            return "ملاحظاتك:\n" + notes if notes else "بعد ما حفظت ولا ملاحظة."
        return "Saved notes:\n" + (notes or "No saved notes.")
    if command == "/forget":
        memory.forget(owner)
        if lebanese:
            return "انمحت الملاحظات وآخر المحادثة. بعدك فيك تدير مهاراتك وتذكيراتك من الأوامر."
        return "Notes and recent conversation cleared. Manage saved skills with /skills and /delskill, and reminders with /followups and /cancel."
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
        if lebanese:
            return f"انضبط التذكير #{reminder_id} لـ {datetime.fromtimestamp(due, timezone.utc):%Y-%m-%d %H:%M UTC}. خلّي البوت شغّال."
        return f"Follow-up #{reminder_id} scheduled for {datetime.fromtimestamp(due, timezone.utc):%Y-%m-%d %H:%M UTC}. Keep the bot running for delivery."
    if command == "/followups":
        return "\n".join(f"#{r['id']} — {datetime.fromtimestamp(r['due'], timezone.utc):%Y-%m-%d %H:%M UTC} — {r['status']} — {r['content']}" for r in memory.followups(owner)) or ("ما عندك تذكيرات بعد." if lebanese else "No pending follow-ups.")
    if command == "/cancel":
        if not argument.isdigit():
            return "Usage: /cancel <id>"
        cancelled = memory.cancel(owner, int(argument))
        if lebanese:
            return "انلغى التذكير." if cancelled else "ما لقيت هالتذكير."
        return "Follow-up cancelled." if cancelled else "Follow-up not found."


async def deliver_followups(session, config, memory):
    for reminder in memory.due():
        try:
            prefix = "تذكير: " if memory.preferred_language(reminder["owner"]) else "Follow-up: "
            await send_message(session, config, reminder["chat_id"], prefix + reminder["content"])
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
        await register_private_commands(session, config)
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
