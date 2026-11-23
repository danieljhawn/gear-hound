from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_upgrades_and_downgrades(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "alembic_version",
        "listings",
        "listing_observations",
        "listing_states",
        "owned_gear",
        "trade_details",
    } <= tables

    command.downgrade(config, "base")

    remaining_tables = set(inspect(engine).get_table_names())
    assert remaining_tables == {"alembic_version"}
