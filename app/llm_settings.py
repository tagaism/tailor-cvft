from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.config import settings

PROVIDERS = ("lmstudio", "openai", "openrouter", "groq", "xai", "custom")

_PRESETS: dict[str, dict] = {
    "lmstudio": {
        "label": "LM Studio",
        "base_url": "http://127.0.0.1:1234/v1",
        "local": True,
        "key_required": False,
        "model_required": False,
        "timeout": 600.0,
        "placeholder_key": "lm-studio",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
        "placeholder_key": "",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
        "placeholder_key": "",
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
        "placeholder_key": "",
    },
    "xai": {
        "label": "xAI",
        "base_url": "https://api.x.ai/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
        "placeholder_key": "",
    },
    "custom": {
        "label": "Custom",
        "base_url": "",
        "local": False,
        "key_required": False,
        "model_required": False,
        "timeout": 180.0,
        "placeholder_key": "",
    },
}


@dataclass(frozen=True)
class ResolvedLlm:
    provider: str
    label: str
    base_url: str
    api_key: str
    model: str
    timeout: float
    local: bool
    key_required: bool
    model_required: bool

    def missing_config(self) -> str:
        if self.provider == "custom" and not self.base_url:
            return "Set LLM_BASE_URL for a custom OpenAI-compatible host."
        if self.key_required and not self.api_key:
            return f"Set LLM_API_KEY for {self.label}."
        if self.model_required and not self.model:
            return f"Set LLM_MODEL for {self.label}."
        return ""


def parse_provider(value: str | None) -> str:
    name = (value or "lmstudio").strip().lower().replace("-", "").replace("_", "")
    aliases = {
        "lmstudio": "lmstudio",
        "openai": "openai",
        "openrouter": "openrouter",
        "groq": "groq",
        "xai": "xai",
        "custom": "custom",
    }
    if name not in aliases:
        raise ValueError(
            f"Unknown LLM_PROVIDER {value!r}. Use one of: {', '.join(PROVIDERS)}."
        )
    return aliases[name]


def _normalize_base_url(url: str) -> str:
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return ""
    if not raw.endswith("/v1"):
        raw = f"{raw}/v1"
    return raw


def _host_is_local(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "host.docker.internal"}


def _in_docker() -> bool:
    if settings.llm_in_docker:
        return True
    return Path("/.dockerenv").exists()


def _rewrite_docker_localhost(url: str) -> str:
    if not _in_docker():
        return url
    return (
        url.replace("://127.0.0.1", "://host.docker.internal")
        .replace("://localhost", "://host.docker.internal")
    )


def resolve_llm() -> ResolvedLlm:
    try:
        provider = parse_provider(settings.llm_provider)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    preset = _PRESETS[provider]
    override = (settings.llm_base_url or "").strip()
    base_url = _normalize_base_url(override or preset["base_url"])
    local = bool(preset["local"] or (provider == "custom" and _host_is_local(base_url)))
    if local:
        base_url = _rewrite_docker_localhost(base_url)
    key = (settings.llm_api_key or "").strip()
    if not key:
        key = preset["placeholder_key"]
    timeout = settings.llm_timeout if settings.llm_timeout is not None else float(preset["timeout"])
    model_required = bool(preset["model_required"])
    if provider == "custom" and not local:
        model_required = True
    return ResolvedLlm(
        provider=provider,
        label=str(preset["label"]),
        base_url=base_url,
        api_key=key,
        model=(settings.llm_model or "").strip(),
        timeout=float(timeout),
        local=local,
        key_required=bool(preset["key_required"]),
        model_required=model_required,
    )
