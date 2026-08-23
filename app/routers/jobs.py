from __future__ import annotations

import copy
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db
from app.deps import templates
from app.models import Job
from app.richtext import apply_cv_path, sanitize_rich
from app.schemas import Profile
from app.services.pdf import html_to_pdf

router = APIRouter()


class BulletEdit(BaseModel):
    path: str = Field(min_length=1, max_length=200)
    html: str = Field(default="", max_length=16000)


def _job_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _load_cv(job: Job) -> Profile:
    generation = job.latest_generation
    if generation is None:
        raise HTTPException(status_code=400, detail="Build a CV first.")
    return Profile.model_validate(generation.cv_json)


@router.post("/jobs/{job_id}/cv-bullet")
async def save_cv_bullet(job_id: int, payload: BulletEdit, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    generation = job.latest_generation
    if generation is None:
        raise HTTPException(status_code=400, detail="Build a CV first.")
    cleaned = sanitize_rich(payload.html)
    if payload.path == "cover_letter":
        generation.cover_letter = cleaned
        job.updated_at = datetime.now(timezone.utc)
        db.add(generation)
        db.commit()
        return JSONResponse({"ok": True, "html": cleaned})
    cv = copy.deepcopy(generation.cv_json or {})
    try:
        apply_cv_path(cv, payload.path, cleaned)
        Profile.model_validate(cv)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not save that bullet: {exc}") from exc
    generation.cv_json = cv
    flag_modified(generation, "cv_json")
    job.updated_at = datetime.now(timezone.utc)
    db.add(generation)
    db.commit()
    return JSONResponse({"ok": True, "html": cleaned})


@router.get("/jobs/{job_id}/preview", response_class=HTMLResponse)
async def preview_cv(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    cv = _load_cv(job)
    return templates.TemplateResponse(
        request,
        "cv/preview.html",
        {"request": request, "cv": cv, "standalone": True, "job": job},
    )


@router.get("/jobs/{job_id}/pdf")
async def download_cv_pdf(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    cv = _load_cv(job)
    html = templates.get_template("cv/preview.html").render(
        {"request": request, "cv": cv, "standalone": True, "job": job}
    )
    pdf = html_to_pdf(html, cv=cv)
    filename = _pdf_filename(cv.contact.full_name or "resume", job.company_name or job.title, "cv")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/jobs/{job_id}/cover-letter", response_class=HTMLResponse)
async def preview_letter(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    generation = job.latest_generation
    if generation is None:
        raise HTTPException(status_code=400, detail="Build a pack first.")
    cv = Profile.model_validate(generation.cv_json)
    return templates.TemplateResponse(
        request,
        "cv/cover_letter.html",
        {
            "request": request,
            "cv": cv,
            "job": job,
            "letter": generation.cover_letter,
            "standalone": True,
        },
    )


@router.get("/jobs/{job_id}/cover-letter/pdf")
async def download_letter_pdf(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    generation = job.latest_generation
    if generation is None:
        raise HTTPException(status_code=400, detail="Build a pack first.")
    cv = Profile.model_validate(generation.cv_json)
    html = templates.get_template("cv/cover_letter.html").render(
        {
            "request": request,
            "cv": cv,
            "job": job,
            "letter": generation.cover_letter,
            "standalone": True,
        }
    )
    pdf = html_to_pdf(
        html,
        cv=cv,
        letter=generation.cover_letter,
        job_title=job.title,
        company=job.company_name,
    )
    filename = _pdf_filename(cv.contact.full_name or "letter", job.company_name or job.title, "cover-letter")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_filename(name: str, company: str, kind: str) -> str:
    def slug(value: str) -> str:
        keep = "".join(ch if ch.isalnum() else "-" for ch in value.lower())
        return "-".join(part for part in keep.split("-") if part) or "file"

    return f"{slug(name)}-{slug(company)}-{kind}.pdf"
