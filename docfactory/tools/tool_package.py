from typing import Any

from docfactory.tools.tool import Tool
from docfactory.tools.tool_registry import ToolRegistry


class ToolPackage:
    """A named, fixed list of registry tools for exactly one agent (least privilege). The agent can reach nothing outside it."""

    def __init__(self, name: str, registry: ToolRegistry, tool_names: list[str]) -> None:
        if len(set(tool_names)) != len(tool_names):
            raise ValueError(f"package {name}: duplicate tool names")
        missing = [n for n in tool_names if n not in registry.names()]
        if missing:
            raise ValueError(f"package {name}: tools not in the registry: {missing}")
        self.name = name
        self._tools = {n: registry.get(n) for n in tool_names}

    def tool_names(self) -> list[str]:
        """The package's tool names in their declared order."""
        return list(self._tools)

    def tools(self) -> list[Tool]:
        """The package's tools in their declared order."""
        return list(self._tools.values())

    def call(self, name: str, arguments: dict) -> Any:
        """Run a tool of this package. A tool outside the package is refused with PermissionError."""
        if name not in self._tools:
            raise PermissionError(f"tool {name!r} is not in the {self.name} package; available: {self.tool_names()}")
        return self._tools[name].call(arguments)
