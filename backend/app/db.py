"""Database engine and session management."""
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()


def _normalize_db_url(url: str) -> str:
    """Normalize Postgres URLs to the psycopg (v3) driver.

    Managed providers (Render, Railway, Heroku, etc.) often hand out
    `postgres://` or `postgresql://` URLs. SQLAlchemy needs an explicit driver;
    map both to `postgresql+psycopg://` so they work out of the box.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


database_url = _normalize_db_url(settings.database_url)

# SQLite needs check_same_thread=False for use across FastAPI's threadpool.
connect_args = (
    {"check_same_thread": False}
    if database_url.startswith("sqlite")
    else {}
)

engine = create_engine(database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Create tables from SQLModel metadata (used for tests / quick start)."""
    # Import models so they register with SQLModel.metadata.
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
