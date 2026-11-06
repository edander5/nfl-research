import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_require_credentials(monkeypatch):
    for name in ["APP_DB_HOST", "APP_DB_NAME", "APP_DB_USER", "APP_DB_PASSWORD"]:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_password_is_redacted_and_url_handles_special_characters():
    password = "SYNTHETIC:/@?# value"
    settings = Settings(db_host="localhost", db_name="synthetic", db_user="synthetic", db_password=password)
    assert password not in repr(settings)
    assert password not in str(settings.database_url)
    assert settings.database_url.password == password


@pytest.mark.parametrize("password", ["", "   "])
def test_blank_password_rejected(password):
    with pytest.raises(ValidationError):
        Settings(db_host="localhost", db_name="synthetic", db_user="synthetic", db_password=password)
