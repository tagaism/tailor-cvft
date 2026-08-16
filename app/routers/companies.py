from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import template_context, templates
from app.models import Company
from app.services.companies import get_or_create_company, normalize_company_name

router = APIRouter()


@router.get("/companies", response_class=HTMLResponse)
async def list_companies(request: Request, db: Session = Depends(get_db)):
    companies = db.scalars(
        select(Company).options(selectinload(Company.positions)).order_by(Company.name)
    ).all()
    return templates.TemplateResponse(
        request,
        "companies/list.html",
        template_context(
            request,
            companies=companies,
            active="companies",
            flash=request.query_params.get("flash", ""),
            error=request.query_params.get("error", ""),
        ),
    )


@router.post("/companies")
async def create_company(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = str(form.get("name") or "").strip()
    if not name:
        return RedirectResponse(
            "/companies?error=" + quote("A company needs a name."),
            status_code=303,
        )
    company = get_or_create_company(db, name)
    assert company is not None
    company.website = str(form.get("website") or "").strip() or company.website
    company.location = str(form.get("location") or "").strip() or company.location
    company.notes = str(form.get("notes") or "").strip() or company.notes
    db.commit()
    return RedirectResponse(f"/companies/{company.id}?flash=saved", status_code=303)


@router.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(request: Request, company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        return RedirectResponse("/companies?error=Company+not+found.", status_code=303)
    return templates.TemplateResponse(
        request,
        "companies/detail.html",
        template_context(
            request,
            company=company,
            positions=company.positions,
            active="companies",
            flash=request.query_params.get("flash", ""),
            error=request.query_params.get("error", ""),
        ),
    )


@router.post("/companies/{company_id}")
async def update_company(request: Request, company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        return RedirectResponse("/companies?error=Company+not+found.", status_code=303)
    form = await request.form()
    name = str(form.get("name") or "").strip()
    if not name:
        return RedirectResponse(
            f"/companies/{company.id}?error=" + quote("A company needs a name."),
            status_code=303,
        )
    new_key = normalize_company_name(name)
    clash = db.scalar(select(Company).where(Company.name_key == new_key, Company.id != company.id))
    if clash:
        return RedirectResponse(
            f"/companies/{company.id}?error=" + quote("Another company already uses that name."),
            status_code=303,
        )
    company.name = name
    company.name_key = new_key
    company.website = str(form.get("website") or "").strip()
    company.location = str(form.get("location") or "").strip()
    company.notes = str(form.get("notes") or "").strip()
    company.updated_at = datetime.now(timezone.utc)
    for job in company.positions:
        job.company = name
    db.commit()
    return RedirectResponse(f"/companies/{company.id}?flash=saved", status_code=303)


@router.post("/companies/{company_id}/delete")
async def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        return RedirectResponse("/companies?error=Company+not+found.", status_code=303)
    if company.positions:
        return RedirectResponse(
            f"/companies/{company.id}?error="
            + quote("Remove or reassign this company's positions before deleting it."),
            status_code=303,
        )
    db.delete(company)
    db.commit()
    return RedirectResponse("/companies?flash=deleted", status_code=303)
