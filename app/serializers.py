from __future__ import annotations

from datetime import datetime

from app.models import Company, Generation, Job
from app.schemas import MatchAnalysis, Profile


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def job_payload(job: Job, *, detail: bool = False) -> dict:
    data = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "company_id": job.company_id,
        "company_name": job.company_name,
        "url": job.url,
        "location": job.location,
        "source_text": job.source_text,
        "required_skills": job.required_skills,
        "desired_skills": job.desired_skills,
        "required_skill_list": job.required_skill_list,
        "desired_skill_list": job.desired_skill_list,
        "notes": job.notes,
        "scrape_warning": job.scrape_warning,
        "status": job.status,
        "status_label": job.status_label,
        "status_note": job.status_note,
        "applied_at": _iso(job.applied_at),
        "created_at": _iso(job.created_at),
        "updated_at": _iso(job.updated_at),
        "source_host": job.source_host,
        "has_generation": bool(job.latest_generation),
    }
    if detail:
        data["generation"] = generation_payload(job.latest_generation)
    return data


def generation_payload(generation: Generation | None) -> dict | None:
    if generation is None:
        return None
    try:
        cv = Profile.model_validate(generation.cv_json or {})
        match = MatchAnalysis.model_validate(generation.match_json or {})
    except Exception:
        cv = Profile()
        match = MatchAnalysis()
    return {
        "id": generation.id,
        "created_at": _iso(generation.created_at),
        "model_name": generation.model_name,
        "cover_letter": generation.cover_letter,
        "cv": cv.model_dump(),
        "match": match.model_dump(),
    }


def company_payload(company: Company, *, include_positions: bool = False) -> dict:
    data = {
        "id": company.id,
        "name": company.name,
        "website": company.website,
        "location": company.location,
        "notes": company.notes,
        "created_at": _iso(company.created_at),
        "updated_at": _iso(company.updated_at),
        "position_count": len(company.positions),
    }
    if include_positions:
        data["positions"] = [job_payload(job) for job in company.positions]
    return data
