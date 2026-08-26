from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dental Claims Engine"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/claims_db"

    JWT_SECRET_KEY: str = "insecure_dev_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = Field(default="dental-claims-engine")
    JWT_AUDIENCE: str = Field(default="dental-claims-api")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_security_defaults(self) -> Self:
        if self.ENVIRONMENT in ("production", "staging"):
            if "insecure" in self.JWT_SECRET_KEY.lower() or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    f"Insecure JWT_SECRET_KEY detected for environment '{self.ENVIRONMENT}'. "
                    "Must be at least 32 characters and cannot use default dev string."
                )

            if "localhost" in self.DATABASE_URL or "127.0.0.1" in self.DATABASE_URL:
                raise ValueError(
                    f"Local database host in DATABASE_URL is not allowed in '{self.ENVIRONMENT}' environment."
                )

        return self


settings = Settings()
