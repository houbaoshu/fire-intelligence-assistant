# Deployment and Operations

Production deployment uses independent frontend and backend containers, PostgreSQL,
protected object storage, and the durable database-backed task worker included in the
FastAPI process. Set all required secrets in the deployment secret manager; never place
them in frontend `VITE_*` variables.

## Required production values

- `POSTGRES_PASSWORD`
- `APP_AUTH_SECRET_KEY` (at least 32 characters)
- `APP_AI_BASE_URL`, `APP_AI_API_KEY`, and capability model names for AI workflows

Start the local production topology with `docker compose up --build`. The backend applies
Alembic migrations before serving traffic. `/health` is the readiness endpoint and the
authenticated administrator endpoint `/api/system/metrics` exposes bounded request counters.

## Backup and restore

Run `backend/scripts/backup.sh` with the database URL and storage root. A complete restore
requires both the database dump and the matching object-storage archive. Test restoration
regularly in an isolated environment before relying on a backup policy. Vector data is stored
as derived knowledge chunks and can also be rebuilt from protected source documents.

## Scaling boundary

The included task dispatcher is durable across application restarts and suitable for a
single API replica. Before running multiple API replicas, move task claiming to a queue with
leases (for example Redis plus a worker service) to prevent two processes from claiming the
same queued task. Uploaded media processing also requires FFmpeg in worker images.
