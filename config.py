import os
from dataclasses import dataclass


DEFAULT_SYSTEM_PROMPT = "You are a concise, helpful Telegram assistant."
DEFAULT_POLL_TIMEOUT = 30


@dataclass(frozen=True)
class AssistantConfig:
    openai_api_key: str
    openai_model: str
    system_prompt: str


@dataclass(frozen=True)
class BotConfig(AssistantConfig):
    telegram_bot_token: str
    poll_timeout: int

    @property
    def telegram_api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.telegram_bot_token}"


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_assistant_config() -> AssistantConfig:
    return AssistantConfig(
        openai_api_key=required_env("OPENAI_API_KEY"),
        openai_model=required_env("OPENAI_MODEL"),
        system_prompt=os.getenv("BOT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
    )


def load_bot_config() -> BotConfig:
    assistant = load_assistant_config()
    return BotConfig(
        openai_api_key=assistant.openai_api_key,
        openai_model=assistant.openai_model,
        system_prompt=assistant.system_prompt,
        telegram_bot_token=required_env("TELEGRAM_BOT_TOKEN"),
        poll_timeout=int(os.getenv("POLL_TIMEOUT", str(DEFAULT_POLL_TIMEOUT))),
    )
