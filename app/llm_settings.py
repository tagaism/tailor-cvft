from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.config import (
    DEFAULT_LLM_BASE_URL,
    LLM_PROVIDERS,
    LOCAL_LLM_API_KEY,
    normalize_llm_provider,
    parse_llm_timeout,
    settings,
)

PROVIDERS = LLM_PROVIDERS

# Do not treat the local SDK dummy as a real key (old .env files still have it).
PLACEHOLDER_API_KEYS = frozenset({LOCAL_LLM_API_KEY.lower()})

_PRESETS: dict[str, dict] = {
    "lmstudio": {
        "label": "LM Studio",
        "base_url": DEFAULT_LLM_BASE_URL,
        "local": True,
        "key_required": False,
        "model_required": False,
        "timeout": 600.0,
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
    },
    "xai": {
        "label": "xAI",
        "base_url": "https://api.x.ai/v1",
        "local": False,
        "key_required": True,
        "model_required": True,
        "timeout": 120.0,
    },
    "custom": {
        "label": "Custom",
        "base_url": "",
        "local": False,
        "key_required": False,
        # Required for remote hosts. _model_required() drops this when the URL is local.
        "model_required": True,
        "timeout": 180.0,
    },
}


@dataclass(frozen=True)
class ResolvedLlm:
    """Effective LLM client settings after applying .env on top of a provider preset.

    ``resolve_llm()`` builds this: pick ``LLM_PROVIDER`` (default lmstudio), take that
    preset's base URL / timeout / key-and-model rules, then overlay ``LLM_BASE_URL``,
    ``LLM_API_KEY``, ``LLM_MODEL``, and ``LLM_TIMEOUT``. Empty overlays keep the preset.
    A leftover localhost ``LLM_BASE_URL`` is ignored for named cloud providers. Local
    hosts (LM Studio, or custom on 127.0.0.1 / localhost / host.docker.internal) can
    omit the model; Docker rewrites localhost to host.docker.internal. ``api_key`` is
    empty when unset or still the local dummy — not a real credential.
    """

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
        if self.key_required and not _effective_api_key(self.api_key):
            return f"Set LLM_API_KEY for {self.label}."
        if self.model_required and not self.model:
            return f"Set LLM_MODEL for {self.label}."
        return ""


def _effective_api_key(value: str | None) -> str:
    key = (value or "").strip()
    if key.lower() in PLACEHOLDER_API_KEYS:
        return ""
    return key


def parse_provider(value: str | None) -> str:
    return normalize_llm_provider(value)


def _resolve_timeout(value, fallback) -> float:
    parsed = parse_llm_timeout(value)
    if parsed is not None:
        return parsed
    try:
        timeout = float(fallback)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"LLM_TIMEOUT must be a number of seconds, got {fallback!r}.") from exc
    if timeout <= 0:
        raise ValueError("LLM_TIMEOUT must be greater than 0.")
    return timeout


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


def _base_url_override(provider: str, raw: str) -> str:
    """User LLM_BASE_URL, or empty to use the preset.

    Older .env files set the LM Studio URL for every provider. Ignore that leftover
    on named cloud presets so switching to OpenAI/OpenRouter does not stay on localhost.
    """
    override = (raw or "").strip()
    if not override:
        return ""
    if provider not in {"lmstudio", "custom"} and _host_is_local(override):
        return ""
    return override


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


def _model_required(preset: dict, *, local: bool) -> bool:
    """Local /v1 hosts can list models. Remote hosts use the preset (custom: required)."""
    if local:
        return False
    return bool(preset["model_required"])


def resolve_llm() -> ResolvedLlm:
    """Merge Settings with the provider preset into a ``ResolvedLlm``."""
    try:
        provider = parse_provider(settings.llm_provider)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    preset = _PRESETS[provider]
    override = _base_url_override(provider, settings.llm_base_url)
    base_url = _normalize_base_url(override or preset["base_url"])
    local = bool(preset["local"] or (provider == "custom" and _host_is_local(base_url)))
    if local:
        base_url = _rewrite_docker_localhost(base_url)
    key = _effective_api_key(settings.llm_api_key)
    timeout = _resolve_timeout(settings.llm_timeout, preset["timeout"])
    return ResolvedLlm(
        provider=provider,
        label=str(preset["label"]),
        base_url=base_url,
        api_key=key,
        model=(settings.llm_model or "").strip(),
        timeout=timeout,
        local=local,
        key_required=bool(preset["key_required"]),
        model_required=_model_required(preset, local=local),
    )
