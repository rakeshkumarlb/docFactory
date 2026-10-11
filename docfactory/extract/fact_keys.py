"""Which fact key an entity extracted from an ingested original is saved under (Phase 3). Deterministic, no LLM.

The scope is the first folder of the original's bundle path. An application folder gives '<App>.<Entity>'; entities that only accept a
'Shared.' key (Slo, Kpis) are taken only from files in 'shared/', so an application document never overwrites a common standard;
'shared/' gives only those shared keys; 'general/' holds documentation of no single application and gives no fact.
Component keys are not derived here: extraction works at application level.
"""
from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.key_patterns import SHARED
from docfactory.ingest.scope_rules import GENERAL
from docfactory.ingest.scope_rules import SHARED as SHARED_FOLDER


def is_shared_entity(entity: str) -> bool:
    """True when the entity accepts only 'Shared.' keys (Slo, Kpis)."""
    return entity in FACT_SPECS and FACT_SPECS[entity]["shared"]


def fact_key(source_path: str, entity: str) -> tuple[str | None, str]:
    """(fact key, '') or (None, why no fact is extracted for this entity from this file)."""
    if entity not in FACT_SPECS:
        return None, f"no fact registered for {entity!r}"
    parts = source_path.replace("\\", "/").strip("/").split("/")
    if len(parts) < 2:
        return None, f"{source_path!r} is not inside a scope folder"
    scope = parts[0]
    shared_entity = is_shared_entity(entity)
    if scope.lower() == GENERAL:
        return None, "files in general/ document no single application and give no facts"
    if scope.lower() == SHARED_FOLDER:
        if not shared_entity:
            return None, f"{entity} is application-specific; a file in shared/ only gives the shared facts (Slo, Kpis)"
        return f"{SHARED}.{entity}", ""
    if shared_entity:
        return None, f"{entity} is a shared fact (Shared.{entity}); it is taken only from files in shared/, not from an application document"
    return f"{scope}.{entity}", ""
