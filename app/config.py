from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "lmstudio"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: float | None = None
    llm_in_docker: bool = False
    data_dir: Path = ROOT_DIR / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "resumeer.db"

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "profile.json"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def templates_dir(self) -> Path:
        return APP_DIR / "templates"

    @property
    def static_dir(self) -> Path:
        return APP_DIR / "static"


settings = Settings()


def ensure_data_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
