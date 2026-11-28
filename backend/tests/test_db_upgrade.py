"""An older database keeps working after an update: new columns are added, nothing is lost."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.db import init_db


def test_old_database_gets_new_columns_and_keeps_its_data():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:  # the tables as they were before knowledge tracing
        conn.execute(text("CREATE TABLE section (id INTEGER PRIMARY KEY, document_id INTEGER, position INTEGER, "
                          "number VARCHAR, title VARCHAR, paragraphs_json VARCHAR)"))
        conn.execute(text("INSERT INTO section VALUES (1, 1, 0, '1', 'Μέση τιμή', '[\"κείμενο\"]')"))
    added = init_db(engine)
    assert ("section", "concepts_json") in added
    with engine.connect() as conn:
        row = conn.execute(text("SELECT title, concepts_json FROM section")).one()
    assert row == ("Μέση τιμή", "[]")
    assert "conceptmastery" in inspect(engine).get_table_names()
    assert init_db(engine) == []  # running again changes nothing
