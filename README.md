# Salon Booking PWA

A single-salon haircut booking application. Customers browse services, pick a
stylist, see real open time slots, and book/cancel appointments. A salon admin
manages services, stylists, and views all bookings.

Delivered as a **Progressive Web App** (installable on web + mobile from one
codebase) with a **FastAPI** backend.

- **Backend:** Python, FastAPI, SQLModel/SQLAlchemy 2.0, Pydantic v2, JWT auth,
  SQLite (Postgres-ready). Pure availability engine with unit tests.
- **Frontend:** React + TypeScript + Vite, `vite-plugin-pwa` (Workbox, prompt
  updates), React Router.

---

## Prerequisites

- **Python 3.11+** (developed/tested on 3.14)
- **Node.js LTS** (18+; developed/tested on 24). On Windows:
  `winget install OpenJS.NodeJS.LTS`

---

## Quick start (Windows / PowerShell)

Two convenience scripts are provided at the repo root. Run each in its own terminal:

```powershell
# Terminal 1 — backend (creates venv, installs deps, seeds DB, runs on :8000)
powershell -ExecutionPolicy Bypass -File .\run-backend.ps1

# Terminal 2 — frontend (installs deps, runs on :5173)
powershell -ExecutionPolicy Bypass -File .\run-frontend.ps1
```

Then open **http://localhost:5173**. The dev server proxies `/api` → `http://127.0.0.1:8000`.

### Seed accounts

| Role     | Email                | Password     |
| -------- | -------------------- | ------------ |
| Admin    | `admin@salon.test`   | `admin12345` |
| Customer | `customer@salon.test`| `customer123`|

---

## Manual setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env            # optional; defaults work out of the box
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # production build -> dist/ (generates service worker + manifest)
npm run preview    # serve the production build
```

> On Windows, if `npm` is blocked by PowerShell execution policy, call
> `& "C:\Program Files\nodejs\npm.cmd" <cmd>` and ensure the Node folder is on
> PATH for the session:
> `$env:Path = "C:\Program Files\nodejs;" + $env:Path`

---

## Tests

### Backend (pytest)

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Covers: health, auth + role guards, service/stylist CRUD access control, the
pure availability engine (edge cases), the booking flow, double-booking
prevention (409), cancellation freeing the slot, and ownership checks.

### End-to-end (against a running server)

```powershell
# with the backend running + seeded on :8000
cd backend
.\.venv\Scripts\python.exe e2e_check.py http://127.0.0.1:8000
```

Runs: register → availability → book → verify slot disappears → double-book
rejected → history → cancel → verify slot returns.

### Frontend (vitest)

```powershell
cd frontend
npm test
```

---

## Configuration

### Backend (`backend/.env`)

| Variable                      | Default                                 | Purpose                                   |
| ----------------------------- | --------------------------------------- | ----------------------------------------- |
| `DATABASE_URL`                | `sqlite:///./salon.db`                  | DB connection. Swap to Postgres for prod. |
| `SECRET_KEY`                  | (dev placeholder)                       | JWT signing key. **Change in prod.**      |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440`                                  | Token lifetime.                           |
| `CORS_ORIGINS`                | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origins.           |
| `SLOT_INTERVAL_MINUTES`       | `15`                                    | Slot granularity.                         |
| `BOOKING_BUFFER_MINUTES`      | `0`                                     | Buffer around each booking.               |
| `SALON_TZ`                    | `Asia/Kolkata`                          | IANA timezone for working hours + past-slot cutoff. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | seed admin creds                     | Used by the seed script.                  |

### Frontend (`frontend/.env`)

| Variable        | Default | Purpose                                                        |
| --------------- | ------- | -------------------------------------------------------------- |
| `VITE_API_BASE` | `/api`  | API base. In dev it's proxied. Set to a full URL for prod.     |

---

## API overview

| Method | Path                          | Auth      | Description                          |
| ------ | ----------------------------- | --------- | ------------------------------------ |
| GET    | `/health`                     | —         | Health check                         |
| POST   | `/auth/register`              | —         | Register customer, returns JWT       |
| POST   | `/auth/login`                 | —         | OAuth2 form login                    |
| POST   | `/auth/login-json`            | —         | JSON login (used by the SPA)         |
| GET    | `/auth/me`                    | user      | Current user                         |
| GET    | `/services`                   | —         | List services                        |
| POST   | `/services`                   | admin     | Create service                       |
| PATCH  | `/services/{id}`              | admin     | Update service                       |
| DELETE | `/services/{id}`              | admin     | Delete service                       |
| GET    | `/stylists`                   | —         | List stylists (+ services + hours)   |
| POST   | `/stylists`                   | admin     | Create stylist                       |
| PATCH  | `/stylists/{id}`              | admin     | Update stylist                       |
| DELETE | `/stylists/{id}`              | admin     | Delete stylist                       |
| GET    | `/availability`               | —         | Open slots for stylist+service+date  |
| POST   | `/appointments`               | user      | Book (double-booking guarded)        |
| GET    | `/appointments/me`            | user      | My appointment history               |
| GET    | `/appointments`               | admin     | All appointments                     |
| PATCH  | `/appointments/{id}/cancel`   | owner/admin | Cancel appointment                 |

---

## Project structure

```
salon-booking/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, router wiring, /health
│   │   ├── config.py         # pydantic-settings config
│   │   ├── db.py             # engine + session dependency
│   │   ├── models.py         # SQLModel entities
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── security.py       # bcrypt hashing + JWT
│   │   ├── deps.py           # auth dependencies + admin guard
│   │   ├── availability.py   # PURE slot-generation engine
│   │   ├── seed.py           # sample data + admin
│   │   └── routers/          # auth, services, stylists, availability, appointments
│   ├── tests/                # pytest (unit + API)
│   ├── e2e_check.py          # end-to-end integration script
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api.ts            # typed fetch client + token handling
│   │   ├── types.ts          # types mirroring the API
│   │   ├── auth.tsx          # AuthProvider / useAuth
│   │   ├── App.tsx           # nav + routes + protected routes
│   │   └── pages/            # Booking, Login, Register, History, Admin
│   ├── public/               # icons, manifest assets
│   └── vite.config.ts        # PWA + dev proxy + vitest config
├── run-backend.ps1
└── run-frontend.ps1
```

---

## Notes & design decisions

- **Availability engine is pure** (`app/availability.py`): it takes plain data
  (working periods + existing bookings) and returns slots, making it trivial to
  unit-test edge cases (no hours, fully booked, service longer than window,
  buffers, past slots).
- **Times are stored as naive UTC** consistently across the engine, DB, and
  booking logic. The booking endpoint normalizes any timezone-aware input to
  naive UTC.
- **Double-booking prevention:** booking re-checks for overlapping non-cancelled
  appointments (with optional buffer) before inserting.
- **PWA:** built with `vite-plugin-pwa` using `registerType: 'prompt'` so users
  are asked before loading a new version (avoids stale bundles). API calls use a
  network-first runtime cache; the app shell is precached for offline loading.
- **Notifications** (email/SMS) are intentionally deferred to a later phase.
- **Postgres upgrade path:** set `DATABASE_URL` to a Postgres URL. For
  production migrations, introduce Alembic (the models are already structured
  for it); the current setup auto-creates tables on startup for simplicity.
