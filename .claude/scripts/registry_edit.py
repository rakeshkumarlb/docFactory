"""Reads and edits the fact registry (docfactory/bundle/fact_registry.py): the list of facts a bundle can hold.

A fact is an entity model in entitymodels/facts/ with an entry in FACT_SPECS. Pure text functions; the caller reads and writes the file.
"""
import ast
import re

IMPORT_PREFIX = "from docfactory.entitymodels.facts."
DICT_START = "FACT_SPECS = {"


def registered(text: str) -> set:
    """The entity names registered in the FACT_SPECS dict of the registry source."""
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FACT_SPECS" for t in node.targets) and isinstance(node.value, ast.Dict):
            return {key.value for key in node.value.keys if isinstance(key, ast.Constant)}
    return set()


def add_entry(text: str, class_name: str, module: str, shared: bool) -> str:
    """The registry source with `class_name` (defined in `module`) imported and added to FACT_SPECS.

    Raises ValueError when it is already registered or the registry has no FACT_SPECS dict to add to.
    """
    if class_name in registered(text):
        raise ValueError(f"{class_name} is already registered in the fact registry")
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith(DICT_START)), None)
    if start is None:
        raise ValueError("the fact registry has no FACT_SPECS dict")
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "}")
    lines.insert(end, f'    "{class_name}": {{"model": {class_name}, "shared": {shared}}},')
    new_import = f"from {module} import {class_name}"
    imports = [i for i, line in enumerate(lines[:start]) if line.startswith(IMPORT_PREFIX)]
    if imports:
        at = next((i for i in imports if lines[i] > new_import), imports[-1] + 1)
    else:
        at = max((i for i, line in enumerate(lines[:start]) if re.match(r"(from|import) ", line)), default=-1) + 1
    lines.insert(at, new_import)
    return "\n".join(lines)
