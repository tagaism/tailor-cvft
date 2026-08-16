from __future__ import annotations

from app.schemas import Experience, Profile

SKILL_CATEGORIES = (
    "Languages",
    "Databases",
    "Frameworks",
    "Technologies and Tools",
)


def _display_link(url: str) -> str:
    text = (url or "").strip()
    for prefix in ("https://", "http://", "www."):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
    return text.rstrip("/")


def contact_bits(profile: Profile) -> list[str]:
    contact = profile.contact
    bits = []
    if contact.location:
        bits.append(contact.location)
    if contact.phone:
        bits.append(contact.phone)
    if contact.linkedin:
        bits.append(_display_link(contact.linkedin))
    if contact.email:
        bits.append(contact.email)
    elif contact.github:
        bits.append(_display_link(contact.github))
    return bits


def date_span(start: str, end: str, current: bool = False) -> str:
    finish = end or ("Present" if current else "")
    if start and finish:
        return f"{start}-{finish}"
    return start or finish


def role_dates(role: Experience) -> str:
    return date_span(role.start, role.end, role.current)


def skill_lines(profile: Profile) -> list[str]:
    grouped: dict[str, str] = {}
    leftover: list[str] = []
    for item in profile.skills:
        text = (item or "").strip()
        if not text:
            continue
        if ":" in text:
            category, rest = text.split(":", 1)
            grouped[category.strip()] = rest.strip()
        else:
            leftover.append(text)
    lines: list[str] = []
    used = set()
    for category in SKILL_CATEGORIES:
        match = next((key for key in grouped if key.lower() == category.lower()), None)
        if match and grouped[match]:
            lines.append(f"{category}: {grouped[match]}")
            used.add(match)
    for key, value in grouped.items():
        if key not in used and value:
            lines.append(f"{key}: {value}")
    if leftover:
        extra = ", ".join(leftover)
        tech = next((line for line in lines if line.startswith("Technologies and Tools:")), None)
        if tech:
            lines[lines.index(tech)] = f"{tech}, {extra}"
        else:
            lines.append(f"Technologies and Tools: {extra}")
    return lines
