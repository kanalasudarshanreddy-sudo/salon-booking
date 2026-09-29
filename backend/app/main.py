"""FastAPI application entrypoint for the salon booking API."""
from __future__ import annotations

from contextlib import asynccontextmanager

import email_validator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import appointments, auth, availability, services, stylists

settings = get_settings()

# Permit the RFC 6761 reserved `.test` TLD in email addresses so the documented
# seed/demo accounts (e.g. admin@salon.test) validate. Other special-use
# domains (localhost, invalid, etc.) remain rejected.
email_validator.SPECIAL_USE_DOMAIN_NAMES = [
    d for d in email_validator.SPECIAL_USE_DOMAIN_NAMES if d != "test"
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (fine for SQLite dev; use Alembic for prod).
    init_db()
    yield


app = FastAPI(title="Salon Booking API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(services.router)
app.include_router(stylists.router)
app.include_router(availability.router)
app.include_router(appointments.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
