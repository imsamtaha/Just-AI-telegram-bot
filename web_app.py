import os
from pathlib import Path

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import AssistantConfig, load_assistant_config
from openai_client import create_openai_response


STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Just AI Telegram Bot Web", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    reply: str


class StatusResponse(BaseModel):
    configured: bool
    missing: list[str]
    model: str | None
    telegram_bot_configured: bool


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
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
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
        except aiohttp.ClientError as exc:
            raise HTTPException(status_code=502, detail="Could not reach OpenAI") from exc
    return ChatResponse(reply=reply)
