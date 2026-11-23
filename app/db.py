from typing import Any

from sqlalchemy import Engine, create_engine, event


def create_database_engine(database_url: str) -> Engine:
    engine = create_engine(database_url)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(
            dbapi_connection: Any, _connection_record: Any
        ) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine
