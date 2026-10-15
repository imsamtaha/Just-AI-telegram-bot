from typing import Any, Protocol


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
FALLBACK_RESPONSE = "I could not generate a response."


class PostableSession(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any:
        ...


def _extract_output_text(data: Any) -> str | None:
    """Extract assistant text from a raw Responses API JSON payload."""
    if not isinstance(data, dict):
        return None

    text_parts: list[str] = []
    output = data.get("output")
    if not isinstance(output, list):
        return None

    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str):
                text_parts.append(text)

    return "".join(text_parts) or None


async def create_openai_response(
    session: PostableSession,
    api_key: str,
    model: str,
    system_prompt: str,
    user_text: str,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "instructions": system_prompt,
        "input": user_text,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    async with session.post(OPENAI_RESPONSES_URL, json=payload, headers=headers) as response:
        response.raise_for_status()
        data = await response.json()
    return _extract_output_text(data) or FALLBACK_RESPONSE
