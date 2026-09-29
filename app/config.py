from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuGuard"
    environment: str = "development"
    database_url: str
    openai_api_key: SecretStr | None = None
    extraction_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-small"
    reranker_model: str = "gpt-5-mini"
    policy_assistant_model: str = "gpt-5-mini"
    public_demo: bool = False
    demo_review_token: SecretStr | None = None
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="DOCUGUARD_",
    )
    document_storage_path: Path = Path("data/documents")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_url(cls, value: str) -> str:
        """Accept managed-Postgres URLs while keeping SQLAlchemy async internally.

        Render and several other managed Postgres providers expose a standard
        ``postgresql://`` connection string. SQLAlchemy's async engine requires
        the explicit ``postgresql+asyncpg://`` dialect prefix instead.
        """
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
