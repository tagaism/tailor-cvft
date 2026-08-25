from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypedDict

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.config import DEFAULT_LLM_PROVIDER, LOCAL_LLM_API_KEY, settings
from app.llm_settings import ResolvedLlm, resolve_llm
from app.schemas import MatchAnalysis, Profile, ShokumuCv, ShokumuPack, TailorPack
from app.services.ground import ground_shokumu_cv

logger = logging.getLogger(__name__)
_JOB_TEXT_LIMIT = 18000
_CV_TEXT_LIMIT = 20000

PROFILE_SCHEMA_HINT = """
{
  "contact": {
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "website": ""
  },
  "summary": "",
  "skills": [
    "Languages: ...",
    "Databases: ...",
    "Frameworks: ...",
    "Technologies and Tools: ..."
  ],
  "additional_skills": ["Fluent in ..."],
  "experience": [
    {
      "title": "",
      "company": "",
      "location": "",
      "start": "",
      "end": "",
      "current": false,
      "projects": [{"summary": "what you did", "impact": "outcome or metric"}],
      "bullets": []
    }
  ],
  "education": [
    {"school": "", "degree": "", "field": "", "start": "", "end": "", "location": "", "details": ""}
  ],
  "projects": [
    {"name": "", "url": "", "description": "", "bullets": ["..."]}
  ],
  "certifications": [
    {"name": "", "issuer": "", "year": ""}
  ]
}
""".strip()

SHOKUMU_SCHEMA_HINT = """
{
  "as_of": "2026年8月24日",
  "name": "",
  "summary": "",
  "employers": [
    {
      "start": "2010年03月",
      "end": "2015年02月",
      "company": "",
      "business": "",
      "employment_type": "正社員として勤務",
      "capital": "",
      "revenue": "",
      "employees": "",
      "listing": "",
      "assignments": [
        {
          "start": "2010年03月",
          "end": "2015年02月",
          "department": "",
          "duties": "",
          "points": ""
        }
      ]
    }
  ],
  "pc_skills": [{"name": "", "level": ""}],
  "certifications": [{"name": "", "date": ""}],
  "self_pr": ""
}
""".strip()


class LLMError(Exception):
    pass


class LlmHealth(TypedDict):
    ok: bool
    provider: str
    model: str
    message: str
    checked_at: str


_RESOLVED_CACHE: ResolvedLlm | None = None


def _resolved() -> ResolvedLlm:
    """Return cached ``resolve_llm()`` or raise ``LLMError`` if config is incomplete.

    Settings come from ``.env`` at process start; a restart is required to pick up changes.
    Failures are not cached so a later call can succeed after a transient config read.
    """
    global _RESOLVED_CACHE
    if _RESOLVED_CACHE is not None:
        return _RESOLVED_CACHE
    try:
        llm = resolve_llm()
    except ValueError as exc:
        raise LLMError(str(exc)) from exc
    missing = llm.missing_config()
    if missing:
        raise LLMError(missing)
    _RESOLVED_CACHE = llm
    return llm


def openai_base_url() -> str:
    return _resolved().base_url


def _client(timeout: float | None = None, connect: float = 2.0) -> OpenAI:
    llm = _resolved()
    return OpenAI(
        api_key=llm.api_key or LOCAL_LLM_API_KEY,
        base_url=llm.base_url,
        timeout=httpx.Timeout(timeout if timeout is not None else llm.timeout, connect=connect),
    )


def resolve_model(client: OpenAI | None = None) -> str:
    llm = _resolved()
    configured = _model_id(llm.model)
    if configured:
        return configured
    if llm.model_required:
        raise LLMError(f"Set LLM_MODEL for {llm.label}.")
    client = client or _client()
    try:
        models = client.models.list()
    except Exception as exc:
        raise LLMError(_friendly_connection_error(exc, llm)) from exc
    ids = [item.id for item in getattr(models, "data", []) if getattr(item, "id", None)]
    chat_ids = [item for item in ids if "embed" not in item.lower()]
    chosen = chat_ids or ids
    if not chosen:
        raise LLMError(
            f"{llm.label} is reachable but no chat model is available. "
            "Set LLM_MODEL or load a model, then try again."
        )
    return chosen[0]


def _friendly_connection_error(exc: Exception, llm: ResolvedLlm | None = None) -> str:
    llm = llm or _resolved()
    if isinstance(exc, APITimeoutError):
        extra = (
            " Local models often spend a minute reasoning before they write JSON."
            if llm.local
            else ""
        )
        return (
            f"{llm.label} took longer than {int(llm.timeout)}s.{extra} "
            "Keep the tab open and try Build again. Raise LLM_TIMEOUT in .env if needed."
        )
    if isinstance(exc, APIConnectionError):
        hint = (
            " Start the local server (Developer tab, port 1234) and load a model."
            if llm.local
            else " Check LLM_BASE_URL, LLM_API_KEY, and network access."
        )
        return f"Cannot reach {llm.label} at {llm.base_url}.{hint}"
    if isinstance(exc, APIStatusError):
        return f"{llm.label} returned HTTP {exc.status_code}: {exc.message}"
    return f"{llm.label} request failed: {exc}"


_HEALTH_CACHE: tuple[float, LlmHealth] | None = None
_HEALTH_TTL_SECONDS = 20.0


def _model_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _health_model_message(label: str, model: Any) -> str:
    name = _model_id(model)
    return f"{label} · {name}" if name else label


def _health(*, ok: bool, provider: str, model: str, message: str) -> LlmHealth:
    return {
        "ok": ok,
        "provider": provider,
        "model": model,
        "message": message,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def llm_health() -> LlmHealth:
    """Never block a page on the model host. Prefer a short HTTP probe over the SDK."""
    global _HEALTH_CACHE
    now = time.time()
    if _HEALTH_CACHE and now - _HEALTH_CACHE[0] < _HEALTH_TTL_SECONDS:
        return _HEALTH_CACHE[1]
    try:
        llm = resolve_llm()
    except ValueError as exc:
        result = _health(
            ok=False,
            provider=settings.llm_provider or DEFAULT_LLM_PROVIDER,
            model="",
            message=str(exc),
        )
        _HEALTH_CACHE = (now, result)
        return result
    configured = _model_id(llm.model)
    missing = llm.missing_config()
    if missing:
        result = _health(ok=False, provider=llm.provider, model=configured, message=missing)
        _HEALTH_CACHE = (now, result)
        return result
    try:
        headers = {}
        if llm.api_key:
            headers["Authorization"] = f"Bearer {llm.api_key}"
        response = httpx.get(
            f"{llm.base_url}/models",
            headers=headers,
            timeout=httpx.Timeout(0.8, connect=0.4),
        )
        response.raise_for_status()
        payload = response.json()
        ids = [
            item.get("id")
            for item in payload.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]
        chat_ids = [item for item in ids if "embed" not in item.lower()]
        available = chat_ids or ids
        if configured:
            if available and configured not in available:
                result = _health(
                    ok=False,
                    provider=llm.provider,
                    model=configured,
                    message=(
                        f"{llm.label} is reachable but {configured} is not available. "
                        "Set LLM_MODEL to a loaded chat model."
                    ),
                )
            else:
                result = _health(
                    ok=True,
                    provider=llm.provider,
                    model=configured,
                    message=_health_model_message(llm.label, configured),
                )
        elif not available:
            result = _health(
                ok=False,
                provider=llm.provider,
                model="",
                message=(
                    f"{llm.label} is reachable but no model is available. "
                    "Set LLM_MODEL or load a model."
                ),
            )
        else:
            model = available[0]
            result = _health(
                ok=True,
                provider=llm.provider,
                model=model,
                message=_health_model_message(llm.label, model),
            )
    except Exception:
        result = _health(
            ok=False,
            provider=llm.provider,
            model=configured,
            message=(
                f"Cannot reach {llm.label} at {llm.base_url}."
                + (
                    " Start the local server and load a model."
                    if llm.local
                    else " Check LLM_API_KEY and LLM_BASE_URL."
                )
            ),
        )
    _HEALTH_CACHE = (now, result)
    return result


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    for candidate in (cleaned, _close_truncated_json(cleaned)):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise LLMError("The model did not return complete JSON. Try building again.")


def _close_truncated_json(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return text
    chunk = text[start:]
    stack: list[str] = []
    in_string = False
    escape = False
    for char in chunk:
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in "}]" and stack and stack[-1] == char:
            stack.pop()
    if in_string:
        chunk += '"'
    while stack:
        chunk += stack.pop()
    return chunk


class _ReasoningWindow:
    """Keep the newest complete reasoning lines for the live UI (about four rows)."""

    def __init__(self, max_lines: int = 4):
        self.max_lines = max_lines
        self._text = ""

    def push(self, chunk: str) -> list[str]:
        if not chunk:
            return self.lines
        self._text += chunk.replace("\r\n", "\n").replace("\r", "\n")
        return self.lines

    @property
    def lines(self) -> list[str]:
        parts = self._text.split("\n")
        if parts and parts[-1] == "":
            parts = parts[:-1]
        return [part for part in parts if part.strip()][-self.max_lines :]


def _delta_reasoning_text(delta: Any) -> str:
    if delta is None:
        return ""
    dumped: dict[str, Any] = {}
    if hasattr(delta, "model_dump"):
        try:
            dumped = delta.model_dump(exclude_none=True)
        except Exception:
            dumped = {}
    for key in ("reasoning", "reasoning_content"):
        value = dumped.get(key)
        if value is None:
            value = getattr(delta, key, None)
        if isinstance(value, str) and value:
            return value
    details = dumped.get("reasoning_details")
    if details is None:
        details = getattr(delta, "reasoning_details", None)
    if isinstance(details, list):
        parts: list[str] = []
        for item in details:
            if isinstance(item, dict):
                text = item.get("text") or item.get("summary") or ""
            else:
                text = getattr(item, "text", None) or getattr(item, "summary", None) or ""
            if isinstance(text, str) and text:
                parts.append(text)
        return "".join(parts)
    return ""


def _reasoning_request_kwargs() -> dict[str, Any]:
    provider = _resolved().provider
    if provider in {"openrouter", "xai", "openai"}:
        return {"extra_body": {"reasoning": {"effort": "medium"}}}
    return {}


def _stream_completion(
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    extra: dict[str, Any],
    on_reasoning: Callable[[list[str]], None] | None,
) -> str:
    window = _ReasoningWindow()
    last_emit = 0.0

    def emit(force: bool = False) -> None:
        nonlocal last_emit
        if on_reasoning is None or not window.lines:
            return
        now = time.monotonic()
        if not force and now - last_emit < 0.1:
            return
        last_emit = now
        on_reasoning(window.lines)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 8192,
        "stream": True,
    }
    try:
        stream = client.chat.completions.create(**kwargs, **extra)
    except APIStatusError as exc:
        if extra and exc.status_code in {400, 422}:
            logger.info("Retrying stream without reasoning extras: %s", exc.message)
            stream = client.chat.completions.create(**kwargs)
        else:
            raise
    content_parts: list[str] = []
    for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = choices[0].delta
        reasoning = _delta_reasoning_text(delta)
        if reasoning:
            window.push(reasoning)
            emit()
        piece = getattr(delta, "content", None) or ""
        if piece:
            content_parts.append(piece)
    emit(force=True)
    return "".join(content_parts).strip()


def complete_json(
    system: str,
    user: str,
    on_reasoning: Callable[[list[str]], None] | None = None,
) -> tuple[dict[str, Any], str]:
    client = _client()
    model = resolve_model(client)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    extra = _reasoning_request_kwargs() if on_reasoning else {}
    last_error: Exception | None = None
    for attempt in range(2):
        if attempt == 1:
            messages.append(
                {
                    "role": "user",
                    "content": "Your previous reply was not valid JSON. Reply with a single JSON object only. No markdown, no commentary.",
                }
            )
        try:
            if on_reasoning:
                content = _stream_completion(client, model, messages, extra, on_reasoning)
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=8192,
                )
                content = (response.choices[0].message.content or "").strip()
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(_friendly_connection_error(exc)) from exc
        try:
            return extract_json_object(content), model
        except (LLMError, json.JSONDecodeError) as exc:
            last_error = exc
            messages.append({"role": "assistant", "content": content})
            time.sleep(0.2)
    raise LLMError(str(last_error) if last_error else "Could not parse model JSON.")


def extract_profile_from_cv(raw_text: str) -> tuple[Profile, str]:
    system = (
        "You extract a structured resume profile from raw CV text. "
        "Return ONLY valid JSON matching the schema. "
        "Do not invent facts. If a field is missing, use an empty string or empty array. "
        "Keep dates as originally written. Split experience into distinct roles. "
        "For each role, list projects with a short summary and impact (metrics or outcomes if present). "
        "Leave impact empty if unknown. Do not invent facts."
    )
    user = (
        f"JSON schema:\n{PROFILE_SCHEMA_HINT}\n\n"
        f"Raw CV text:\n{_clip(raw_text, _CV_TEXT_LIMIT, label='CV text')}"
    )
    data, model = complete_json(system, user)
    try:
        return Profile.model_validate(data), model
    except Exception as exc:
        raise LLMError(f"Could not read a profile from the model JSON: {exc}") from exc


def tailor_pack(
    profile: Profile,
    job_text: str,
    notes: str,
    title: str,
    company: str,
    required_skills: list[str] | None = None,
    desired_skills: list[str] | None = None,
    on_reasoning: Callable[[list[str]], None] | None = None,
) -> tuple[TailorPack, str]:
    system = (
        "You are a precise resume tailor. You rewrite one candidate’s existing profile for one specific job.\n\n"
        "HARD RULES (never break these):\n"
        "- Use ONLY facts that already exist in the provided profile. Never invent employers, titles, dates, "
        "degrees, metrics, tools, skills, achievements, or responsibilities.\n"
        "- You MAY rephrase, reorder, drop low-relevance items, and adopt the job’s wording when it honestly "
        "describes work the candidate has already done.\n"
        "- If a fact is not in the profile, omit it. Do not approximate or fill gaps.\n\n"
        "SKILLS FORMAT (strict):\n"
        "- Technical Skills must be exactly these four lines (omit any line that would be empty):\n"
        "  Languages: ...\n"
        "  Databases: ...\n"
        "  Frameworks: ...\n"
        "  Technologies and Tools: ...\n"
        "- additional_skills: array of spoken languages or other extras that already appear in the profile. "
        "Use [] if none.\n\n"
        "CONTENT GUIDELINES:\n"
        "- summary: 2–4 sentences, tailored, facts only. Placed under the name and above Technical Skills.\n"
        "- Up to two pages friendly: 3–6 bullets per recent role; fewer for older roles.\n"
        "- Experience: 3–6 bullets for recent roles, fewer for older roles. Strong action verbs, truthful only.\n"
        "- Cover letter: 180–250 words, plain text paragraphs, specific to this job and company, no fabricated claims.\n"
        "- Match analysis must be honest and concise.\n\n"
        "OUTPUT:\n"
        "- Return one complete JSON object that exactly follows the output_schema provided in the user message.\n"
        "- No markdown fences, no commentary, no text before or after the JSON.\n"
        "- Do not stop mid-string."
    )
    user = {
        "job_title": title,
        "company": company,
        "job_description": _clip(job_text, _JOB_TEXT_LIMIT, label="job description"),
        "required_skills": required_skills or [],
        "desired_skills": desired_skills or [],
        "candidate_notes": notes,
        "profile": profile.model_dump(),
        "output_schema": {
            "cv": json.loads(PROFILE_SCHEMA_HINT),
            "cover_letter": "plain text",
            "match": {
                "matched_skills": ["..."],
                "missing_skills": ["..."],
                "keyword_coverage": [{"keyword": "...", "present": True}],
                "emphasis": ["what you leaned on and why"],
                "gaps": ["honest gaps"],
                "talking_points": ["interview talking points grounded in the profile"],
            },
        },
    }
    data, model = complete_json(
        system, json.dumps(user, ensure_ascii=False, indent=2), on_reasoning=on_reasoning
    )
    try:
        cv = Profile.model_validate(data.get("cv") or {})
        match = MatchAnalysis.model_validate(_normalize_match(data.get("match")))
    except Exception as exc:
        raise LLMError(f"Model JSON did not match the expected schema: {exc}") from exc
    pack = TailorPack(
        cv=cv,
        cover_letter=str(data.get("cover_letter") or "").strip(),
        match=match,
    )
    return pack, model


def _clip(text: str, limit: int, *, label: str) -> str:
    raw = text or ""
    if len(raw) <= limit:
        return raw
    logger.warning("Truncating %s from %s to %s characters", label, len(raw), limit)
    return raw[:limit]


def _normalize_match(raw_match) -> dict[str, Any]:
    if not isinstance(raw_match, dict):
        return {}
    coverage = raw_match.get("keyword_coverage") or []
    if isinstance(coverage, list):
        normalized = []
        for item in coverage:
            if isinstance(item, str):
                normalized.append({"keyword": item, "present": False})
            else:
                normalized.append(item)
        raw_match = dict(raw_match)
        raw_match["keyword_coverage"] = normalized
    return raw_match


def tailor_shokumu_pack(
    profile: Profile,
    job_text: str,
    notes: str,
    title: str,
    company: str,
    required_skills: list[str] | None = None,
    desired_skills: list[str] | None = None,
    on_reasoning: Callable[[list[str]], None] | None = None,
) -> tuple[ShokumuPack, str]:
    now = datetime.now(timezone.utc)
    today = f"{now.year}年{now.month}月{now.day}日"
    system = (
        "あなたは日本の職務経歴書（Googleスプレッドシート定型）の作成者です。"
        "候補者の既存プロフィールだけを使い、日本語の職務経歴書と志望動機を書く。\n"
        "HARD RULES:\n"
        "- プロフィールにある事実のみ。雇用主・役職・年月・学位・数値・資本金・売上・従業員数・上場を捏造しない。\n"
        "- 不明な会社概要（資本金・売上高・従業員数・上場）は空文字。\n"
        "- 雇用形態が不明なら「正社員として勤務」。事業内容は分かる範囲のみ。\n"
        "- 和名が不明ならプロフィールの氏名をそのまま使う。会社名はプロフィールの表記のまま。\n"
        "- 職務経歴は会社ごとにまとめる。各社の assignments に期間・部署・【職務内容】・【ポイント】を書く。\n"
        "- 各社 experience.projects の summary を【職務内容】、impact を【ポイント】に対応させる。\n"
        "- 職務内容は具体。ポイントはプロフィールにある成果・数値のみ。\n"
        "- PCスキルはプロフィールのツールを name/level で。Officeに無いものは無理にWord/Excelにしない。\n"
        "- 資格は name と取得年月（不明なら空）。自己PRは＜見出し＞付き2テーマ程度。\n"
        "- 職務要約は3–6文。志望動機は250–400字、この求人向け、事実のみ。\n"
        "- match は英語の短い正直な分析（各リスト最大6）。\n"
        "- JSONオブジェクト1つだけ返す。キーは cv, cover_letter, match。"
    )
    user = {
        "as_of": today,
        "job_title": title,
        "company": company,
        "job_description": _clip(job_text, _JOB_TEXT_LIMIT, label="job description"),
        "required_skills": required_skills or [],
        "desired_skills": desired_skills or [],
        "candidate_notes": notes,
        "profile": profile.model_dump(),
        "output_schema": {
            "cv": json.loads(SHOKUMU_SCHEMA_HINT),
            "cover_letter": "志望動機（日本語プレーンテキスト）",
            "match": {
                "matched_skills": ["..."],
                "missing_skills": ["..."],
                "keyword_coverage": [{"keyword": "...", "present": True}],
                "emphasis": ["..."],
                "gaps": ["..."],
                "talking_points": ["..."],
            },
        },
    }
    data, model = complete_json(
        system, json.dumps(user, ensure_ascii=False, indent=2), on_reasoning=on_reasoning
    )
    try:
        cv = ShokumuCv.model_validate(data.get("cv") or {})
        match = MatchAnalysis.model_validate(_normalize_match(data.get("match")))
    except Exception as exc:
        raise LLMError(f"Model JSON did not match the expected schema: {exc}") from exc
    cv.as_of = today
    cv = ground_shokumu_cv(cv, profile)
    pack = ShokumuPack(
        cv=cv,
        cover_letter=str(data.get("cover_letter") or "").strip(),
        match=match,
    )
    return pack, model
