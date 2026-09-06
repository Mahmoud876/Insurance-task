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
    APP_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    OIDC_ISSUER_URL: str = "http://localhost:8080/realms/insurance"
    OIDC_CLIENT_ID: str = "insurance-frontend"
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_SCOPE: str = "openid profile email offline_access"
    OIDC_REDIRECT_PATH: str = "/auth/callback"

    AUTH_REFRESH_COOKIE_NAME: str = "refresh_token"
    AUTH_STATE_COOKIE_NAME: str = "oidc_state"
    AUTH_PKCE_COOKIE_NAME: str = "oidc_pkce_verifier"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_DOMAIN: str | None = None
    AUTH_COOKIE_PATH: str = "/auth"
    AUTH_CALLBACK_COOKIE_MAX_AGE_SECONDS: int = 300
    AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 30

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

            if not self.AUTH_COOKIE_SECURE:
                raise ValueError("AUTH_COOKIE_SECURE must be true in staging/production")

        return self


settings = Settings()
