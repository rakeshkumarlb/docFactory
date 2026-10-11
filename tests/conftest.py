"""Shared fixtures. Every test that touches the bundle or the generated documents uses `tmp_bundle`."""
import pytest

from docfactory.bundle import paths as bundle_paths


@pytest.fixture
def tmp_bundle(tmp_path, monkeypatch):
    """A fresh temporary workspace: the OKF bundle (DOCFACTORY_BUNDLE) and the output folder (DOCFACTORY_OUTPUT) are empty folders under tmp_path."""
    monkeypatch.setenv(bundle_paths.ENV_VAR, str(tmp_path / "bundle"))  # facts, sources and contributions are files: never into the repo
    monkeypatch.setenv("DOCFACTORY_OUTPUT", str(tmp_path / "output"))  # generated documents and their state files: never into the repo
    return tmp_path
