"""The generic tool layer: Tool (schema from the typed signature, feedback instead of exceptions), ToolRegistry and ToolPackage."""
from typing import Annotated

import pytest
from pydantic import Field

from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry


def store(target_path: Annotated[str, Field(description="Where to put it: '<scope folder>/<file name>'.")],
          note: Annotated[str | None, Field(description="Optional note.")] = None) -> dict:
    if not target_path.count("/") == 1:
        raise ValueError("target_path must be '<scope folder>/<file name>'")
    return {"ok": True, "target_path": target_path}


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
    schema = Tool(store, "Store a file.").input_schema()
    assert schema["required"] == ["target_path"]
    assert "scope folder" in schema["properties"]["target_path"]["description"]
    assert Tool(lambda: 1, "none", name="n").input_schema()["properties"] == {}


def test_tool_call_returns_feedback_instead_of_raising():
    tool = Tool(store, "Store a file.")
    assert tool.call({})["ok"] is False  # missing argument
    assert tool.call({"target_path": "no-folder"}) == {"ok": False, "error": "target_path must be '<scope folder>/<file name>'"}
    assert tool.call({"target_path": "a/x.txt"}) == {"ok": True, "target_path": "a/x.txt"}


def test_annotated_defaults_are_optional():
    def f(a: Annotated[int, Field(description="a")], b: Annotated[int, Field(description="b")] = 2) -> int:
        return a + b

    tool = Tool(f, "adds")
    assert tool.call({"a": 1}) == 3 and tool.call({"a": 1, "b": 5}) == 6
    assert tool.input_schema()["required"] == ["a"]
