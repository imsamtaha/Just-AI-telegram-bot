"""Anthropic Messages API using the application's pooled HTTP session."""
from typing import Any

CLAUDE_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


async def create_claude_response(session: Any, api_key: str, model: str,
                                 system_prompt: str, user_text: str,
                                 history: list[dict[str, str]] | None = None) -> str:
    async with session.post(
        CLAUDE_MESSAGES_URL,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        json={"model": model, "system": system_prompt, "max_tokens": 2048,
              "messages": [*(history or []), {"role": "user", "content": user_text}]},
    ) as response:
        response.raise_for_status()
        data = await response.json()
    return "\n".join(block["text"] for block in data.get("content", [])
                     if block.get("type") == "text") or "I could not generate a response."
