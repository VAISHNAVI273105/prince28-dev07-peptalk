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
    git_sha: str = "dev"

    # LLM gateway (Day 8). Keys default to empty so tests and CI never need them.
    gemini_api_key: str = ""
    groq_api_key: str = ""
    llm_primary_model: str = "gemini-3.8-flash"
    llm_fallback_model: str = "openai/gpt-oss-20b"
    # Both providers speak the OpenAI API, so any compatible server works (Ollama, a test fake).
    llm_primary_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_fallback_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = 30.0
    usd_inr: float = 95.0  # rupees per US dollar, for cost estimates
    prompts_dir: Path = Path("prompts")

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
