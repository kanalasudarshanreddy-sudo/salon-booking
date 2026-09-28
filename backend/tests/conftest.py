"""Shared pytest fixtures: isolated file DB + FastAPI TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture()
def client():
    # Import here so app modules pick up defaults.
    from app import db as db_module
    from app.db import get_session
    from app.main import app as fastapi_app

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    # Patch engine used by seed/other modules too.
    db_module.engine = test_engine
    fastapi_app.dependency_overrides[get_session] = override_get_session

    with TestClient(fastapi_app) as c:
        yield c

    fastapi_app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(test_engine)


def register(client, name="User", email="u@test.com", password="password123"):
    return client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_admin_token(client) -> str:
    """Register a user then promote to admin directly in the DB."""
    from app import db as db_module
    from app.models import Customer, Role
    from sqlmodel import Session, select

    register(client, name="Admin", email="admin@test.com", password="admin12345")
    with Session(db_module.engine) as session:
        user = session.exec(
            select(Customer).where(Customer.email == "admin@test.com")
        ).first()
        user.role = Role.admin
        session.add(user)
        session.commit()
    resp = client.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "admin12345"},
    )
    return resp.json()["access_token"]
