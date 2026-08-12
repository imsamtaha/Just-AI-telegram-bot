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
    return data.get("output_text") or "I could not generate a response."
