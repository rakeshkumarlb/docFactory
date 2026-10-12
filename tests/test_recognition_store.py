"""RecognitionStore: one recognition concept per original, round trip, tamper check, listing, removal."""
import pytest

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.paths import bundle_root, recognition_relpath
from docfactory.bundle.recognition_store import RecognitionStore
from docfactory.bundle.bundle_store import BundleStore
from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.window_recognition import WindowRecognition

RES = "App/references/arch.pdf"
WINDOW = WindowRecognition(window_hash="1" * 64, chunk_nos=[1, 2], entities=[RecognizedEntity(name="Matching Engine", type="Component", chunks=[1])])


def test_the_path():
    assert recognition_relpath(RES) == "App/recognition/arch.pdf.md"
    with pytest.raises(ValueError):
        recognition_relpath("App/arch.pdf")


def test_round_trip_listing_and_log(tmp_bundle):
    store = RecognitionStore()
    saved = store.save(RES, [WINDOW], "t/1", "2026-10-12T10:00:00Z")
    assert store.get(RES) == saved
    assert store.list("App") == [saved] and store.list() == [saved] and store.list("Other") == []
    text = (bundle_root() / recognition_relpath(RES)).read_text(encoding="utf-8")
    assert text.startswith('---\ntype: "Recognition"') and "# Value" in text
    store.save(RES, [WINDOW], "t/1", "2026-10-12T11:00:00Z")  # same windows: no new log line
    assert (bundle_root() / "log.md").read_text(encoding="utf-8").count("recognition of") == 1


def test_a_recognition_is_not_a_fact(tmp_bundle):
    RecognitionStore().save(RES, [WINDOW], "t/1", "2026-10-12T10:00:00Z")
    assert BundleStore().list_facts() == []


def test_an_edited_file_is_refused(tmp_bundle):
    RecognitionStore().save(RES, [WINDOW], "t/1", "2026-10-12T10:00:00Z")
    path = bundle_root() / recognition_relpath(RES)
    path.write_text(path.read_text(encoding="utf-8").replace("Matching Engine", "Billing"), encoding="utf-8")
    with pytest.raises(BundleError, match="edited outside the system"):
        RecognitionStore().get(RES)


def test_remove(tmp_bundle):
    store = RecognitionStore()
    store.save(RES, [WINDOW], "t/1", "2026-10-12T10:00:00Z")
    store.remove(RES)
    assert store.get(RES) is None
    store.remove(RES)  # nothing left: no error
