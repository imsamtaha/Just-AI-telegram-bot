"""Small, resilient asynchronous client for the Telegram Bot API."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

TELEGRAM_MESSAGE_LIMIT = 4096
DEFAULT_RETRIES = 3


class TelegramAPIError(RuntimeError):
    """An unsuccessful Telegram API response, without exposing request credentials."""

    def __init__(self, status: int, description: str, retry_after: float | None = None):
        super().__init__(f"Telegram API error {status}: {description}")
        self.status = status
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        return self.status in {408, 425, 429} or self.status >= 500


class TelegramClient:
    """Telegram API wrapper that validates responses and retries transient failures.

    Reuse one instance with an application-scoped ``aiohttp.ClientSession``. Network
    retries are intentionally bounded; a send whose response was lost may be
    delivered more than once, as Telegram does not provide idempotency keys.
    """

    def __init__(
        self,
        session: Any,
        api_base: str,
        *,
        retries: int = DEFAULT_RETRIES,
        sleep=asyncio.sleep,
    ) -> None:
        self.session = session
        self.api_base = api_base.rstrip("/")
        self.retries = max(0, retries)
        self._sleep = sleep

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        url = f"{self.api_base}/{endpoint}"
        request = getattr(self.session, method)
        for attempt in range(self.retries + 1):
            try:
                async with request(url, **kwargs) as response:
                    status = getattr(response, "status", 200)
                    json_method = getattr(response, "json", None)
                    data = await json_method() if json_method is not None else {}
                    if isinstance(data, dict) and data.get("ok") is False:
                        parameters = data.get("parameters") or {}
                        retry_after = parameters.get("retry_after")
                        try:
                            retry_after = float(retry_after) if retry_after is not None else None
                        except (TypeError, ValueError):
                            retry_after = None
                        error = TelegramAPIError(
                            int(data.get("error_code", status)),
                            str(data.get("description", "request failed")),
                            retry_after,
                        )
                    elif status >= 400:
                        error = TelegramAPIError(status, "HTTP request failed")
                    elif not isinstance(data, dict):
                        raise TelegramAPIError(status, "invalid JSON response")
                    else:
                        return data.get("result")
            except TelegramAPIError as exc:
                error = exc
            except (asyncio.TimeoutError, getattr(aiohttp, "ClientError", OSError)) as exc:
                if attempt >= self.retries:
                    raise TelegramAPIError(0, "network request failed") from exc
                await self._backoff(attempt)
                continue

            if not error.retryable or attempt >= self.retries:
                raise error
            await self._backoff(attempt, error.retry_after)

        raise TelegramAPIError(0, "request retries exhausted")

    async def _backoff(self, attempt: int, retry_after: float | None = None) -> None:
        delay = retry_after if retry_after is not None else min(0.5 * (2**attempt), 5.0)
        await self._sleep(max(0.0, min(delay, 30.0)))

    async def get_updates(self, *, timeout: int, offset: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "edited_message"],
        }
        if offset is not None:
            params["offset"] = offset
        result = await self._request("get", "getUpdates", params=params)
        if not isinstance(result, list):
            raise TelegramAPIError(200, "getUpdates returned an invalid result")
        return result

    async def send_text(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        """Send text in Telegram-sized UTF-16 chunks, preserving chunk order."""
        text = text or "I could not generate a response."
        chunks: list[str] = []
        current: list[str] = []
        units = 0
        for character in text:
            size = 2 if ord(character) > 0xFFFF else 1
            if units + size > TELEGRAM_MESSAGE_LIMIT:
                chunks.append("".join(current))
                current = []
                units = 0
            current.append(character)
            units += size
        if current:
            chunks.append("".join(current))

        for index, chunk in enumerate(chunks):
            payload: dict[str, Any] = {"chat_id": chat_id, "text": chunk}
            if index == 0 and reply_markup is not None:
                payload["reply_markup"] = reply_markup
            await self._request("post", "sendMessage", json=payload)


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split text by UTF-16 code units (useful for callers and unit tests)."""
    if limit < 2:
        raise ValueError("limit must be at least 2 UTF-16 code units")
    chunks: list[str] = []
    current: list[str] = []
    units = 0
    for character in text or "I could not generate a response.":
        size = 2 if ord(character) > 0xFFFF else 1
        if units + size > limit:
            chunks.append("".join(current))
            current, units = [], 0
        current.append(character)
        units += size
    if current:
        chunks.append("".join(current))
    return chunks
