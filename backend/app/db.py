import os

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./studybuddy.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db(bind=engine) -> None:
    from app import models  # noqa: F401  (registers tables)

    SQLModel.metadata.create_all(bind)


def get_session():
    with Session(engine) as session:
        yield session
