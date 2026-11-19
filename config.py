import os
from dataclasses import dataclass, field


DEFAULT_SYSTEM_PROMPT = "You are a concise, helpful Telegram assistant."
DEFAULT_POLL_TIMEOUT = 30
DEFAULT_ATLAS_DASHBOARD_URL = "https://atlas-market.imsamtaha.chatgpt.site"


@dataclass(frozen=True)
class AssistantConfig:
    openai_api_key: str
    openai_model: str
    system_prompt: str
    ai_provider: str = field(default="openai", kw_only=True)


@dataclass(frozen=True)
class BotConfig(AssistantConfig):
    telegram_bot_token: str
    poll_timeout: int
    atlas_dashboard_url: str = DEFAULT_ATLAS_DASHBOARD_URL

    @property
    def telegram_api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.telegram_bot_token}"


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_assistant_config() -> AssistantConfig:
    provider = os.getenv("AI_PROVIDER", "openai").strip().lower()
    if provider not in {"openai", "claude"}:
        raise RuntimeError("AI_PROVIDER must be openai or claude")
    prefix = "ANTHROPIC" if provider == "claude" else "OPENAI"
    return AssistantConfig(
        ai_provider=provider,
        openai_api_key=required_env(f"{prefix}_API_KEY"),
        openai_model=required_env(f"{prefix}_MODEL"),
        system_prompt=os.getenv("BOT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
    )


def load_bot_config() -> BotConfig:
    assistant = load_assistant_config()
    return BotConfig(
        ai_provider=assistant.ai_provider,
        openai_api_key=assistant.openai_api_key,
        openai_model=assistant.openai_model,
        system_prompt=assistant.system_prompt,
        telegram_bot_token=required_env("TELEGRAM_BOT_TOKEN"),
        poll_timeout=int(os.getenv("POLL_TIMEOUT", str(DEFAULT_POLL_TIMEOUT))),
        atlas_dashboard_url=os.getenv("ATLAS_DASHBOARD_URL", DEFAULT_ATLAS_DASHBOARD_URL).strip(),
    )
