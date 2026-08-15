from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.llm import llm_health

templates = Jinja2Templates(directory=str(settings.templates_dir))


def template_context(request, **extra):
    ctx = {
        "request": request,
        "llm": llm_health(),
        **extra,
    }
    return ctx
