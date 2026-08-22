from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import DEFAULT_UI_ORIGIN, ensure_data_dirs, settings
from app.db import init_db
from app.routers import api, jobs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_data_dirs()
    init_db()
    yield


app = FastAPI(title="tailor-cvft", lifespan=lifespan)
_cors_origins = {
    DEFAULT_UI_ORIGIN,
    "http://localhost:5173",
    settings.ui_origin,
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.include_router(api.router)
app.include_router(jobs.router)


@app.get("/health")
async def health():
    return {"ok": True}


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(settings.ui_origin, status_code=303)
