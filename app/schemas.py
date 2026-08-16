from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Contact(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""


def _string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(item) for item in value if item is not None]


class Experience(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    current: bool = False
    bullets: list[str] = Field(default_factory=list)

    @field_validator("current", mode="before")
    @classmethod
    def _boolish(cls, value):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)

    @field_validator("bullets", mode="before")
    @classmethod
    def _bullets(cls, value):
        return _string_list(value)


class Education(BaseModel):
    school: str = ""
    degree: str = ""
    field: str = ""
    start: str = ""
    end: str = ""
    location: str = ""
    details: str = ""


class Project(BaseModel):
    name: str = ""
    url: str = ""
    description: str = ""
    bullets: list[str] = Field(default_factory=list)

    @field_validator("bullets", mode="before")
    @classmethod
    def _bullets(cls, value):
        return _string_list(value)


class Certification(BaseModel):
    name: str = ""
    issuer: str = ""
    year: str = ""


class Profile(BaseModel):
    contact: Contact = Field(default_factory=Contact)
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    additional_skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)

    @field_validator("skills", "additional_skills", mode="before")
    @classmethod
    def _skill_lists(cls, value):
        return _string_list(value)

    def is_ready(self) -> bool:
        has_name = bool(self.contact.full_name.strip())
        has_substance = bool(
            self.experience
            or self.skills
            or self.projects
            or self.education
            or self.summary.strip()
        )
        return has_name and has_substance


class KeywordCoverage(BaseModel):
    keyword: str = ""
    present: bool = False

    @field_validator("present", mode="before")
    @classmethod
    def _boolish(cls, value):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)


class MatchAnalysis(BaseModel):
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    keyword_coverage: list[KeywordCoverage] = Field(default_factory=list)
    emphasis: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)

    @field_validator(
        "matched_skills",
        "missing_skills",
        "emphasis",
        "gaps",
        "talking_points",
        mode="before",
    )
    @classmethod
    def _lists(cls, value):
        return _string_list(value)

    @field_validator("keyword_coverage", mode="before")
    @classmethod
    def _coverage(cls, value):
        if not value:
            return []
        out = []
        for item in value:
            if isinstance(item, str):
                out.append({"keyword": item, "present": False})
            elif isinstance(item, dict):
                out.append(item)
        return out


class TailorPack(BaseModel):
    cv: Profile
    cover_letter: str = ""
    match: MatchAnalysis = Field(default_factory=MatchAnalysis)


class ApplicationStatus(str, Enum):
    saved = "saved"
    applied = "applied"
    under_consideration = "under_consideration"
    rejected = "rejected"
    declined = "declined"


APPLICATION_STATUSES: list[dict[str, str]] = [
    {"value": ApplicationStatus.saved.value, "label": "Saved", "hint": "Not applied yet"},
    {"value": ApplicationStatus.applied.value, "label": "Applied", "hint": "You have submitted an application"},
    {
        "value": ApplicationStatus.under_consideration.value,
        "label": "Under consideration",
        "hint": "They are reviewing you",
    },
    {"value": ApplicationStatus.rejected.value, "label": "Rejected", "hint": "They rejected you"},
    {"value": ApplicationStatus.declined.value, "label": "Declined", "hint": "You declined or rejected them"},
]

STATUS_LABELS = {item["value"]: item["label"] for item in APPLICATION_STATUSES}


def parse_status(value: Optional[str]) -> ApplicationStatus:
    try:
        return ApplicationStatus((value or "").strip())
    except ValueError:
        return ApplicationStatus.saved


class Company(BaseModel):
    id: Optional[int] = None
    name: str = ""
    website: str = ""
    location: str = ""
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    position_count: int = 0


class Position(BaseModel):
    """A role at a company, plus the job-description source used to tailor a CV."""

    id: Optional[int] = None
    title: str = ""
    company_id: Optional[int] = None
    company_name: str = ""
    url: str = ""
    location: str = ""
    source_text: str = ""
    required_skills: list[str] = Field(default_factory=list)
    desired_skills: list[str] = Field(default_factory=list)
    notes: str = ""
    scrape_warning: str = ""
    status: ApplicationStatus = ApplicationStatus.saved
    status_note: str = ""
    applied_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    has_generation: bool = False
