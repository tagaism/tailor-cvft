from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.deps import template_context, templates
from app.forms import profile_from_form
from app.profile_store import load_profile, save_profile
from app.services.llm import LLMError, extract_profile_from_cv
from app.services.merge import merge_profiles
from app.services.parser import ParseError, extract_text

router = APIRouter()


@router.get("/profile", response_class=HTMLResponse)
async def edit_profile(request: Request):
    flash = request.query_params.get("flash", "")
    error = request.query_params.get("error", "")
    return templates.TemplateResponse(
        request,
        "profile/edit.html",
        template_context(
            request,
            profile=load_profile(),
            flash=flash,
            error=error,
            active="profile",
        ),
    )


@router.post("/profile")
async def save_profile_form(request: Request):
    form = await request.form()
    save_profile(profile_from_form(form))
    return RedirectResponse("/profile?flash=saved", status_code=303)


MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/profile/upload")
async def upload_cv(request: Request):
    try:
        form = await request.form(max_part_size=MAX_UPLOAD_BYTES)
    except Exception:
        return RedirectResponse(
            "/profile?error=" + _q("Could not read that upload. Use a PDF, DOCX, or TXT under 20 MB."),
            status_code=303,
        )
    upload = form.get("file")
    if not isinstance(upload, (UploadFile, StarletteUploadFile)) or not upload.filename:
        return RedirectResponse("/profile?error=" + _q("Choose a CV file first, then click Extract and merge."), status_code=303)
    data = await upload.read()
    if not data:
        return RedirectResponse("/profile?error=" + _q("That file was empty."), status_code=303)
    if len(data) > MAX_UPLOAD_BYTES:
        return RedirectResponse("/profile?error=" + _q("That file is larger than 20 MB."), status_code=303)
    try:
        raw = extract_text(upload.filename, data)
        extracted, _model = await asyncio.to_thread(extract_profile_from_cv, raw)
    except ParseError as exc:
        return RedirectResponse(f"/profile?error={_q(str(exc))}", status_code=303)
    except LLMError as exc:
        return RedirectResponse(f"/profile?error={_q(str(exc))}", status_code=303)
    except Exception as exc:
        return RedirectResponse(
            f"/profile?error={_q(f'Upload failed: {exc}')}",
            status_code=303,
        )
    merged = merge_profiles(load_profile(), extracted)
    save_profile(merged)
    return RedirectResponse("/profile?flash=imported", status_code=303)


def _q(message: str) -> str:
    from urllib.parse import quote

    return quote(message)
