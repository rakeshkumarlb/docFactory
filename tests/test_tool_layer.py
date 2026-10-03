import shutil
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import Field

from docfactory import db
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV
from docfactory.tools.ingestion_tools import INGESTION_TOOL_NAMES, ingestion_package
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

CORPUS = Path(__file__).parent / "corpus" / "incoming"


@pytest.fixture
def dirs(tmp_db, tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(incoming))
    monkeypatch.setenv(DOCSTORE_ENV, str(tmp_path / "DocStore"))
    return incoming


def test_ingestion_package_holds_exactly_the_agreed_tools():
    package = ingestion_package()
    assert package.tool_names() == ["list_incoming", "read_incoming_text", "search_docstore",
                                    "compare_with_docstore", "store_file", "defer_file"]
    assert package.tool_names() == INGESTION_TOOL_NAMES


def test_package_refuses_tools_outside_it():
    registry = ToolRegistry()
    registry.register(Tool(lambda: 1, "one", name="one"))
    registry.register(Tool(lambda: 2, "two", name="two"))
    package = ToolPackage("p", registry, ["one"])
    assert package.call("one", {}) == 1
    with pytest.raises(PermissionError):
        package.call("two", {})
    with pytest.raises(PermissionError):
        package.call("nonexistent", {})


def test_package_rejects_unknown_or_duplicate_names():
    registry = ToolRegistry()
    registry.register(Tool(lambda: 1, "one", name="one"))
    with pytest.raises(ValueError):
        ToolPackage("p", registry, ["missing"])
    with pytest.raises(ValueError):
        ToolPackage("p", registry, ["one", "one"])
    with pytest.raises(ValueError):
        registry.register(Tool(lambda: 1, "dup", name="one"))


def test_schemas_come_from_typed_signatures():
    tools = {t.name: t for t in ingestion_package().tools()}
    schema = tools["store_file"].input_schema()
    assert set(schema["required"]) == {"incoming_path", "target_path"}
    assert "scope folder" in schema["properties"]["target_path"]["description"]
    assert tools["list_incoming"].input_schema()["properties"] == {}
    assert tools["search_docstore"].input_schema().get("required") is None
    assert all(t.description for t in tools.values())


def test_tool_call_returns_feedback_instead_of_raising(dirs):
    package = ingestion_package()
    assert package.call("store_file", {"incoming_path": "x"})["ok"] is False  # missing argument
    assert package.call("store_file", {"incoming_path": "x", "target_path": "a/x.txt", "bogus": 1})["ok"] is False
    assert "no such incoming file" in package.call("read_incoming_text", {"path": "missing.txt"})["error"]
    assert package.call("defer_file", {"path": "x", "reason": ""})["ok"] is False


def test_compare_is_read_only_and_flow_works_through_the_package(dirs):
    incoming = dirs
    shutil.copyfile(CORPUS / "notes.txt", incoming / "notes.txt")
    shutil.copyfile(CORPUS / "readmeforge-runbooks.html", incoming / "runbooks.html")
    package = ingestion_package()
    assert [f["path"] for f in package.call("list_incoming", {})] == ["notes.txt", "runbooks.html"]
    assert "PagerDuty" in package.call("read_incoming_text", {"path": "runbooks.html"})
    compared = package.call("compare_with_docstore", {"incoming_path": "runbooks.html", "target_path": "ReadmeForge/runbooks.html"})
    assert compared["action"] == "NEW" and db.list_docstore_rows() == []
    stored = package.call("store_file", {"incoming_path": "runbooks.html", "target_path": "ReadmeForge/runbooks.html"})
    assert stored["ok"] and stored["action"] == "NEW" and stored["version"] == 1
    assert [r["FullPath"] for r in package.call("search_docstore", {"folder": "ReadmeForge"})] == ["ReadmeForge/runbooks.html"]
    deferred = package.call("defer_file", {"path": "notes.txt", "reason": "personal notes"})
    assert deferred["ok"] and (incoming / "notes.txt").is_file()


def test_annotated_defaults_are_optional():
    def f(a: Annotated[int, Field(description="a")], b: Annotated[int, Field(description="b")] = 2) -> int:
        return a + b

    tool = Tool(f, "adds")
    assert tool.call({"a": 1}) == 3 and tool.call({"a": 1, "b": 5}) == 6
    assert tool.input_schema()["required"] == ["a"]
