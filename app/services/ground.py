from __future__ import annotations

import logging
import re

from app.schemas import Experience, Profile, ShokumuCv, ShokumuEmployer

logger = logging.getLogger(__name__)

_YEAR = re.compile(r"(?:19|20)\d{2}")
_COMPANY_STRIP = re.compile(
    r"株式会社|合同会社|有限会社|\binc\.?\b|\bltd\.?\b|\bllc\b|\bco\.?\b",
    re.I,
)
_FINANCIAL_FIELDS = ("capital", "revenue", "employees", "listing")


def _norm(value: str) -> str:
    return " ".join((value or "").lower().split())


def _company_key(name: str) -> str:
    return _norm(_COMPANY_STRIP.sub("", name or ""))


def _years(value: str) -> set[str]:
    return set(_YEAR.findall(value or ""))


def _profile_blob(profile: Profile) -> str:
    return _norm(" ".join(_iter_profile_text(profile)))


def _iter_profile_text(profile: Profile):
    c = profile.contact
    yield from (c.full_name, c.email, c.phone, c.location, c.linkedin, c.github, c.website)
    yield profile.summary
    yield from profile.skills
    yield from profile.additional_skills
    for role in profile.experience:
        yield from (role.title, role.company, role.location, role.start, role.end, *role.bullets)
        for project in role.projects:
            if project.summary:
                yield project.summary
            if project.impact:
                yield project.impact
    for edu in profile.education:
        yield from (edu.school, edu.degree, edu.field, edu.start, edu.end, edu.location, edu.details)
    for project in profile.projects:
        yield from (project.name, project.url, project.description, *project.bullets)
    for cert in profile.certifications:
        yield from (cert.name, cert.issuer, cert.year)


def _in_profile(value: str, blob: str) -> bool:
    token = _norm(value)
    return bool(token) and token in blob


def _latin_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _company_key(name))


def _roles_for_company(profile: Profile, company: str) -> list[Experience]:
    key = _company_key(company)
    latin = _latin_key(company)
    if not key and not latin:
        return []
    matched = []
    for role in profile.experience:
        other = _company_key(role.company)
        if key and other and (key in other or other in key):
            matched.append(role)
            continue
        olatin = _latin_key(role.company)
        if latin and olatin and min(len(latin), len(olatin)) >= 3 and (latin in olatin or olatin in latin):
            matched.append(role)
    return matched


def _allowed_years(roles: list[Experience]) -> set[str]:
    years: set[str] = set()
    for role in roles:
        years |= _years(role.start) | _years(role.end)
        if role.current:
            years.add("現在")
    return years


def _ground_dates(employer: ShokumuEmployer, roles: list[Experience]) -> None:
    allowed = _allowed_years(roles)
    if not allowed:
        return
    if _years(employer.start) and not (_years(employer.start) & allowed):
        logger.warning("Dropping ungrounded employer start %r for %s", employer.start, employer.company)
        employer.start = roles[0].start
    if _years(employer.end) and not (_years(employer.end) & allowed):
        logger.warning("Dropping ungrounded employer end %r for %s", employer.end, employer.company)
        employer.end = roles[-1].end
    for item in employer.assignments:
        if _years(item.start) and not (_years(item.start) & allowed):
            logger.warning("Dropping ungrounded assignment start %r for %s", item.start, employer.company)
            item.start = employer.start or roles[0].start
        if _years(item.end) and not (_years(item.end) & allowed):
            logger.warning("Dropping ungrounded assignment end %r for %s", item.end, employer.company)
            item.end = employer.end or roles[-1].end


def ground_shokumu_cv(cv: ShokumuCv, profile: Profile) -> ShokumuCv:
    """Strip invented financials and realign dates to the source profile."""
    blob = _profile_blob(profile)
    for employer in cv.employers:
        for field in _FINANCIAL_FIELDS:
            value = getattr(employer, field)
            if value and not _in_profile(value, blob):
                logger.warning("Clearing ungrounded %s %r for %s", field, value, employer.company)
                setattr(employer, field, "")
        roles = _roles_for_company(profile, employer.company)
        if not roles:
            logger.warning("No profile role matched employer %r; using all profile dates", employer.company)
            roles = list(profile.experience)
        if roles:
            _ground_dates(employer, roles)
    return cv
