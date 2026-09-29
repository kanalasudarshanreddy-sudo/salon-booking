# Project Progress — Salon Booking PWA

_Last updated: 2026-09-28_

## 1. Overview

A single-salon haircut booking application, built as a Progressive Web App
(PWA) so it works on web and mobile from one codebase, with a Python FastAPI
backend.

- **Customers:** browse services, pick a stylist, see real open time slots,
  book and cancel appointments, view history.
- **Admin:** manage services and stylists (with working hours), view all bookings.
- **Scope:** learning-focused but launch-capable. Notifications (email/SMS)
  intentionally deferred.

**Location:** `C:\Users\kanal\KIRO_Projects\salon-booking\`
**GitHub:** https://github.com/kanalasudarshanreddy-sudo/salon-booking (branch `main`)

---

## 2. Tech stack (Option 2 chosen)

| Layer     | Technology |
| --------- | ---------- |
| Backend   | Python, FastAPI, SQLModel / SQLAlchemy 2.0, Pydantic v2, JWT (python-jose), bcrypt, pytest + httpx |
| Frontend  | React 18 + TypeScript + Vite 6, vite-plugin-pwa (Workbox, `registerType: 'prompt'`), React Router, vitest |
| Database  | SQLite (dev), Postgres-ready via `DATABASE_URL` |
| Auth      | JWT bearer tokens, role-based (customer / admin) |

---

## 3. Environment

- **OS:** Windows (PowerShell)
- **Python:** 3.14.7 (venv at `backend/.venv`)
- **Node.js:** LTS 24.19.0, npm 11.17.0 (installed via `winget install OpenJS.NodeJS.LTS`)
- **Git:** 2.55.0

### System changes made
- Added `C:\Program Files\nodejs` to the **user PATH** (persistent) so
  `node`/`npm`/`npx` work in any terminal.
- Set PowerShell execution policy to `RemoteSigned` (CurrentUser) so `npm.ps1`
  runs in PowerShell.

> Note: open a **new** terminal for these to take effect.

---

## 4. Implementation status — ALL 11 TASKS COMPLETE

| # | Task | Status |
| - | ---- | ------ |
| 1 | Backend scaffold + health check | ✅ |
| 2 | Data models + seed script | ✅ |
| 3 | Authentication and roles | ✅ |
| 4 | Services & stylists CRUD (admin writes, public reads) | ✅ |
| 5 | Availability engine (pure fn + endpoint, unit tests) | ✅ |
| 6 | Booking & cancellation (double-booking prevention) | ✅ |
| 7 | Frontend PWA scaffold | ✅ |
| 8 | Customer booking flow | ✅ |
| 9 | Auth + appointment history (frontend) | ✅ |
| 10 | Admin view (frontend) | ✅ |
| 11 | Integration, seed, README, run scripts, e2e | ✅ |

---

## 5. Verification results

- **Backend pytest:** 15 passed (7 availability unit tests + 8 API tests) —
  health, auth + role guards, CRUD access control, booking flow,
  double-booking 409, cancel-frees-slot, ownership checks.
- **Frontend build:** `tsc -b && vite build` succeeds; generates `dist/sw.js`
  + `manifest.webmanifest` with 12 precache entries.
- **Frontend vitest:** 2 passed (shell renders; unauthenticated `/history`
  redirects to `/login`).
- **End-to-end (live server):** PASSED — public reads → register →
  availability (31 slots) → book → slot disappears → double-book 409 →
  history → cancel → slot returns.
- **Live run:** backend `/health` ok; frontend serves 200; proxy
  `/api/services` returned 5 services (full chain works).

---

## 6. Project structure

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
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api.ts            # typed fetch client + token handling
│   │   ├── types.ts          # types mirroring the API
│   │   ├── auth.tsx          # AuthProvider / useAuth
│   │   ├── App.tsx           # nav + routes + protected routes
│   │   └── pages/            # Booking, Login, Register, History, Admin
│   ├── public/               # favicon, icons, robots.txt
│   ├── vite.config.ts        # PWA + dev proxy + vitest config
│   └── .env.example
├── run-backend.ps1
├── run-frontend.ps1
└── README.md
```

---

## 7. Data model

- **Customer**: id, name, email, password_hash, role (customer/admin)
- **Service**: id, name, duration_min, price, category, active
- **Stylist**: id, name, bio, active
- **WorkingHours**: id, stylist_id, weekday (0=Mon), start, end
- **Appointment**: id, customer_id, stylist_id, service_id, start, end, status
- **StylistServiceLink**: many-to-many (stylist ↔ services offered)

Relationships: Customer 1—* Appointment; Stylist 1—* Appointment;
Service 1—* Appointment; Stylist 1—* WorkingHours; Stylist *—* Service.

---

## 8. API endpoints

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| GET | `/health` | — | Health check |
| POST | `/auth/register` | — | Register customer, returns JWT |
| POST | `/auth/login` | — | OAuth2 form login |
| POST | `/auth/login-json` | — | JSON login (used by SPA) |
| GET | `/auth/me` | user | Current user |
| GET | `/services` | — | List services |
| POST/PATCH/DELETE | `/services[/{id}]` | admin | Manage services |
| GET | `/stylists` | — | List stylists (+ services + hours) |
| POST/PATCH/DELETE | `/stylists[/{id}]` | admin | Manage stylists |
| GET | `/availability` | — | Open slots for stylist+service+date |
| POST | `/appointments` | user | Book (double-booking guarded) |
| GET | `/appointments/me` | user | My history |
| GET | `/appointments` | admin | All appointments |
| PATCH | `/appointments/{id}/cancel` | owner/admin | Cancel |

---

## 9. How to run (local testing)

Two terminals. Everything is already installed/seeded.

**Terminal 1 — backend (port 8000):**
```powershell
cd C:\Users\kanal\KIRO_Projects\salon-booking
powershell -ExecutionPolicy Bypass -File .\run-backend.ps1
```

**Terminal 2 — frontend (port 5173):**
```powershell
cd C:\Users\kanal\KIRO_Projects\salon-booking
powershell -ExecutionPolicy Bypass -File .\run-frontend.ps1
```

Then open **http://localhost:5173**.
API docs: **http://127.0.0.1:8000/docs**

### Direct commands (alternative)
```powershell
# backend
cd C:\Users\kanal\KIRO_Projects\salon-booking\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# frontend
cd C:\Users\kanal\KIRO_Projects\salon-booking\frontend
npm run dev
```

### Stop the servers
```powershell
# stop whatever is listening on the two ports
foreach ($port in 8000,5173) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
}
```

### Seed accounts
| Role | Email | Password |
| ---- | ----- | -------- |
| Admin | `admin@salon.test` | `admin12345` |
| Customer | `customer@salon.test` | `customer123` |

---

## 10. Tests

```powershell
# Backend unit + API
cd C:\Users\kanal\KIRO_Projects\salon-booking\backend
.\.venv\Scripts\python.exe -m pytest -q

# End-to-end (backend must be running + seeded on :8000)
.\.venv\Scripts\python.exe e2e_check.py http://127.0.0.1:8000

# Frontend
cd C:\Users\kanal\KIRO_Projects\salon-booking\frontend
npm test
```

---

## 11. Key design decisions

- **Pure availability engine** (`app/availability.py`): takes plain data
  (working periods + existing bookings) and returns slots — easy to unit-test
  edge cases (no hours, fully booked, service longer than window, buffers,
  past slots).
- **Naive UTC everywhere**: times stored/compared as naive UTC across engine,
  DB, and booking logic. The booking endpoint normalizes timezone-aware input
  to naive UTC.
- **Double-booking prevention**: booking re-checks for overlapping
  non-cancelled appointments (with optional buffer) before inserting.
- **PWA update strategy**: `registerType: 'prompt'` asks users before loading
  a new version (avoids stale bundles); API calls use a network-first runtime
  cache; app shell precached for offline loading.
- **Postgres upgrade path**: set `DATABASE_URL` to a Postgres URL; models are
  structured so Alembic can be introduced. Current dev setup auto-creates
  tables on startup.

### Notable fixes during the build
- Used **bcrypt directly** (not passlib) due to passlib 1.7.4 incompatibility
  with bcrypt 5.x.
- `models.py` must **not** use `from __future__ import annotations`
  (SQLModel/SQLAlchemy 2.0 relationship resolution). Uses `typing.List/Optional`.
- SQLModel 0.0.47 defaults `datetime` to `UTCDateTime` (requires aware
  datetimes). Fixed with explicit `sa_column=Column(DateTime)` for naive UTC
  storage.
- Test fixture imports FastAPI app as `fastapi_app` to avoid shadowing the
  `app` package.

---

## 12. Git

- Repo initialized; branch renamed `master` → `main`.
- Initial commit `a8619f8` — "Initial commit: single-salon haircut booking PWA
  (FastAPI + React PWA)" — 53 files.
- Remote `origin` → https://github.com/kanalasudarshanreddy-sudo/salon-booking
- Pushed and tracking `origin/main`.

### Everyday workflow
```powershell
git add -A
git commit -m "your message"
git push
git pull   # to fetch remote changes
```

`.gitignore` excludes: `node_modules/`, `.venv/`, `*.db`, `dist/`,
`*.tsbuildinfo`, `.env`. Only `.env.example` files are committed (no secrets).

---

## 13. Known minor items / future work

- Backend emits harmless `datetime.utcnow()` deprecation warnings — switch to
  timezone-aware UTC in a cleanup pass.
- Introduce Alembic migrations for production DB changes.
- Add notifications (email/SMS) — deferred phase.
- Optional: deploy frontend (Vercel/Netlify) + backend & Postgres
  (Render/Railway) — swap `DATABASE_URL`, set `VITE_API_BASE`.
