#!/bin/sh
set -eu

# Render's manual Docker-service flow does not apply Blueprint pre-deploy
# commands. Defaulting this to true keeps a single-instance demo deploy
# self-contained. Production Compose runs migrations as a separate one-shot
# service and sets this to false for the API container.
if [ "${DOCUGUARD_RUN_MIGRATIONS:-true}" = "true" ]; then
  /app/.venv/bin/alembic upgrade head
fi

if [ "${DOCUGUARD_SEED_DEMO:-false}" = "true" ]; then
  /app/.venv/bin/python -m app.scripts.seed_demo --reset
fi

exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
