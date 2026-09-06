from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from html import unescape as html_unescape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.cv_layout import contact_bits
from app.db import get_db
from app.deps import templates
from app.models import Generation, Job
from app.profile_store import load_profile
from app.richtext import apply_cv_path, delete_cv_path, sanitize_rich
from app.schemas import CvStyle, Profile, ShokumuCv
from app.services.pdf import html_to_pdf, letter_to_pdf, shokumu_to_pdf

router = APIRouter()


class BulletEdit(BaseModel):
    path: str = Field(min_length=1, max_length=200)
    html: str = Field(default="", max_length=16000)
    delete: bool = False


class ContactPick(BaseModel):
    identity: int = 0


def _job_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _get_generation_or_400(job: Job) -> Generation:
    generation = job.latest_generation
    if generation is None:
        raise HTTPException(status_code=400, detail="Build a CV first.")
    return generation


def _is_shokumu(job: Job) -> bool:
    generation = job.latest_generation
    return bool(generation and generation.cv_style == CvStyle.shokumu.value)


def _load_cv(job: Job) -> Profile:
    return Profile.model_validate(_get_generation_or_400(job).cv_json)


def _load_shokumu(job: Job) -> ShokumuCv:
    return ShokumuCv.model_validate(_get_generation_or_400(job).cv_json)


def _identity_choices() -> list[dict[str, str]]:
    return [
        {"full_name": item.full_name, "email": item.email}
        for item in load_profile().contact.identities
        if item.full_name.strip() or item.email.strip()
    ]


def _match_identity_index(identities: list[dict[str, str]], name: str, email: str) -> int:
    name = (name or "").strip()
    email = (email or "").strip()
    if email:
        for index, item in enumerate(identities):
            if (item.get("email") or "").strip() == email:
                return index
    if name:
        for index, item in enumerate(identities):
            if (item.get("full_name") or "").strip() == name:
                return index
    return 0


def _plain_text(value: str) -> str:
    text = sanitize_rich(value)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(html_unescape(text).split())


def _identity_from_edit(text: str, field: str) -> dict[str, str]:
    needle = (text or "").strip().lower()
    if not needle:
        raise ValueError("Name and email must match a pair on your profile.")
    key = "email" if field == "email" else "full_name"
    for item in _identity_choices():
        if (item.get(key) or "").strip().lower() == needle:
            return item
    raise ValueError("Name and email must match a pair on your profile.")


def _stamp_identity_on_cv(generation: Generation, chosen: dict[str, str]) -> tuple[dict, str, str, str]:
    name = (chosen.get("full_name") or "").strip()
    email = (chosen.get("email") or "").strip()
    cv = copy.deepcopy(generation.cv_json or {})
    profile = load_profile()
    if generation.cv_style == CvStyle.shokumu.value:
        if name:
            cv["name"] = name
        ShokumuCv.model_validate(cv)
        return cv, name or str(cv.get("name") or ""), email, ""
    contact = cv.setdefault("contact", {})
    contact["full_name"] = name
    contact["email"] = email
    chosen_dump = {"full_name": name, "email": email}
    rest = [
        item.model_dump()
        for item in profile.contact.identities
        if item.full_name.strip() != name or item.email.strip() != email
    ]
    contact["identities"] = [chosen_dump] + rest
    parsed = Profile.model_validate(cv)
    return parsed.model_dump(), parsed.contact.full_name, parsed.contact.email, " | ".join(contact_bits(parsed))


def _preview_contact_context(job: Job) -> dict:
    identities = _identity_choices()
    generation = job.latest_generation
    name = email = ""
    if generation:
        data = generation.cv_json or {}
        if generation.cv_style == CvStyle.shokumu.value:
            name = str(data.get("name") or "")
        else:
            contact = data.get("contact") or {}
            name = str(contact.get("full_name") or "")
            email = str(contact.get("email") or "")
    return {
        "identities": identities,
        "selected_identity": _match_identity_index(identities, name, email),
    }


@router.post("/jobs/{job_id}/cv-bullet")
async def save_cv_bullet(job_id: int, payload: BulletEdit, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    generation = job.latest_generation
    if generation is None:
        raise HTTPException(status_code=400, detail="Build a CV first.")
    if payload.path == "cover_letter" and payload.delete:
        raise HTTPException(status_code=400, detail="Cannot delete the cover letter this way.")
    cleaned = sanitize_rich(payload.html)
    if payload.path == "cover_letter":
        generation.cover_letter = cleaned
        job.updated_at = datetime.now(timezone.utc)
        db.add(generation)
        db.commit()
        return JSONResponse({"ok": True, "html": cleaned})
    if payload.path in {"contact.full_name", "contact.email", "name"}:
        field = "email" if payload.path.endswith("email") else "full_name"
        try:
            chosen = _identity_from_edit(_plain_text(payload.html), field)
            cv, full_name, email, contact_line = _stamp_identity_on_cv(generation, chosen)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not save that contact: {exc}") from exc
        generation.cv_json = cv
        flag_modified(generation, "cv_json")
        job.updated_at = datetime.now(timezone.utc)
        db.add(generation)
        db.commit()
        html = email if field == "email" else full_name
        return JSONResponse(
            {
                "ok": True,
                "html": html,
                "full_name": full_name,
                "email": email,
                "contact_line": contact_line,
            }
        )
    cv = copy.deepcopy(generation.cv_json or {})
    try:
        if payload.delete:
            delete_cv_path(cv, payload.path)
        else:
            apply_cv_path(cv, payload.path, cleaned)
        if generation.cv_style == CvStyle.shokumu.value:
            ShokumuCv.model_validate(cv)
        else:
            Profile.model_validate(cv)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not save that bullet: {exc}") from exc
    generation.cv_json = cv
    flag_modified(generation, "cv_json")
    job.updated_at = datetime.now(timezone.utc)
    db.add(generation)
    db.commit()
    if payload.delete:
        return JSONResponse({"ok": True, "deleted": True})
    return JSONResponse({"ok": True, "html": cleaned})


@router.post("/jobs/{job_id}/cv-contact")
async def pick_cv_contact(job_id: int, payload: ContactPick, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    generation = _get_generation_or_400(job)
    registered = _identity_choices()
    if not registered:
        raise HTTPException(status_code=400, detail="Add a name and email on your profile first.")
    if payload.identity < 0 or payload.identity >= len(registered):
        raise HTTPException(status_code=400, detail="Name and email must match a pair on your profile.")
    try:
        cv, full_name, email, contact_line = _stamp_identity_on_cv(generation, registered[payload.identity])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not apply that contact: {exc}") from exc
    generation.cv_json = cv
    flag_modified(generation, "cv_json")
    job.updated_at = datetime.now(timezone.utc)
    db.add(generation)
    db.commit()
    return JSONResponse(
        {"ok": True, "full_name": full_name, "email": email, "contact_line": contact_line}
    )


@router.get("/jobs/{job_id}/preview", response_class=HTMLResponse)
async def preview_cv(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    if _is_shokumu(job):
        cv = _load_shokumu(job)
        template = "cv/shokumu.html"
    else:
        cv = _load_cv(job)
        template = "cv/preview.html"
    return templates.TemplateResponse(
        request,
        template,
        {"request": request, "cv": cv, "standalone": True, "job": job, **_preview_contact_context(job)},
    )


@router.get("/jobs/{job_id}/pdf")
async def download_cv_pdf(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    if _is_shokumu(job):
        cv = _load_shokumu(job)
        pdf = shokumu_to_pdf(cv)
        filename = _pdf_filename(cv.name or "resume", job.company_name or job.title, "shokumu")
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    cv = _load_cv(job)
    html = templates.get_template("cv/preview.html").render(
        {"request": request, "cv": cv, "standalone": True, "job": None}
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
    generation = _get_generation_or_400(job)
    if generation.cv_style == CvStyle.shokumu.value:
        jp = ShokumuCv.model_validate(generation.cv_json or {})
        cv = Profile(contact={"full_name": jp.name})
    else:
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
            **_preview_contact_context(job),
        },
    )


@router.get("/jobs/{job_id}/cover-letter/pdf")
async def download_letter_pdf(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    generation = _get_generation_or_400(job)
    japanese = generation.cv_style == CvStyle.shokumu.value
    if japanese:
        jp = ShokumuCv.model_validate(generation.cv_json or {})
        cv = Profile(contact={"full_name": jp.name})
        pdf = letter_to_pdf(
            cv,
            generation.cover_letter,
            job.title,
            job.company_name,
            japanese=True,
            sender_name=jp.name,
        )
        filename = _pdf_filename(jp.name or "letter", job.company_name or job.title, "shibou-douki")
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
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
