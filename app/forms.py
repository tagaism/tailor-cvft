from __future__ import annotations

from starlette.datastructures import FormData

from app.schemas import Certification, Contact, Education, Experience, Profile, Project


def _getlist(form: FormData, key: str) -> list[str]:
    return [str(value) for value in form.getlist(key)]


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def parse_skill_text(value: str) -> str:
    """Normalize a skills textarea to one unique skill per line."""
    seen = set()
    out: list[str] = []
    for chunk in (value or "").replace(",", "\n").splitlines():
        skill = chunk.strip()
        key = skill.lower()
        if not skill or key in seen:
            continue
        seen.add(key)
        out.append(skill)
    return "\n".join(out)


def profile_from_form(form: FormData) -> Profile:
    titles = _getlist(form, "exp_title")
    companies = _getlist(form, "exp_company")
    locations = _getlist(form, "exp_location")
    starts = _getlist(form, "exp_start")
    ends = _getlist(form, "exp_end")
    bullets = _getlist(form, "exp_bullets")
    experience: list[Experience] = []
    for index, title in enumerate(titles):
        company = companies[index] if index < len(companies) else ""
        if not title.strip() and not company.strip():
            continue
        end = ends[index] if index < len(ends) else ""
        experience.append(
            Experience(
                title=title.strip(),
                company=company.strip(),
                location=(locations[index] if index < len(locations) else "").strip(),
                start=(starts[index] if index < len(starts) else "").strip(),
                end=end.strip(),
                current=not end.strip() or end.strip().lower() in {"present", "current", "now"},
                bullets=_lines(bullets[index] if index < len(bullets) else ""),
            )
        )

    schools = _getlist(form, "edu_school")
    degrees = _getlist(form, "edu_degree")
    fields = _getlist(form, "edu_field")
    edu_starts = _getlist(form, "edu_start")
    edu_ends = _getlist(form, "edu_end")
    details = _getlist(form, "edu_details")
    education: list[Education] = []
    for index, school in enumerate(schools):
        degree = degrees[index] if index < len(degrees) else ""
        if not school.strip() and not degree.strip():
            continue
        education.append(
            Education(
                school=school.strip(),
                degree=degree.strip(),
                field=(fields[index] if index < len(fields) else "").strip(),
                start=(edu_starts[index] if index < len(edu_starts) else "").strip(),
                end=(edu_ends[index] if index < len(edu_ends) else "").strip(),
                details=(details[index] if index < len(details) else "").strip(),
            )
        )

    names = _getlist(form, "proj_name")
    urls = _getlist(form, "proj_url")
    descriptions = _getlist(form, "proj_description")
    proj_bullets = _getlist(form, "proj_bullets")
    projects: list[Project] = []
    for index, name in enumerate(names):
        if not name.strip():
            continue
        projects.append(
            Project(
                name=name.strip(),
                url=(urls[index] if index < len(urls) else "").strip(),
                description=(descriptions[index] if index < len(descriptions) else "").strip(),
                bullets=_lines(proj_bullets[index] if index < len(proj_bullets) else ""),
            )
        )

    cert_names = _getlist(form, "cert_name")
    issuers = _getlist(form, "cert_issuer")
    years = _getlist(form, "cert_year")
    certifications: list[Certification] = []
    for index, name in enumerate(cert_names):
        if not name.strip():
            continue
        certifications.append(
            Certification(
                name=name.strip(),
                issuer=(issuers[index] if index < len(issuers) else "").strip(),
                year=(years[index] if index < len(years) else "").strip(),
            )
        )

    return Profile(
        contact=Contact(
            full_name=str(form.get("full_name") or "").strip(),
            email=str(form.get("email") or "").strip(),
            phone=str(form.get("phone") or "").strip(),
            location=str(form.get("location") or "").strip(),
            linkedin=str(form.get("linkedin") or "").strip(),
            github=str(form.get("github") or "").strip(),
            website=str(form.get("website") or "").strip(),
        ),
        summary=str(form.get("summary") or "").strip(),
        skills=_lines(str(form.get("skills") or "")),
        experience=experience,
        education=education,
        projects=projects,
        certifications=certifications,
    )
