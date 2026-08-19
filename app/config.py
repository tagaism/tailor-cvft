from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

DEFAULT_LLM_PROVIDER = "lmstudio"
DEFAULT_LLM_BASE_URL = "http://127.0.0.1:1234/v1"
# Dummy string the OpenAI SDK needs for local /v1 hosts. Not a credential.
LOCAL_LLM_API_KEY = "lm-studio"
LLM_PROVIDERS = ("lmstudio", "openai", "openrouter", "groq", "xai", "custom")


def normalize_llm_provider(value: Optional[str]) -> str:
    """Empty/missing → LM Studio. Unknown names fail instead of reaching the client."""
    name = (value or DEFAULT_LLM_PROVIDER).strip().lower().replace("-", "").replace("_", "")
    if not name:
        return DEFAULT_LLM_PROVIDER
    if name not in LLM_PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER {value!r}. Use one of: {', '.join(LLM_PROVIDERS)}."
        )
    return name


def parse_llm_timeout(value) -> Optional[float]:
    """Blank/None stays unset (provider preset). Non-numeric values fail with a clear error."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"LLM_TIMEOUT must be a number of seconds, got {value!r}.") from exc
    if timeout <= 0 or math.isnan(timeout):
        raise ValueError("LLM_TIMEOUT must be greater than 0.")
    return timeout


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = DEFAULT_LLM_PROVIDER
    # Empty means "use the provider preset". LM Studio still defaults to DEFAULT_LLM_BASE_URL.
    llm_base_url: str = ""
    # Empty is fine for LM Studio. The client sends LOCAL_LLM_API_KEY; cloud providers require a real key.
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: Optional[float] = None
    llm_in_docker: bool = False
    data_dir: Path = ROOT_DIR / "data"

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _default_and_validate_provider(cls, value):
        return normalize_llm_provider(value)

    @field_validator("llm_timeout", mode="before")
    @classmethod
    def _validate_timeout(cls, value):
        return parse_llm_timeout(value)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "resumeer.db"

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "profile.json"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def templates_dir(self) -> Path:
        return APP_DIR / "templates"

    @property
    def static_dir(self) -> Path:
        return APP_DIR / "static"


settings = Settings()


def ensure_data_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
