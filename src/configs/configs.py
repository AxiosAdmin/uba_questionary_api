"""Application settings and configuration management using environment variables."""

import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    OPENAI_API_KEY: str
    FERNET_KEY: str
    JWT_SECRET_KEY: str
    ALGORITHM: str
    JWT_EXPIRATION_MINUTES: int
    RESTRICT_STRIPE_AUTH_KEY: str
    PUBLIC_STRIPE_AUTH_KEY: str
    SECRET_STRIPE_AUTH_KEY: str
    WEBHOOK_STRIPE_SECRECT_KEY: str

    FRONTEND_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ai-questionary-front-iyek.vercel.app",
        "https://aiquestionaryfront-production.up.railway.app",
        "https://dev.axiosacademy.com.br",
    ]

    @field_validator("FRONTEND_ORIGINS", mode="before")
    @classmethod
    def parse_frontend_origins(cls, value: Any) -> list[str]:
        """Support either a list or a comma-separated string of allowed origins."""
        if isinstance(value, str):
            if value.strip().startswith("["):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def database_url(self):
        """Build the database URL from individual components."""
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        """Configuration for loading environment variables from a .env file."""

        env_file = ".env"


settings = Settings()  # type: ignore[call-arg]
