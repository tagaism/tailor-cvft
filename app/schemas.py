from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Contact(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""


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


class Education(BaseModel):
    school: str = ""
    degree: str = ""
    field: str = ""
    start: str = ""
    end: str = ""
    details: str = ""


class Project(BaseModel):
    name: str = ""
    url: str = ""
    description: str = ""
    bullets: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str = ""
    issuer: str = ""
    year: str = ""


class Profile(BaseModel):
    contact: Contact = Field(default_factory=Contact)
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)

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
    keyword: str
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


class TailorPack(BaseModel):
    cv: Profile
    cover_letter: str = ""
    match: MatchAnalysis = Field(default_factory=MatchAnalysis)
