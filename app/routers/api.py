from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import DEFAULT_LLM_PROVIDER, settings
from app.db import get_db
from app.forms import parse_skill_text
from app.models import Company, Generation, Job
from app.profile_store import load_profile, save_profile
from app.schemas import APPLICATION_STATUSES, ApplicationStatus, Profile
from app.serializers import company_payload, job_payload
from app.services.companies import apply_status, get_or_create_company, link_job_company, normalize_company_name
from app.services.llm import LLMError, extract_profile_from_cv, llm_health, tailor_pack
from app.services.merge import merge_profiles
from app.services.parser import ParseError, extract_text
from app.services.scraper import fetch_job

router = APIRouter(prefix="/api")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class JobWrite(BaseModel):
    url: str = ""
    company_name: str = ""
    job_description: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    notes: str = ""
    source_text: str = ""
    required_skills: str = ""
    desired_skills: str = ""
    status: str = ""
    status_note: str = ""


class CompanyWrite(BaseModel):
    name: str = ""
    website: str = ""
    location: str = ""
    notes: str = ""


def _error(message: str, status_code: int = 400) -> None:
    raise HTTPException(status_code=status_code, detail=message)


@router.get("/health")
async def api_health():
    llm = llm_health()
    return {
        "ok": True,
        "llm": {
            "ok": bool(llm.get("ok")),
            "provider": llm.get("provider") or settings.llm_provider or DEFAULT_LLM_PROVIDER,
            "model": llm.get("model") or "",
            "message": llm.get("message") or "",
            "checked_at": llm.get("checked_at") or "",
        },
        "statuses": APPLICATION_STATUSES,
    }


@router.get("/profile")
async def api_get_profile():
    profile = load_profile()
    return {"profile": profile.model_dump(), "ready": profile.is_ready()}


@router.put("/profile")
async def api_put_profile(profile: Profile):
    save_profile(profile)
    return {"profile": profile.model_dump(), "ready": profile.is_ready()}


@router.post("/profile/upload")
async def api_upload_profile(file: UploadFile = File(...)):
    if not file.filename:
        _error("Choose a CV file first.")
    data = await file.read()
    if not data:
        _error("That file was empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        _error("That file is larger than 20 MB.")
    try:
        raw = extract_text(file.filename, data)
        extracted, _model = await asyncio.to_thread(extract_profile_from_cv, raw)
    except ParseError as exc:
        _error(str(exc))
    except LLMError as exc:
        _error(str(exc))
    except Exception as exc:
        _error(f"Upload failed: {exc}")
    merged = merge_profiles(load_profile(), extracted)
    save_profile(merged)
    return {"profile": merged.model_dump(), "ready": merged.is_ready(), "imported": True}


@router.get("/jobs")
async def api_list_jobs(status: str = "", db: Session = Depends(get_db)):
    query = select(Job).order_by(Job.updated_at.desc())
    if status and status in {item.value for item in ApplicationStatus}:
        query = query.where(Job.status == status)
    jobs = db.scalars(query).all()
    profile = load_profile()
    return {"jobs": [job_payload(job) for job in jobs], "profile_ready": profile.is_ready()}


@router.post("/jobs")
async def api_create_job(payload: JobWrite, db: Session = Depends(get_db)):
    url = payload.url.strip()
    company_name = (payload.company_name or payload.company).strip()
    job_description = (payload.job_description or payload.source_text).strip()
    if not url and not job_description:
        _error("Add a job URL or a job description.")

    scraped_title = scraped_company = scraped_text = warning = ""
    final_url = url
    if url:
        scraped = fetch_job(url)
        scraped_title = scraped.title
        scraped_company = scraped.company
        scraped_text = scraped.text
        warning = scraped.warning
        final_url = scraped.url or url

    source_text = job_description or scraped_text
    title = scraped_title or (source_text.splitlines()[0][:120] if source_text else "Untitled role")
    company = company_name or scraped_company
    if not source_text and not warning:
        warning = "No job text yet. Paste the description on this form or the next screen."

    job = Job(
        url=final_url,
        title=title,
        source_text=source_text,
        required_skills=parse_skill_text(payload.required_skills),
        desired_skills=parse_skill_text(payload.desired_skills),
        notes=payload.notes.strip(),
        scrape_warning=warning,
        status=ApplicationStatus.saved.value,
    )
    link_job_company(db, job, company)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {**job_payload(job, detail=True), "profile_ready": load_profile().is_ready()}


@router.get("/jobs/{job_id}")
async def api_get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        _error("Job not found.", 404)
    profile = load_profile()
    return {
        **job_payload(job, detail=True),
        "profile_ready": profile.is_ready(),
    }


@router.put("/jobs/{job_id}")
async def api_update_job(job_id: int, payload: JobWrite, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        _error("Job not found.", 404)
    job.title = payload.title.strip() or job.title
    link_job_company(db, job, (payload.company or payload.company_name).strip())
    job.location = payload.location.strip()
    job.url = payload.url.strip()
    job.notes = payload.notes.strip()
    job.source_text = (payload.source_text or payload.job_description).strip()
    job.required_skills = parse_skill_text(payload.required_skills)
    job.desired_skills = parse_skill_text(payload.desired_skills)
    apply_status(job, payload.status or job.status)
    job.status_note = payload.status_note.strip()
    job.updated_at = datetime.now(timezone.utc)
    if job.source_text and "paste" in (job.scrape_warning or "").lower():
        job.scrape_warning = ""
    db.commit()
    db.refresh(job)
    return {**job_payload(job, detail=True), "profile_ready": load_profile().is_ready()}


@router.delete("/jobs/{job_id}")
async def api_delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is not None:
        db.delete(job)
        db.commit()
    return JSONResponse({"ok": True})


@router.post("/jobs/{job_id}/refetch")
async def api_refetch_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        _error("Job not found.", 404)
    if not job.url:
        _error("This job has no URL to re-fetch.")
    scraped = fetch_job(job.url)
    job.url = scraped.url or job.url
    if scraped.title:
        job.title = scraped.title
    if scraped.company:
        link_job_company(db, job, scraped.company)
    if scraped.text:
        job.source_text = scraped.text
    job.scrape_warning = scraped.warning
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return {**job_payload(job, detail=True), "profile_ready": load_profile().is_ready()}


@router.post("/jobs/{job_id}/build")
async def api_build_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        _error("Job not found.", 404)
    profile = load_profile()
    if not profile.is_ready():
        _error("Fill your profile (name plus experience, skills, or education) before building.")
    if not job.source_text.strip():
        _error("This job has no description yet. Paste the posting text and save.")
    try:
        pack, model = await asyncio.to_thread(
            tailor_pack,
            profile,
            job.source_text,
            job.notes,
            job.title,
            job.company_name,
            job.required_skill_list,
            job.desired_skill_list,
        )
    except LLMError as exc:
        _error(str(exc))
    generation = Generation(
        job_id=job.id,
        cv_json=pack.cv.model_dump(),
        cover_letter=pack.cover_letter,
        match_json=pack.match.model_dump(),
        model_name=model,
    )
    db.add(generation)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return {**job_payload(job, detail=True), "profile_ready": True}


@router.get("/companies")
async def api_list_companies(db: Session = Depends(get_db)):
    companies = db.scalars(
        select(Company).options(selectinload(Company.positions)).order_by(Company.name)
    ).all()
    return {"companies": [company_payload(company) for company in companies]}


@router.post("/companies")
async def api_create_company(payload: CompanyWrite, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        _error("A company needs a name.")
    company = get_or_create_company(db, name)
    assert company is not None
    if payload.website.strip():
        company.website = payload.website.strip()
    if payload.location.strip():
        company.location = payload.location.strip()
    if payload.notes.strip():
        company.notes = payload.notes.strip()
    db.commit()
    db.refresh(company)
    return company_payload(company, include_positions=True)


@router.get("/companies/{company_id}")
async def api_get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        _error("Company not found.", 404)
    return company_payload(company, include_positions=True)


@router.put("/companies/{company_id}")
async def api_update_company(company_id: int, payload: CompanyWrite, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        _error("Company not found.", 404)
    name = payload.name.strip()
    if not name:
        _error("A company needs a name.")
    new_key = normalize_company_name(name)
    clash = db.scalar(select(Company).where(Company.name_key == new_key, Company.id != company.id))
    if clash:
        _error("Another company already uses that name.")
    company.name = name
    company.name_key = new_key
    company.website = payload.website.strip()
    company.location = payload.location.strip()
    company.notes = payload.notes.strip()
    company.updated_at = datetime.now(timezone.utc)
    for job in company.positions:
        job.company = name
    db.commit()
    db.refresh(company)
    return company_payload(company, include_positions=True)


@router.delete("/companies/{company_id}")
async def api_delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        _error("Company not found.", 404)
    if company.positions:
        _error("Remove or reassign this company's positions before deleting it.")
    db.delete(company)
    db.commit()
    return JSONResponse({"ok": True})
