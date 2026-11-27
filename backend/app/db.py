import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")  # CONTENT_PROVIDER, ANTHROPIC_API_KEY, ... (never committed)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'studybuddy.db'}")
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BACKEND_DIR / "storage"))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db(bind=engine) -> None:
    from app import models  # noqa: F401  (registers tables)

    SQLModel.metadata.create_all(bind)


def get_session():
    with Session(engine) as session:
        yield session
