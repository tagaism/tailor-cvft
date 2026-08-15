from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.config import settings
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
  "skills": ["..."],
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
    {"school": "", "degree": "", "field": "", "start": "", "end": "", "details": ""}
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


def _client(timeout: float = 180.0, connect: float = 2.0) -> OpenAI:
    return OpenAI(
        api_key=settings.llm_api_key or "lm-studio",
        base_url=settings.llm_base_url.rstrip("/"),
        timeout=httpx.Timeout(timeout, connect=connect),
    )


def resolve_model(client: OpenAI | None = None) -> str:
    if settings.llm_model.strip():
        return settings.llm_model.strip()
    client = client or _client()
    try:
        models = client.models.list()
    except Exception as exc:
        raise LLMError(_friendly_connection_error(exc)) from exc
    ids = [item.id for item in getattr(models, "data", []) if getattr(item, "id", None)]
    if not ids:
        raise LLMError(
            "LM Studio is running but no model is loaded. Load a model in LM Studio, then try again."
        )
    return ids[0]


def _friendly_connection_error(exc: Exception) -> str:
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return (
            "Cannot reach LM Studio at "
            f"{settings.llm_base_url}. Start the local server (Developer tab, port 1234) "
            "and load a model."
        )
    if isinstance(exc, APIStatusError):
        return f"LM Studio returned HTTP {exc.status_code}: {exc.message}"
    return f"LM Studio request failed: {exc}"


_HEALTH_CACHE: tuple[float, dict[str, Any]] | None = None
_HEALTH_TTL_SECONDS = 8.0


def llm_health() -> dict[str, Any]:
    global _HEALTH_CACHE
    now = time.time()
    if _HEALTH_CACHE and now - _HEALTH_CACHE[0] < _HEALTH_TTL_SECONDS:
        return _HEALTH_CACHE[1]
    try:
        client = _client(timeout=2.0, connect=1.0)
        model = resolve_model(client)
        result = {"ok": True, "model": model, "message": f"LM Studio · {model}"}
    except LLMError as exc:
        result = {"ok": False, "model": "", "message": str(exc)}
    except Exception as exc:
        result = {"ok": False, "model": "", "message": _friendly_connection_error(exc)}
    _HEALTH_CACHE = (now, result)
    return result


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise LLMError("The model did not return JSON. Try again, or use a stronger local model.")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise LLMError("The model returned JSON that was not an object.")
    return data


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


def tailor_pack(profile: Profile, job_text: str, notes: str, title: str, company: str) -> tuple[TailorPack, str]:
    system = (
        "You are a precise resume tailor. You rewrite a candidate's existing profile for one job.\n"
        "HARD RULES:\n"
        "- Use only facts present in the profile. Never invent employers, titles, dates, degrees, metrics, tools, or skills.\n"
        "- You MAY rephrase bullets, reorder, drop irrelevant items, and use the job's wording when it honestly describes existing work.\n"
        "- Skills on the tailored CV must be a subset of the profile skills, or obvious synonyms already supported by the profile (JS → JavaScript).\n"
        "- One-page friendly: summary ≤ 4 sentences; 3–6 bullets per recent role; fewer for older roles.\n"
        "- Cover letter: 250–350 words, specific to this job, no fake claims, plain text paragraphs.\n"
        "- Match analysis must be honest. List real gaps. Do not flatter.\n"
        "Return ONLY a JSON object with keys cv, cover_letter, match."
    )
    user = {
        "job_title": title,
        "company": company,
        "job_description": job_text[:18000],
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
