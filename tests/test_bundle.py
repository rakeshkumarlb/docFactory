"""Bundle paths and the bundle file writer."""
import pytest

from docfactory import bundle


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv(bundle.ENV_VAR, str(tmp_path / "bundles"))
    return tmp_path / "bundles"


@pytest.mark.parametrize("key,path", [
    ("ReadmeForge.ApplicationOverview", "bundles/ReadmeForge/ApplicationOverview.md"),
    ("Shared.Kpis", "bundles/Shared/Kpis.md"),
    ("ReadmeForge.Components.api server.Architecture", "bundles/ReadmeForge/Components/api server/Architecture.md"),
])
def test_file_path_follows_the_key(key, path):
    assert bundle.file_path_of(key) == path


@pytest.mark.parametrize("key", [
    "ReadmeForge.Components.a/b.Architecture", "ReadmeForge.Components.a\\b.Architecture", "ReadmeForge..Architecture",
    "ReadmeForge.Components. api.Architecture", "ReadmeForge.Components.c:d.Architecture", "ReadmeForge.Components.con.Architecture",
    "ReadmeForge.Components.x?.Architecture", "ReadmeForge.Components.\x00.Architecture",
])
def test_unsafe_key_segments_are_refused(key):
    with pytest.raises(ValueError, match="cannot be used as a file name"):
        bundle.file_path_of(key)


def test_default_root_is_bundles_under_the_project(monkeypatch):
    monkeypatch.delenv(bundle.ENV_VAR, raising=False)
    assert bundle.bundles_root() == bundle.PROJECT_ROOT / "bundles"


def test_file_text_is_frontmatter_blank_line_body():
    assert bundle.file_text("type: X\n", "# T\n") == "---\ntype: X\n---\n\n# T\n"


def test_write_creates_folders_and_is_a_no_op_when_content_is_there(root):
    assert bundle.write_file("bundles/A/B/C.md", "text\n") is True
    target = root / "A" / "B" / "C.md"
    assert target.read_bytes() == b"text\n"  # LF bytes, whatever the platform
    stamp = target.stat().st_mtime_ns
    assert bundle.write_file("bundles/A/B/C.md", "text\n") is False and target.stat().st_mtime_ns == stamp
    assert bundle.write_file("bundles/A/B/C.md", "changed\n") is True and target.read_text(encoding="utf-8") == "changed\n"


def test_write_refuses_to_leave_the_bundle_folder(root):
    with pytest.raises(ValueError, match="outside the bundle folder"):
        bundle.write_file("bundles/../escape.md", "x")
    assert not (root.parent / "escape.md").exists()
