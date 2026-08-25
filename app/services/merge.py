from __future__ import annotations

from app.schemas import (
    Certification,
    Contact,
    Education,
    Experience,
    ExperienceProject,
    Profile,
    Project,
)


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def _prefer(existing: str, incoming: str) -> str:
    return existing.strip() or incoming.strip()


def _union_preserve(existing: list[str], incoming: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in existing + incoming:
        key = _norm(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _merge_contact(current: Contact, incoming: Contact) -> Contact:
    return Contact(
        full_name=_prefer(current.full_name, incoming.full_name),
        email=_prefer(current.email, incoming.email),
        phone=_prefer(current.phone, incoming.phone),
        location=_prefer(current.location, incoming.location),
        linkedin=_prefer(current.linkedin, incoming.linkedin),
        github=_prefer(current.github, incoming.github),
        website=_prefer(current.website, incoming.website),
    )


def _merge_experience(current: list[Experience], incoming: list[Experience]) -> list[Experience]:
    merged = [item.model_copy(deep=True) for item in current]
    index = {(_norm(item.company), _norm(item.title)): item for item in merged if item.company or item.title}
    for item in incoming:
        key = (_norm(item.company), _norm(item.title))
        if key in index and any(key):
            existing = index[key]
            existing.location = _prefer(existing.location, item.location)
            existing.start = _prefer(existing.start, item.start)
            existing.end = _prefer(existing.end, item.end)
            existing.current = existing.current or item.current
            existing.projects = _merge_role_projects(existing.projects, item.projects)
            existing.bullets = [
                " — ".join(part for part in [proj.summary.strip(), proj.impact.strip()] if part)
                for proj in existing.projects
            ]
        else:
            copy = item.model_copy(deep=True)
            merged.append(copy)
            if any(key):
                index[key] = copy
    return merged


def _merge_role_projects(
    current: list[ExperienceProject], incoming: list[ExperienceProject]
) -> list[ExperienceProject]:
    merged = [item.model_copy(deep=True) for item in current]
    seen = {_norm(item.summary) for item in merged if item.summary}
    for item in incoming:
        key = _norm(item.summary)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item.model_copy(deep=True))
    return merged


def _merge_education(current: list[Education], incoming: list[Education]) -> list[Education]:
    merged = [item.model_copy(deep=True) for item in current]
    index = {(_norm(item.school), _norm(item.degree)): item for item in merged if item.school or item.degree}
    for item in incoming:
        key = (_norm(item.school), _norm(item.degree))
        if key in index and any(key):
            existing = index[key]
            existing.field = _prefer(existing.field, item.field)
            existing.start = _prefer(existing.start, item.start)
            existing.end = _prefer(existing.end, item.end)
            existing.details = _prefer(existing.details, item.details)
        else:
            copy = item.model_copy(deep=True)
            merged.append(copy)
            if any(key):
                index[key] = copy
    return merged


def _merge_projects(current: list[Project], incoming: list[Project]) -> list[Project]:
    merged = [item.model_copy(deep=True) for item in current]
    index = {_norm(item.name): item for item in merged if item.name}
    for item in incoming:
        key = _norm(item.name)
        if key and key in index:
            existing = index[key]
            existing.url = _prefer(existing.url, item.url)
            existing.description = _prefer(existing.description, item.description)
            existing.bullets = _union_preserve(existing.bullets, item.bullets)
        else:
            copy = item.model_copy(deep=True)
            merged.append(copy)
            if key:
                index[key] = copy
    return merged


def _merge_certs(current: list[Certification], incoming: list[Certification]) -> list[Certification]:
    merged = [item.model_copy(deep=True) for item in current]
    index = {_norm(item.name): item for item in merged if item.name}
    for item in incoming:
        key = _norm(item.name)
        if key and key in index:
            existing = index[key]
            existing.issuer = _prefer(existing.issuer, item.issuer)
            existing.year = _prefer(existing.year, item.year)
        else:
            copy = item.model_copy(deep=True)
            merged.append(copy)
            if key:
                index[key] = copy
    return merged


def merge_profiles(current: Profile, incoming: Profile) -> Profile:
    """Fill empty fields and union list items. Never wipe the existing profile."""
    return Profile(
        contact=_merge_contact(current.contact, incoming.contact),
        summary=_prefer(current.summary, incoming.summary),
        skills=_union_preserve(current.skills, incoming.skills),
        additional_skills=_union_preserve(current.additional_skills, incoming.additional_skills),
        experience=_merge_experience(current.experience, incoming.experience),
        education=_merge_education(current.education, incoming.education),
        projects=_merge_projects(current.projects, incoming.projects),
        certifications=_merge_certs(current.certifications, incoming.certifications),
    )
