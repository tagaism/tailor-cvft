from __future__ import annotations


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
