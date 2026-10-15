import asyncio
from collections import defaultdict, deque
from hashlib import sha256
from hmac import compare_digest
import os
from pathlib import Path
from time import monotonic

import aiohttp
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import AssistantConfig, load_assistant_config, positive_int_env
from openai_client import create_openai_response


STATIC_DIR = Path(__file__).parent / "static"
RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_RATE_LIMIT_REQUESTS = 10

app = FastAPI(title="Just AI Telegram Bot Web", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
bearer_scheme = HTTPBearer(auto_error=False)
request_times: dict[str, deque[float]] = defaultdict(deque)
rate_limit_lock = asyncio.Lock()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    reply: str


class StatusResponse(BaseModel):
    configured: bool
    missing: list[str]
    model: str | None
    telegram_bot_configured: bool
    web_chat_auth_configured: bool


def missing_required_env() -> list[str]:
    return [
        name
        for name in ("OPENAI_API_KEY", "OPENAI_MODEL")
        if not os.getenv(name)
    ]


def safe_config() -> AssistantConfig:
    try:
        return load_assistant_config()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def authorize_chat(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Apply optional bearer authentication and rate-limit the caller."""
    expected_key = os.getenv("WEB_API_KEY")
    if expected_key and (
        credentials is None
        or not compare_digest(credentials.credentials, expected_key)
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")

    try:
        request_limit = positive_int_env(
            "WEB_RATE_LIMIT_REQUESTS", DEFAULT_RATE_LIMIT_REQUESTS
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    principal = (
        sha256(credentials.credentials.encode()).hexdigest()
        if expected_key and credentials is not None
        else "anonymous"
    )
    now = monotonic()
    async with rate_limit_lock:
        timestamps = request_times[principal]
        while timestamps and now - timestamps[0] >= RATE_LIMIT_WINDOW_SECONDS:
            timestamps.popleft()
        if len(timestamps) >= request_limit:
            raise HTTPException(status_code=429, detail="Web chat rate limit exceeded")
        timestamps.append(now)
    return principal


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    missing = missing_required_env()
    return StatusResponse(
        configured=not missing,
        missing=missing,
        model=os.getenv("OPENAI_MODEL"),
        telegram_bot_configured=bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        web_chat_auth_configured=bool(os.getenv("WEB_API_KEY")),
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _principal: str = Depends(authorize_chat),
) -> ChatResponse:
    config = safe_config()
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
        try:
            reply = await create_openai_response(
                session=session,
                api_key=config.openai_api_key,
                model=config.openai_model,
                system_prompt=config.system_prompt,
                user_text=request.message.strip(),
            )
        except aiohttp.ClientResponseError as exc:
            raise HTTPException(status_code=exc.status, detail="OpenAI request failed") from exc
        except asyncio.TimeoutError as exc:
            raise HTTPException(status_code=504, detail="OpenAI request timed out") from exc
        except aiohttp.ClientError as exc:
            raise HTTPException(status_code=502, detail="Could not reach OpenAI") from exc
    return ChatResponse(reply=reply)
