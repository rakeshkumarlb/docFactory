import shutil
from pathlib import Path

import pytest

from docfactory import db
from docfactory.ingest import ingest_operations as ops
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV, resolve_within
from docfactory.models.file_action import FileAction

CORPUS = Path(__file__).parent / "corpus"
SRS = "ReadmeForge SRS v0.3.pdf"


@pytest.fixture
def dirs(tmp_db, tmp_path, monkeypatch):
    incoming, store = tmp_path / "incoming", tmp_path / "DocStore"
    incoming.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(incoming))
    monkeypatch.setenv(DOCSTORE_ENV, str(store))
    return incoming, store


def _drop(incoming, name, source=None):
    shutil.copyfile(source or CORPUS / "incoming" / name, incoming / name)


def test_every_corpus_file_converts_to_text(dirs):
    incoming, _ = dirs
    for source in (CORPUS / "incoming").iterdir():
        _drop(incoming, source.name)
        assert ops.read_incoming_text(source.name).strip(), source.name


def test_list_incoming_reports_hash_and_size(dirs):
    incoming, _ = dirs
    _drop(incoming, "notes.txt")
    [info] = ops.list_incoming()
    assert info.path == "notes.txt" and info.size_bytes > 0 and len(info.hashcode) == 64


def test_compare_new_same_changed_and_writes_nothing(dirs):
    incoming, store = dirs
    _drop(incoming, SRS)
    target = "ReadmeForge/" + SRS
    assert ops.compare_with_docstore(SRS, target).action == FileAction.NEW
    assert not store.exists() and db.list_docstore_rows() == []
    assert ops.store_file(SRS, target).action == FileAction.NEW

    _drop(incoming, SRS)
    same = ops.compare_with_docstore(SRS, target)
    assert (same.action, same.stored_version) == (FileAction.SAME, 1)
    _drop(incoming, SRS, CORPUS / "revisions" / SRS)
    changed = ops.compare_with_docstore(SRS, target)
    assert (changed.action, changed.stored_version) == (FileAction.CHANGED, 1)
    assert db.get_docstore_row(target)["Version"] == 1  # compare did not write


def test_store_moves_file_writes_sidecar_and_row(dirs):
    incoming, store = dirs
    _drop(incoming, SRS)
    result = ops.store_file(SRS, "ReadmeForge/" + SRS, clock=lambda: "T1")
    assert result.ok and result.version == 1
    assert not (incoming / SRS).exists()
    assert (store / "ReadmeForge" / SRS).is_file()
    assert result.sidecar_path == "ReadmeForge/" + SRS + ".md"
    assert "Requirements" in (store / result.sidecar_path).read_text(encoding="utf-8")
    assert db.get_docstore_row("ReadmeForge/" + SRS)["Timestamp"] == "T1"


def test_store_same_is_noop_and_removes_duplicate(dirs):
    incoming, _ = dirs
    _drop(incoming, SRS)
    ops.store_file(SRS, "ReadmeForge/" + SRS, clock=lambda: "T1")
    _drop(incoming, SRS)
    result = ops.store_file(SRS, "ReadmeForge/" + SRS, clock=lambda: "T2")
    assert (result.ok, result.action, result.version) == (True, FileAction.SAME, 1)
    assert not (incoming / SRS).exists()
    assert db.get_docstore_row("ReadmeForge/" + SRS)["Timestamp"] == "T1"


def test_store_changed_replaces_bumps_version_regenerates_sidecar(dirs):
    incoming, store = dirs
    target = "ReadmeForge/" + SRS
    _drop(incoming, SRS)
    ops.store_file(SRS, target, clock=lambda: "T1")
    _drop(incoming, SRS, CORPUS / "revisions" / SRS)
    result = ops.store_file(SRS, target, clock=lambda: "T2")
    assert (result.action, result.version) == (FileAction.CHANGED, 2)
    assert "pause automatic scanning" in (store / (target + ".md")).read_text(encoding="utf-8")
    assert [h["Version"] for h in db.list_docstore_history(target)] == [2]


def test_text_file_has_no_sidecar(dirs):
    incoming, store = dirs
    _drop(incoming, "notes.txt")
    result = ops.store_file("notes.txt", "general/notes.txt")
    assert result.ok and result.sidecar_path is None
    assert [p.name for p in (store / "general").iterdir()] == ["notes.txt"]


def test_store_rejects_bad_calls_and_changes_nothing(dirs):
    incoming, store = dirs
    _drop(incoming, "notes.txt")
    for incoming_path, target in [("../x.txt", "a/x.txt"), ("notes.txt", "../escape/notes.txt"), ("missing.txt", "a/missing.txt"),
                                  ("notes.txt", "notes.txt"), ("notes.txt", "a/notes.pdf")]:
        result = ops.store_file(incoming_path, target)
        assert not result.ok and result.error, (incoming_path, target)
    assert (incoming / "notes.txt").is_file() and not store.exists() and db.list_docstore_rows() == []


def test_conversion_failure_changes_nothing(dirs, monkeypatch):
    incoming, store = dirs
    (incoming / "broken.pdf").write_bytes(b"not a pdf at all")

    def boom(path):
        raise RuntimeError("unsupported")

    monkeypatch.setattr(ops, "file_text", boom)
    result = ops.store_file("broken.pdf", "a/broken.pdf")
    assert not result.ok and "convert" in result.error
    assert (incoming / "broken.pdf").is_file() and db.list_docstore_rows() == []


def test_search_docstore(dirs):
    incoming, _ = dirs
    _drop(incoming, SRS)
    ops.store_file(SRS, "ReadmeForge/" + SRS)
    assert [r["FullPath"] for r in ops.search_docstore(folder="ReadmeForge")] == ["ReadmeForge/" + SRS]
    assert ops.search_docstore(name_contains="nothing") == []


def test_defer_leaves_file_and_requires_reason(dirs):
    incoming, _ = dirs
    _drop(incoming, "notes.txt")
    result = ops.defer_file("notes.txt", " unclear what this belongs to ")
    assert result.reason == "unclear what this belongs to" and (incoming / "notes.txt").is_file()
    with pytest.raises(ValueError):
        ops.defer_file("notes.txt", "  ")


def test_resolve_within_blocks_escapes(tmp_path):
    for bad in ["", "/abs", "..", "a/../../b", "C:/x" if Path("C:/x").is_absolute() else "/x"]:
        with pytest.raises(ValueError):
            resolve_within(tmp_path, bad)
    assert resolve_within(tmp_path, "a/b.txt") == (tmp_path / "a" / "b.txt").resolve()


def test_target_rules_reject_sloppy_targets_with_feedback(dirs):
    incoming, store = dirs
    _drop(incoming, SRS)
    for target in ["ReadmeExists?", "Readt...", "ReadmeForge/Other name.pdf", "a/b/" + SRS, "bad scope/" + SRS, "ReadmeForge/", "/" + SRS]:
        result = ops.store_file(SRS, target)
        assert not result.ok and result.error, target
        with pytest.raises(ValueError):
            ops.compare_with_docstore(SRS, target)
    assert (incoming / SRS).is_file() and not store.exists() and db.list_docstore_rows() == []
    assert "stay exactly" in ops.store_file(SRS, "ReadmeForge/renamed.pdf").error
