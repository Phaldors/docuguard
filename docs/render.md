# Render demo deployment

`render.yaml` is a Blueprint for a **public portfolio demo**, not a production
customer-document deployment. It creates a Docker web service and Render
Postgres in Frankfurt, runs migrations before every deploy, and seeds the
synthetic reviewer case once after the initial deploy.

## Why the database URL needs no manual rewrite

Render provides its Postgres `connectionString` in standard
`postgresql://…` form. DocuGuard's settings normalize standard
`postgresql://` and `postgres://` URLs to SQLAlchemy's async
`postgresql+asyncpg://` dialect internally. The Blueprint can therefore use
Render's `fromDatabase` reference directly without placing credentials in Git.

## Deploy it

1. In Render, select **New → Blueprint** and connect
   `Phaldors/docuguard`.
2. Render reads `render.yaml`, shows the free web service and free Postgres
   database, then asks for `DOCUGUARD_OPENAI_API_KEY`. It is marked `sync:
   false`, so it is never stored in the repository.
3. Create the Blueprint and wait for the migration, API health check (`/ready`),
   and one-time synthetic seed hook to complete.
4. Open the service URL followed by `/reviewer`.

## Boundaries of the free demo

The free web service has no persistent disk, so uploaded source files can be
lost when the instance restarts. Free Render Postgres is limited to one active
instance per workspace, has no backups, and expires after 30 days. The seeded
reviewer fixture remains appropriate because it can be recreated at any time;
real user documents do not.

Do not market this deployment as durable document storage. Before accepting
real documents, finish the object-storage abstraction in Milestone 1 and use
durable storage plus a backed-up, paid database. This is a deliberate product
boundary, not a deployment shortcut.
