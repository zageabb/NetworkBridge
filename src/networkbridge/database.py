"""Shared, additive database initialisation independent of collection settings."""

from contextlib import closing
from pathlib import Path

from networkbridge.aliases import ensure_schema as ensure_alias_schema
from networkbridge.devices import ensure_device_schema
from networkbridge.monitor_history import ensure_schema as ensure_monitor_schema
from networkbridge.observations import ensure_schema as ensure_observation_schema
from networkbridge.storage import connect


def database_path(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix) or not url[len(prefix):]:
        raise ValueError("A non-empty SQLite database path is required")
    return Path(url[len(prefix):])


def initialize_database(url: str) -> None:
    path = database_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        ensure_device_schema(db)
        ensure_observation_schema(db)
        ensure_alias_schema(db)
        ensure_monitor_schema(db)
