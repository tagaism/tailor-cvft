from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import ensure_data_dirs, settings
from app.db import init_db
from app.routers import companies, jobs, profile


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_data_dirs()
    init_db()
    yield


app = FastAPI(title="Resumeer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.include_router(jobs.router)
app.include_router(companies.router)
app.include_router(profile.router)


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    from fastapi.responses import RedirectResponse

    return RedirectResponse("/jobs", status_code=303)
