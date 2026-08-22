from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.cv_layout import contact_bits, role_dates, skill_lines
from app.richtext import letter_html, sanitize_rich

templates = Jinja2Templates(directory=str(settings.templates_dir))
templates.env.globals["cv_skill_lines"] = skill_lines
templates.env.globals["cv_contact_bits"] = contact_bits
templates.env.globals["cv_role_dates"] = role_dates
templates.env.filters["rich"] = sanitize_rich
templates.env.filters["letter_html"] = letter_html
