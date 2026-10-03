"""Shared fixtures. Every test that touches the database uses `tmp_db`."""
import pytest

from docfactory import bundle, db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """A fresh temporary database file, selected through DOCFACTORY_DB and initialised."""
    path = tmp_path / "test.sqlite"
    monkeypatch.setenv(db.ENV_VAR, str(path))
    monkeypatch.setenv(bundle.ENV_VAR, str(tmp_path / "bundles"))  # a saved fact also writes its OKF file: never into the repo
    db.connect().close()
    return path
