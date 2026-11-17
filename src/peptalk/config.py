
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "peptalk"
    app_env: Literal["local", "ci", "production"]
    log_level: str = "INFO"
    data_file: str = "data/sample_records.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
