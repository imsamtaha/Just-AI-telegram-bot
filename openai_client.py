from typing import Any, Protocol


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class PostableSession(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any:
        ...


async def create_openai_response(
    session: PostableSession,
    api_key: str,
    model: str,
    system_prompt: str,
    user_text: str,
    history: list[dict[str, str]] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "instructions": system_prompt,
        "input": [*history, {"role": "user", "content": user_text}] if history else user_text,
    }
    if tools:
        payload.update(tools=tools, tool_choice="required", store=False)
    headers = {"Authorization": f"Bearer {api_key}"}
    async with session.post(OPENAI_RESPONSES_URL, json=payload, headers=headers) as response:
        response.raise_for_status()
        data = await response.json()
    text = data.get("output_text") or "\n".join(
        block["text"]
        for item in data.get("output", [])
        for block in item.get("content", [])
        if block.get("type") == "output_text"
    )
    return text or "I could not generate a response."
