# Pinned to the official uv image so dependency resolution uses the committed
# lockfile rather than a host-installed package manager.
FROM ghcr.io/astral-sh/uv:0.12.19-python3.14-trixie-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

# Keep third-party dependencies in a cacheable layer. This project intentionally
# has no build-system: it runs the in-repo `app` package directly.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-editable

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
# The policy assistant reads this committed, precomputed index at runtime.
COPY docs/policy-index ./docs/policy-index
RUN uv sync --locked --no-editable

RUN groupadd --system docuguard \
    && useradd --system --gid docuguard --create-home docuguard \
    && mkdir -p /app/data/documents \
    && chown -R docuguard:docuguard /app

USER docuguard

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
