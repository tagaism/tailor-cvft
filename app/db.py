from collections.abc import Generator

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_jobs()
    _migrate_generations()
    _backfill_companies()


def _table_columns(table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _migrate_jobs() -> None:
    columns = _table_columns("jobs")
    statements = []
    if "company_id" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN company_id INTEGER")
    if "status" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN status VARCHAR(40) DEFAULT 'saved'")
    if "status_note" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN status_note TEXT DEFAULT ''")
    if "applied_at" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN applied_at DATETIME")
    if "location" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN location VARCHAR(400) DEFAULT ''")
    if "required_skills" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN required_skills TEXT DEFAULT ''")
    if "desired_skills" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN desired_skills TEXT DEFAULT ''")
    if not statements:
        return
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _migrate_generations() -> None:
    columns = _table_columns("generations")
    if "cv_style" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE generations ADD COLUMN cv_style VARCHAR(40) DEFAULT 'times'"))


def _backfill_companies() -> None:
    from app.models import Job
    from app.services.companies import link_job_company

    db = SessionLocal()
    try:
        jobs = db.scalars(select(Job)).all()
        dirty = False
        for job in jobs:
            if job.company and not job.company_id:
                link_job_company(db, job, job.company)
                dirty = True
            if not job.status:
                job.status = "saved"
                dirty = True
        if dirty:
            db.commit()
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
