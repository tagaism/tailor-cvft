from __future__ import annotations

from datetime import datetime, timezone

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Job
from app.schemas import ApplicationStatus, parse_status


def normalize_company_name(name: str) -> str:
    return " ".join(name.lower().split())


def get_or_create_company(db: Session, name: str) -> Optional[Company]:
    cleaned = " ".join((name or "").split())
    if not cleaned:
        return None
    key = normalize_company_name(cleaned)
    company = db.scalar(select(Company).where(Company.name_key == key))
    if company is None:
        company = Company(name=cleaned, name_key=key)
        db.add(company)
        db.flush()
    elif company.name != cleaned:
        company.name = cleaned
    return company


def link_job_company(db: Session, job: Job, name: str) -> None:
    company = get_or_create_company(db, name)
    job.company = (company.name if company else "") or " ".join((name or "").split())
    job.company_id = company.id if company else None
    job.employer = company


def apply_status(job: Job, raw_status: str) -> None:
    status = parse_status(raw_status)
    job.status = status.value
    if status == ApplicationStatus.applied and job.applied_at is None:
        job.applied_at = datetime.now(timezone.utc)
