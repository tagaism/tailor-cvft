from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import ensure_data_dirs, settings
from app.db import init_db
from app.routers import api, jobs


def _cors_origins() -> list[str]:
    origin = settings.ui_origin
    origins = {origin}
    if "127.0.0.1" in origin:
        origins.add(origin.replace("127.0.0.1", "localhost", 1))
    elif "localhost" in origin:
        origins.add(origin.replace("localhost", "127.0.0.1", 1))
    return sorted(origins)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_data_dirs()
    init_db()
    yield


app = FastAPI(title="tailor-cvft", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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
    return RedirectResponse(settings.ui_origin, status_code=303)
