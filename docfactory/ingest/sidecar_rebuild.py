"""Regenerates the text sidecars of everything in DocStore from the stored originals: `python -m docfactory.ingest.sidecar_rebuild`.

Use it after the converters improve. A re-ingested identical file is a no-op (same hash), so sidecars are not rebuilt by ingestion.
The originals and the DocStore rows are never touched; the sidecars are views.
"""
from docfactory import db
from docfactory.ingest.paths import docstore_dir, resolve_within
from docfactory.ingest.text_extraction import file_text, is_text_file, sidecar_path


def rebuild_sidecars() -> dict[str, str]:
    """Rebuild every sidecar. Returns {DocStore path: 'rebuilt' | 'skipped: <why>'} for each non-text file in the DocStore table."""
    results: dict[str, str] = {}
    for row in db.list_docstore_rows():
        relative = row["FullPath"]
        original = resolve_within(docstore_dir(), relative)
        if is_text_file(original):
            continue
        if not original.is_file():
            results[relative] = "skipped: original is missing from DocStore"
            continue
        try:
            text = file_text(original)
        except Exception as exc:  # report and carry on with the other files
            results[relative] = f"skipped: could not convert ({exc})"
            continue
        sidecar_path(original).write_text(text, encoding="utf-8")
        results[relative] = "rebuilt"
    return results


def main() -> None:
    for path, outcome in rebuild_sidecars().items():
        print(f"{path}: {outcome}")


if __name__ == "__main__":
    main()
