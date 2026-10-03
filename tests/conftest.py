"""Shared fixtures. Every test that touches the database uses `tmp_db`."""
import pytest

from docfactory import db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """A fresh temporary database file, selected through DOCFACTORY_DB and initialised."""
    path = tmp_path / "test.sqlite"
    monkeypatch.setenv(db.ENV_VAR, str(path))
    db.connect().close()
    return path
