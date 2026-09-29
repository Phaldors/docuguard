import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("provided", "expected"),
    [
        (
            "postgresql://user:password@db.example/docuguard",
            "postgresql+asyncpg://user:password@db.example/docuguard",
        ),
        (
            "postgres://user:password@db.example/docuguard",
            "postgresql+asyncpg://user:password@db.example/docuguard",
        ),
        (
            "postgresql+asyncpg://user:password@db.example/docuguard",
            "postgresql+asyncpg://user:password@db.example/docuguard",
        ),
    ],
)
def test_settings_normalize_managed_postgres_urls(
    provided: str, expected: str
) -> None:
    settings = Settings(database_url=provided)

    assert settings.database_url == expected
