# Deployment Guide

The app has three deployable pieces:

| Piece    | Tech                     | Artifact                        |
| -------- | ------------------------ | ------------------------------- |
| Backend  | FastAPI + gunicorn/uvicorn | `backend/` (Dockerfile)       |
| Database | PostgreSQL (prod)        | managed instance                |
| Frontend | React PWA (static)       | `frontend/dist/` via nginx      |

Local development still uses SQLite and the Vite dev server — nothing here
changes that. See the main `README.md` for the dev quick start.

---

## Configuration

All backend config is via environment variables (see
`backend/.env.production.example`). Key ones:

| Variable        | Required | Notes                                                        |
| --------------- | -------- | ------------------------------------------------------------ |
| `DATABASE_URL`  | yes      | `postgres://`, `postgresql://`, or `postgresql+psycopg://` — all normalized to the psycopg driver automatically. |
| `SECRET_KEY`    | yes      | Long random string. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS`  | yes      | Comma-separated; must include the deployed frontend origin.  |
| `SALON_TZ`      | no       | IANA timezone (default `Asia/Kolkata`).                      |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | no | Used by `python -m app.seed`.               |
| `WEB_CONCURRENCY` | no     | gunicorn worker count (default 2).                           |

The frontend reads `VITE_API_BASE` **at build time** — it must be the
browser-facing backend URL (e.g. `https://api.example.com`). For Docker builds,
pass it as a build arg.

---

## Option 1 — Docker Compose (self-hosted / VPS / local prod-like)

Brings up Postgres + backend + nginx-served frontend together.

```bash
cp .env.docker.example .env      # edit secrets/URLs
docker compose up --build
# seed sample data + admin once:
docker compose exec backend python -m app.seed
```

- Frontend: http://localhost:8080
- Backend:  http://localhost:8000
- Postgres data persists in the `pgdata` volume.

For a real host, put a TLS-terminating reverse proxy (Caddy/Traefik/nginx) in
front, set `CORS_ORIGINS`/`VITE_API_BASE` to your real HTTPS URLs, and use
strong secrets.

---

## Option 2 — Managed hosts (Render + Vercel)

### Database
Create a managed Postgres instance and copy its connection URL into
`DATABASE_URL`.

### Backend (Render Web Service, from `backend/`)
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT`
  (or use the provided `backend/Dockerfile`)
- Set env vars: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `SALON_TZ`.
- Seed once via the host shell: `python -m app.seed`.

### Frontend (Vercel/Netlify, from `frontend/`)
- Build: `npm run build`  → Output: `dist`
- Env: `VITE_API_BASE=https://your-backend-host` (full backend URL).
- After deploy, add the frontend URL to the backend's `CORS_ORIGINS`.

---

## Schema changes / migrations

Tables are auto-created on startup via `init_db()` (`SQLModel.metadata.create_all`).
This is fine for the **first** deploy, but `create_all` does **not** alter
existing tables. For later schema changes against a live Postgres DB, introduce
Alembic (already a dependency) and run migrations as part of deploy. Until then,
schema changes require a manual migration or a fresh DB.

---

## Pre-deploy checklist

- [ ] `SECRET_KEY` set to a strong random value (not the dev default).
- [ ] `DATABASE_URL` points to Postgres.
- [ ] `CORS_ORIGINS` includes the exact frontend origin (scheme + host).
- [ ] `VITE_API_BASE` set to the backend URL for the frontend build.
- [ ] Ran `python -m app.seed` (or created an admin) on the prod DB.
- [ ] Changed the seeded admin password.
