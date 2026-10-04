"""Typed access to FactContributions: what each DocStore file contributed to a knowledge fact (Phase 3).

A fact extracted from documents is the merge of its contributions, so re-extracting one file replaces only that file's row.
Contributions are derived extraction data, written only by the extraction pipeline; KnowledgeFacts stays the source of truth.
"""
from docfactory import db
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.fact_contribution import FactContribution

EXISTING = "(existing)"  # the resource of a fact value stored before any extraction (e.g. seed data): lowest precedence


def _record(row: dict) -> FactContribution:
    return FactContribution(fact_key=row["FactKey"], resource=row["Resource"], value_json=row["Value"], hashcode=row["Hashcode"],
                            chunks_hash=row["ChunksHash"], description=row["Description"], generated_by=row["GeneratedBy"],
                            timestamp=row["Timestamp"])


def get_contribution(key: str, resource: str) -> FactContribution | None:
    row = db.get_contribution(key, resource)
    return _record(row) if row else None


def list_contributions(key: str | None = None, resource: str | None = None) -> list[FactContribution]:
    return [_record(row) for row in db.list_contributions(key, resource)]


def save_contribution(key: str, resource: str, value: dict, chunks_hash: str | None, description: str | None,
                      generated_by: str, timestamp: str) -> FactContribution:
    """Store `value` (the partial fact this file states) as the contribution of `resource` to `key` and return it."""
    text = canonical_json(value)
    db.write_contribution(key, resource, text, sha256_hex(text), chunks_hash, description, generated_by, timestamp)
    return get_contribution(key, resource)


def remove_contribution(key: str, resource: str) -> None:
    db.delete_contribution(key, resource)
