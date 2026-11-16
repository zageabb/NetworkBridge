import pytest

from networkbridge.worker import database_path


def test_database_path():
    assert str(database_path("sqlite:////var/lib/networkbridge/history.db")) == (
        "/var/lib/networkbridge/history.db"
    )


def test_non_sqlite_rejected():
    with pytest.raises(ValueError):
        database_path("postgresql://localhost/networkbridge")
