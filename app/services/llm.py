from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.llm_settings import ResolvedLlm, resolve_llm
from app.schemas import MatchAnalysis, Profile, TailorPack

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
      "bullets": ["..."]
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


class LLMError(Exception):
    pass


def _resolved() -> ResolvedLlm:
    try:
        llm = resolve_llm()
    except ValueError as exc:
        raise LLMError(str(exc)) from exc
    missing = llm.missing_config()
    if missing:
        raise LLMError(missing)
    return llm


def openai_base_url() -> str:
    return _resolved().base_url


def _client(timeout: float | None = None, connect: float = 2.0) -> OpenAI:
    llm = _resolved()
    return OpenAI(
        api_key=llm.api_key or "lm-studio",
        base_url=llm.base_url,
        timeout=httpx.Timeout(timeout if timeout is not None else llm.timeout, connect=connect),
    )


def resolve_model(client: OpenAI | None = None) -> str:
    llm = _resolved()
    if llm.model:
        return llm.model
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


_HEALTH_CACHE: tuple[float, dict[str, Any]] | None = None
_HEALTH_TTL_SECONDS = 20.0


def llm_health() -> dict[str, Any]:
    """Never block a page on the model host. Prefer a short HTTP probe over the SDK."""
    global _HEALTH_CACHE
    now = time.time()
    if _HEALTH_CACHE and now - _HEALTH_CACHE[0] < _HEALTH_TTL_SECONDS:
        return _HEALTH_CACHE[1]
    try:
        llm = resolve_llm()
    except ValueError as exc:
        result = {"ok": False, "provider": "", "model": "", "message": str(exc)}
        _HEALTH_CACHE = (now, result)
        return result
    missing = llm.missing_config()
    if missing:
        result = {
            "ok": False,
            "provider": llm.provider,
            "model": llm.model,
            "message": missing,
        }
        _HEALTH_CACHE = (now, result)
        return result
    fallback = {
        "ok": True,
        "provider": llm.provider,
        "model": llm.model,
        "message": f"{llm.label} · {llm.model}" if llm.model else f"{llm.label}",
    }
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
        model = llm.model or (chat_ids[0] if chat_ids else (ids[0] if ids else ""))
        if not model:
            result = {
                "ok": False,
                "provider": llm.provider,
                "model": "",
                "message": f"{llm.label} is reachable but no model is available. Set LLM_MODEL.",
            }
        else:
            result = {
                "ok": True,
                "provider": llm.provider,
                "model": model,
                "message": f"{llm.label} · {model}",
            }
    except Exception:
        result = _HEALTH_CACHE[1] if _HEALTH_CACHE else fallback
        result = dict(result)
        if not _HEALTH_CACHE:
            result["ok"] = False
            result["provider"] = llm.provider
            result["model"] = llm.model
            result["message"] = (
                f"Cannot reach {llm.label} at {llm.base_url}."
                + (" Start the local server and load a model." if llm.local else " Check LLM_API_KEY and LLM_BASE_URL.")
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


def complete_json(system: str, user: str) -> tuple[dict[str, Any], str]:
    client = _client()
    model = resolve_model(client)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
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
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=8192,
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(_friendly_connection_error(exc)) from exc
        content = (response.choices[0].message.content or "").strip()
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
        "Put each achievement in bullets."
    )
    user = (
        f"JSON schema:\n{PROFILE_SCHEMA_HINT}\n\n"
        f"Raw CV text:\n{raw_text[:20000]}"
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
) -> tuple[TailorPack, str]:
    system = (
        "You are a precise resume tailor. You rewrite a candidate's existing profile for one job.\n"
        "HARD RULES:\n"
        "- Use only facts present in the profile. Never invent employers, titles, dates, degrees, metrics, tools, or skills.\n"
        "- You MAY rephrase bullets, reorder, drop irrelevant items, and use the job's wording when it honestly describes existing work.\n"
        "- Skills MUST be four labeled lines only (omit a line if empty), using only skills from the profile:\n"
        "  Languages: ...\n  Databases: ...\n  Frameworks: ...\n  Technologies and Tools: ...\n"
        "- additional_skills: spoken languages or extras already in the profile. Use [] if none.\n"
        "- summary: 2-4 sentences, tailored intro placed under the name and above Technical Skills. Facts only.\n"
        "- One-page friendly: 3–6 bullets per recent role; fewer for older roles.\n"
        "- Cover letter: 180–250 words, specific to this job, no fake claims, plain text paragraphs.\n"
        "- Match analysis must be honest and SHORT: at most 6 items per list, short phrases only.\n"
        "- Return one complete JSON object with keys cv, cover_letter, match. No markdown fences. Do not stop mid-string."
    )
    user = {
        "job_title": title,
        "company": company,
        "job_description": job_text[:18000],
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
    data, model = complete_json(system, json.dumps(user, ensure_ascii=False, indent=2))
    raw_match = data.get("match") or {}
    if isinstance(raw_match, dict):
        coverage = raw_match.get("keyword_coverage") or []
        if isinstance(coverage, list):
            normalized = []
            for item in coverage:
                if isinstance(item, str):
                    normalized.append({"keyword": item, "present": False})
                else:
                    normalized.append(item)
            raw_match["keyword_coverage"] = normalized
    try:
        cv = Profile.model_validate(data.get("cv") or {})
        match = MatchAnalysis.model_validate(raw_match if isinstance(raw_match, dict) else {})
    except Exception as exc:
        raise LLMError(f"Model JSON did not match the expected schema: {exc}") from exc
    pack = TailorPack(
        cv=cv,
        cover_letter=str(data.get("cover_letter") or "").strip(),
        match=match,
    )
    return pack, model
