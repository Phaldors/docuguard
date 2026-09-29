from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="DOCUGUARD_",
    )
    document_storage_path: Path = Path("data/documents")


@lru_cache
def get_settings() -> Settings:
    return Settings()
