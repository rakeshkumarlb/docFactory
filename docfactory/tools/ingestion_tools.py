"""The ingestion tool package: thin typed wrappers over docfactory.ingest, one operation per tool, nothing else."""
from typing import Annotated

from pydantic import Field

from docfactory.ingest import ingest_operations as ops
from docfactory.models.compare_result import CompareResult
from docfactory.models.defer_result import DeferResult
from docfactory.models.file_info import FileInfo
from docfactory.models.store_result import StoreResult
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

INGESTION_PACKAGE_NAME = "ingestion"
INGESTION_TOOL_NAMES = [
    "list_incoming", "read_incoming_text", "search_docstore", "compare_with_docstore", "store_file", "defer_file",
]

IncomingPath = Annotated[str, Field(description="Path of a file in incoming/, relative with forward slashes, e.g. 'ReadmeForge SRS v0.3.pdf'.")]
TargetPath = Annotated[str, Field(description="Target in DocStore/ as '<scope folder>/<file name>', e.g. 'ReadmeForge/ReadmeForge SRS v0.3.pdf'. Scope is an application name, 'shared' or 'general'. Keep the file's extension.")]


def list_incoming() -> list[FileInfo]:
    return ops.list_incoming()


def read_incoming_text(path: IncomingPath) -> str:
    return ops.read_incoming_text(path)


def search_docstore(
    folder: Annotated[str | None, Field(description="Only files at or below this DocStore folder, e.g. 'ReadmeForge'. Omit to search everywhere.")] = None,
    name_contains: Annotated[str | None, Field(description="Case-insensitive text that must appear in the stored path, e.g. 'srs'.")] = None,
) -> list[dict]:
    return ops.search_docstore(folder, name_contains)


def compare_with_docstore(incoming_path: IncomingPath, target_path: TargetPath) -> CompareResult:
    return ops.compare_with_docstore(incoming_path, target_path)


def store_file(incoming_path: IncomingPath, target_path: TargetPath) -> StoreResult:
    return ops.store_file(incoming_path, target_path)


def defer_file(
    path: IncomingPath,
    reason: Annotated[str, Field(min_length=1, description="Why this file cannot be classified confidently, e.g. 'personal notes, no application or standard is identifiable'.")],
) -> DeferResult:
    return ops.defer_file(path, reason)


_DESCRIPTIONS = {
    "list_incoming": "List the files waiting in incoming/ with size and SHA-256. Start here.",
    "read_incoming_text": "Read the text of one incoming file (PDF, Word, HTML and others are converted to text). Use it to decide what the file is and which scope it belongs to.",
    "search_docstore": "Find files already in DocStore by folder and/or name text. Read-only. Use it to reuse existing scope folder names and to find an existing version of the file.",
    "compare_with_docstore": "Check an incoming file against a DocStore target path: NEW (no such file), SAME (identical bytes, storing is a no-op) or CHANGED (different bytes, storing replaces it and bumps the version). Read-only; call it before store_file.",
    "store_file": "Move an incoming file into DocStore at '<scope>/<file name>' (creates folders, replaces a changed file in place, writes the text sidecar and tracking rows). Only call it when confident of the scope.",
    "defer_file": "Leave a file in incoming/ with a reason because you cannot classify it confidently; a human decides.",
}


def build_ingestion_registry() -> ToolRegistry:
    """A registry holding the ingestion tools."""
    registry = ToolRegistry()
    functions = [list_incoming, read_incoming_text, search_docstore, compare_with_docstore, store_file, defer_file]
    for func in functions:
        registry.register(Tool(func, _DESCRIPTIONS[func.__name__]))
    return registry


def ingestion_package() -> ToolPackage:
    """The only tools the ingestion agent may call."""
    return ToolPackage(INGESTION_PACKAGE_NAME, build_ingestion_registry(), INGESTION_TOOL_NAMES)
