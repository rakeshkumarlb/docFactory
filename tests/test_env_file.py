import os

from docfactory.env_file import load_env_file


def test_loads_values_skips_comments_and_keeps_existing_env(tmp_path, monkeypatch):
    for var in ("TF_A", "TF_B", "TF_C", "TF_D"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("TF_B", "from-shell")
    path = tmp_path / ".env"
    path.write_text('# comment\n\nTF_A=one\nTF_B=from-file\nTF_C="quoted value"\nnot a pair\nTF_D=a=b\n', encoding="utf-8")
    load_env_file(path)
    assert (os.environ["TF_A"], os.environ["TF_B"], os.environ["TF_C"], os.environ["TF_D"]) == ("one", "from-shell", "quoted value", "a=b")
    for var in ("TF_A", "TF_C", "TF_D"):
        monkeypatch.delenv(var)


def test_missing_file_is_fine(tmp_path):
    load_env_file(tmp_path / "nope.env")
