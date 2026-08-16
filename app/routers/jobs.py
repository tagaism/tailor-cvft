from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import template_context, templates
from app.models import Generation, Job
from app.profile_store import load_profile
from app.forms import parse_skill_text
from app.schemas import ApplicationStatus, MatchAnalysis, Profile
from app.services.companies import apply_status, link_job_company
from app.services.llm import LLMError, tailor_pack
from app.services.pdf import html_to_pdf
from app.services.scraper import fetch_job

router = APIRouter()


@router.get("/jobs", response_class=HTMLResponse)
async def list_jobs(request: Request, db: Session = Depends(get_db)):
    status_filter = request.query_params.get("status", "").strip()
    query = select(Job).order_by(Job.updated_at.desc())
    if status_filter and status_filter in {item.value for item in ApplicationStatus}:
        query = query.where(Job.status == status_filter)
    jobs = db.scalars(query).all()
    return templates.TemplateResponse(
        request,
        "jobs/list.html",
        template_context(
            request,
            jobs=jobs,
            active="jobs",
            status_filter=status_filter,
            error=request.query_params.get("error", ""),
            url=request.query_params.get("url", ""),
            company_name=request.query_params.get("company_name", ""),
            job_description=request.query_params.get("job_description", ""),
            required_skills=request.query_params.get("required_skills", ""),
            desired_skills=request.query_params.get("desired_skills", ""),
            notes=request.query_params.get("notes", ""),
        ),
    )


@router.get("/jobs/new")
async def new_job():
    return RedirectResponse("/jobs#add-job", status_code=303)


@router.post("/jobs/new")
async def create_job(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    url = str(form.get("url") or "").strip()
    company_name = str(form.get("company_name") or "").strip()
    job_description = str(form.get("job_description") or form.get("pasted") or "").strip()
    required_skills = parse_skill_text(str(form.get("required_skills") or ""))
    desired_skills = parse_skill_text(str(form.get("desired_skills") or ""))
    notes = str(form.get("notes") or "").strip()
    if not url and not job_description:
        return RedirectResponse(
            "/jobs?error=" + quote("Add a job URL or a job description.") + "#add-job",
            status_code=303,
        )

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
        required_skills=required_skills,
        desired_skills=desired_skills,
        notes=notes,
        scrape_warning=warning,
        status=ApplicationStatus.saved.value,
    )
    link_job_company(db, job, company)
    db.add(job)
    db.commit()
    db.refresh(job)
    return RedirectResponse(f"/jobs/{job.id}", status_code=303)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    generation = job.latest_generation
    cv = Profile.model_validate(generation.cv_json) if generation else None
    match = MatchAnalysis.model_validate(generation.match_json) if generation else None
    return templates.TemplateResponse(
        request,
        "jobs/detail.html",
        template_context(
            request,
            job=job,
            generation=generation,
            cv=cv,
            match=match,
            profile=load_profile(),
            active="jobs",
            flash=request.query_params.get("flash", ""),
            error=request.query_params.get("error", ""),
        ),
    )


@router.post("/jobs/{job_id}")
async def update_job(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    form = await request.form()
    job.title = str(form.get("title") or "").strip() or job.title
    link_job_company(db, job, str(form.get("company") or "").strip())
    job.location = str(form.get("location") or "").strip()
    job.url = str(form.get("url") or "").strip()
    job.notes = str(form.get("notes") or "").strip()
    job.source_text = str(form.get("source_text") or "").strip()
    job.required_skills = parse_skill_text(str(form.get("required_skills") or ""))
    job.desired_skills = parse_skill_text(str(form.get("desired_skills") or ""))
    apply_status(job, str(form.get("status") or job.status))
    job.status_note = str(form.get("status_note") or "").strip()
    job.updated_at = datetime.now(timezone.utc)
    if job.source_text and "paste" in (job.scrape_warning or "").lower():
        job.scrape_warning = ""
    db.commit()
    return RedirectResponse(f"/jobs/{job.id}?flash=saved", status_code=303)


@router.post("/jobs/{job_id}/refetch")
async def refetch_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    if not job.url:
        return RedirectResponse(
            f"/jobs/{job.id}?error=" + quote("This job has no URL to re-fetch."),
            status_code=303,
        )
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
    flash = "refetched" if scraped.text else "warning"
    return RedirectResponse(f"/jobs/{job.id}?flash={flash}", status_code=303)


@router.post("/jobs/{job_id}/status")
async def update_job_status(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    form = await request.form()
    apply_status(job, str(form.get("status") or job.status))
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse(f"/jobs/{job.id}?flash=status", status_code=303)


@router.post("/jobs/{job_id}/delete")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is not None:
        db.delete(job)
        db.commit()
    return RedirectResponse("/jobs", status_code=303)


@router.post("/jobs/{job_id}/build")
async def build_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    profile = load_profile()
    if not profile.is_ready():
        return RedirectResponse(
            f"/jobs/{job.id}?error="
            + quote("Fill your profile (name plus experience, skills, or education) before building."),
            status_code=303,
        )
    if not job.source_text.strip():
        return RedirectResponse(
            f"/jobs/{job.id}?error="
            + quote("This job has no description yet. Paste the posting text and save."),
            status_code=303,
        )
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
        return RedirectResponse(f"/jobs/{job.id}?error={quote(str(exc))}", status_code=303)

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
    return RedirectResponse(f"/jobs/{job.id}?flash=built#results", status_code=303)


def _load_cv(job: Job) -> Profile | None:
    generation = job.latest_generation
    if generation is None:
        return None
    return Profile.model_validate(generation.cv_json)


@router.get("/jobs/{job_id}/preview", response_class=HTMLResponse)
async def preview_cv(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    cv = _load_cv(job)
    if cv is None:
        return RedirectResponse(f"/jobs/{job.id}?error=" + quote("Build a CV first."), status_code=303)
    return templates.TemplateResponse(
        request,
        "cv/preview.html",
        {"request": request, "cv": cv, "standalone": True, "job": job},
    )


@router.get("/jobs/{job_id}/pdf")
async def download_cv_pdf(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    cv = _load_cv(job)
    if cv is None:
        return RedirectResponse(f"/jobs/{job.id}?error=" + quote("Build a CV first."), status_code=303)
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
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    generation = job.latest_generation
    if generation is None:
        return RedirectResponse(f"/jobs/{job.id}?error=" + quote("Build a pack first."), status_code=303)
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
    job = db.get(Job, job_id)
    if job is None:
        return RedirectResponse("/jobs?error=Job+not+found.", status_code=303)
    generation = job.latest_generation
    if generation is None:
        return RedirectResponse(f"/jobs/{job.id}?error=" + quote("Build a pack first."), status_code=303)
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
