from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "peptalk"
    app_env: Literal["local", "ci", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_file: Path = Path("data/sample_records.json")
    database_url: SecretStr | None = None

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log level string to uppercase if provided."""
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("data_file")
    @classmethod
    def validate_data_file_extension(cls, path: Path) -> Path:
        """Validate that the configured data source is a JSON file."""
        if path.suffix.lower() != ".json":
            raise ValueError(f"Configured data_file '{path}' must have a .json extension.")
        return path

    @property
    def is_production(self) -> bool:
        """Return True if running in production environment."""
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        """Return True if running in CI or test environment."""
        return self.app_env == "ci"


@lru_cache
def get_settings() -> Settings:
    return Settings()
