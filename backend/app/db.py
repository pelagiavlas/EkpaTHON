import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")  # CONTENT_PROVIDER, ANTHROPIC_API_KEY, ... (never committed)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'studybuddy.db'}")
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BACKEND_DIR / "storage"))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def _sql_default(column) -> str:
    default = column.default.arg if column.default is not None and not callable(column.default.arg) else None
    if default is None:
        return "NULL"
    if isinstance(default, bool):
        return "1" if default else "0"
    if isinstance(default, (int, float)):
        return str(default)
    return "'" + str(default).replace("'", "''") + "'"


def add_missing_columns(bind=engine) -> list[tuple[str, str]]:
    """Keep an older database working after an update: add new columns with their default.
    Nothing is deleted or changed. Returns the (table, column) pairs that were added."""
    existing = inspect(bind)
    added = []
    with bind.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not existing.has_table(table.name):
                continue  # create_all makes new tables
            have = {c["name"] for c in existing.get_columns(table.name)}
            for column in table.columns:
                if column.name in have:
                    continue
                kind = column.type.compile(dialect=bind.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {kind} DEFAULT {_sql_default(column)}'))
                added.append((table.name, column.name))
    return added


def init_db(bind=engine) -> list[tuple[str, str]]:
    from app import models  # noqa: F401  (registers tables)

    SQLModel.metadata.create_all(bind)
    return add_missing_columns(bind)


def get_session():
    with Session(engine) as session:
        yield session
