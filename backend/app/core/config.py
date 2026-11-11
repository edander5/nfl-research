from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_", extra="ignore", hide_input_in_errors=True
    )

    refresh_state_dir: Path = Path("/app/refresh-state")
    refresh_stale_after_hours: int = Field(default=36, ge=1, le=8760)

    db_purpose: Literal["runtime", "migration"] = "runtime"

    db_host: str = Field(min_length=1)
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = Field(min_length=1)
    db_user: str = Field(min_length=1)
    db_password: SecretStr

    @field_validator("db_password")
    @classmethod
    def require_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("A database password is required")
        return value

    @property
    def database_url(self) -> URL:
        # URL.create handles reserved characters without string interpolation.
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )
