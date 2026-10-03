from docfactory.tools.tool import Tool


class ToolRegistry:
    """In-process registry holding every function tool by name. It only stores and looks up; packages decide who may call what."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Add a tool. A second tool with the same name is an error."""
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """The tool called `name`; raises KeyError when unknown."""
        return self._tools[name]

    def names(self) -> list[str]:
        """All registered tool names, sorted."""
        return sorted(self._tools)
