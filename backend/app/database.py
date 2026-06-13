import os

from sqlalchemy import create_engine, event, text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./harness.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_wal_mode(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401 — import to register models
    Base.metadata.create_all(bind=engine)

    inspector = sa_inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("tools")]
    if "built_in" not in cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE tools ADD COLUMN built_in INTEGER NOT NULL DEFAULT 0"))
            conn.commit()

    from app.seed import seed_tools
    session = SessionLocal()
    try:
        seed_tools(session)
    finally:
        session.close()
