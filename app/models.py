from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base
from app.schemas import ApplicationStatus, STATUS_LABELS


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    name: Mapped[str] = mapped_column(String(400), default="")
    name_key: Mapped[str] = mapped_column(String(400), default="", unique=True)
    website: Mapped[str] = mapped_column(String(2000), default="")
    location: Mapped[str] = mapped_column(String(400), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    positions: Mapped[list[Job]] = relationship(
        back_populates="employer",
        order_by="Job.updated_at.desc()",
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    url: Mapped[str] = mapped_column(String(2000), default="")
    title: Mapped[str] = mapped_column(String(400), default="")
    company: Mapped[str] = mapped_column(String(400), default="")
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    location: Mapped[str] = mapped_column(String(400), default="")
    source_text: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[str] = mapped_column(Text, default="")
    desired_skills: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    scrape_warning: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default=ApplicationStatus.saved.value)
    status_note: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employer: Mapped[Optional[Company]] = relationship(back_populates="positions")
    generations: Mapped[list[Generation]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="Generation.created_at.desc()",
    )

    @property
    def latest_generation(self) -> Optional[Generation]:
        return self.generations[0] if self.generations else None

    @property
    def source_host(self) -> str:
        if not self.url:
            return "pasted"
        from urllib.parse import urlparse

        host = urlparse(self.url).netloc.lower()
        return host[4:] if host.startswith("www.") else host

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status or "Saved")

    @property
    def company_name(self) -> str:
        if self.employer and self.employer.name:
            return self.employer.name
        return self.company

    @property
    def required_skill_list(self) -> list[str]:
        return _skill_lines(self.required_skills)

    @property
    def desired_skill_list(self) -> list[str]:
        return _skill_lines(self.desired_skills)


def _skill_lines(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    cv_json: Mapped[dict] = mapped_column(JSON, default=dict)
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    match_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_name: Mapped[str] = mapped_column(String(200), default="")
    cv_style: Mapped[str] = mapped_column(String(40), default="times")

    job: Mapped[Job] = relationship(back_populates="generations")
