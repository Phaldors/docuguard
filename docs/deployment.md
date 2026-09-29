# Production container and CI

DocuGuard ships a production image and a separate production Compose topology.
This is intentionally distinct from `compose.yaml`, which exists for local
development and the disposable test database.

## What the production topology does

- `postgres` keeps database state in the named `postgres_data` volume.
- `migrate` applies Alembic migrations once and must finish successfully before
  the API can start.
- `api` runs as an unprivileged `docuguard` user, persists uploaded documents in
  the separate `documents_data` volume, and exposes `/health` as its container
  health check.
- The API container sets `DOCUGUARD_RUN_MIGRATIONS=false` because the separate
  `migrate` service owns migrations. The image defaults this switch to true so
  a single-instance portfolio host that does not support pre-deploy commands
  can still initialise its own schema.
- Secrets come from environment variables. No `.env` file or API key is copied
  into the image.

## Run locally in production mode

Copy the committed example and replace every placeholder before starting:

```bash
cp .env.example .env
docker compose --env-file .env -f compose.production.yaml up --build
```

Open `http://127.0.0.1:8000/health` after the API health check turns healthy.
The model-backed extraction and policy-assistant endpoints need
`DOCUGUARD_OPENAI_API_KEY`; storage, deterministic reconciliation, the reviewer
screen, and the demo fixture do not.

## CI guarantees

`.github/workflows/ci.yml` pins the official GitHub Actions used for checkout
and `uv`, installs the locked dependency graph, runs Ruff, migrates a dedicated
PostgreSQL test database from CI-only environment variables, runs the full test
suite, and builds the production image. It does not rely on a local `.env.test`
file, which is deliberately ignored by Git. It does not deploy. Deployment
remains an explicit environment-specific decision rather than an accidental
side effect of merging to `main`.
