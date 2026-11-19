from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from peptalk.api.deps import get_document_store
from peptalk.config import Settings
from peptalk.store import DocumentStore


def test_settings_valid_defaults():
    settings = Settings()
    assert settings.app_name == "peptalk"
    assert settings.app_env in {"local", "ci", "production"}
    assert settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR"}
    assert isinstance(settings.data_file, Path)


@pytest.mark.parametrize("env", ["local", "ci", "production"])
def test_settings_valid_app_env(env):
    settings = Settings(app_env=env)
    assert settings.app_env == env


def test_settings_invalid_app_env():
    with pytest.raises(ValidationError):
        Settings(app_env="prod")


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR"])
def test_settings_valid_log_level(level):
    settings = Settings(log_level=level)
    assert settings.log_level == level


def test_settings_invalid_log_level():
    with pytest.raises(ValidationError):
        Settings(log_level="VERBOSE")


def test_get_document_store_dependency():
    settings = Settings(data_file=Path("data/sample_records.json"))
    store = get_document_store(settings=settings)
    assert isinstance(store, DocumentStore)
    assert store.file_path == Path("data/sample_records.json")


def test_settings_app_env_is_required(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_database_url_optional():
    settings = Settings(app_env="local", database_url=None)
    assert settings.database_url is None


def test_settings_database_url_securely_handled():
    url = "postgresql://localhost:5432/secure_db"
    settings = Settings(app_env="local", database_url=url)
    assert isinstance(settings.database_url, SecretStr)
    assert settings.database_url.get_secret_value() == url
    assert "secure_db" not in repr(settings.database_url)
    assert "secure_db" not in repr(settings)
