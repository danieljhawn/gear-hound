from sqlalchemy import text

from app.db import create_database_engine


def test_sqlite_engine_enforces_foreign_keys() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    with engine.connect() as connection:
        enabled = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert enabled == 1
