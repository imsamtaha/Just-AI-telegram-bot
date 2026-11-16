import asyncio
import logging
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


async def call_openai(session: aiohttp.ClientSession, config: BotConfig, user_text: str, system_prompt: str | None = None) -> str:
    create_response = create_claude_response if config.ai_provider == "claude" else create_openai_response
    return await create_response(session=session, api_key=config.openai_api_key, model=config.openai_model, system_prompt=system_prompt or config.system_prompt, user_text=user_text)


async def send_message(
    session: aiohttp.ClientSession,
    config: BotConfig,
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:TELEGRAM_MESSAGE_LIMIT]}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    async with session.post(f"{config.telegram_api_base}/sendMessage", json=payload) as response:
        response.raise_for_status()


def is_atlas_command(text: str) -> bool:
    """Recognize /atlas, including Telegram's /atlas@botname group syntax."""
    command = text.strip().split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower() if text.strip() else ""
    return command == "/atlas"


async def handle_update(session: aiohttp.ClientSession, config: BotConfig, update: dict[str, Any]) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message or "text" not in message:
        return

    chat_id = message["chat"]["id"]
    user_text = message["text"].strip()
    if not user_text:
        return

    mode, brief = parse_creative_command(user_text)
    if user_text.lower() in {"/start", "/help", "/creative"}:
        await send_message(session, config, chat_id, creative_help() + "\n/atlas — open the ATLAS dashboard")
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

    try:
        answer = await call_openai(session, config, request_text, system_prompt)
    except Exception:
        LOGGER.error("AI request failed")
        answer = "Sorry, I could not reach the AI service right now."

    await send_message(session, config, chat_id, answer)


async def poll_updates(config: BotConfig) -> None:
    offset: int | None = None
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
        while True:
            params: dict[str, Any] = {"timeout": config.poll_timeout, "allowed_updates": ["message", "edited_message"]}
            if offset is not None:
                params["offset"] = offset

            try:
                async with session.get(f"{config.telegram_api_base}/getUpdates", params=params) as response:
                    response.raise_for_status()
                    payload = await response.json()
            except Exception:
                LOGGER.exception("Telegram polling failed")
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
                            await handle_update(session, config, update)
                        except Exception:
                            LOGGER.error("Update delivery failed: %s", update.get("update_id"))

            await asyncio.gather(*(process_chat(updates) for updates in chats.values()))


if __name__ == "__main__":
    asyncio.run(poll_updates(load_bot_config()))
