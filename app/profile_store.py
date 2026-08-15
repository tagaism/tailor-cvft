from __future__ import annotations

import json

from app.config import settings
from app.schemas import Profile


def load_profile() -> Profile:
    path = settings.profile_path
    if not path.exists():
        return Profile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Profile.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return Profile()


def save_profile(profile: Profile) -> None:
    settings.profile_path.parent.mkdir(parents=True, exist_ok=True)
    settings.profile_path.write_text(
        profile.model_dump_json(indent=2),
        encoding="utf-8",
    )
