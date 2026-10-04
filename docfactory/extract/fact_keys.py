"""Which fact key an entity extracted from a DocStore file is saved under (Phase 3). Deterministic, no LLM.

The scope is the first folder of the DocStore path. An application folder gives '<App>.<Entity>'; entities that only accept a
'Shared.' key (Slo, Kpis) are taken only from files in 'shared/', so an application document never overwrites a common standard;
'shared/' gives only those shared keys; 'general/' holds documentation of no single application and gives no fact.
Component keys are not derived here: extraction works at application level.
"""
from docfactory.base_saver import SHARED
from docfactory.ingest.scope_rules import GENERAL
from docfactory.ingest.scope_rules import SHARED as SHARED_FOLDER
from docfactory.saver_resolution import entity_saver_for


def is_shared_entity(entity: str) -> bool:
    """True when the entity's saver accepts only 'Shared.' keys (Slo, Kpis)."""
    saver_class = entity_saver_for(entity)
    return saver_class is not None and all(p.startswith(f"{SHARED}.") for p in saver_class.key_patterns)


def fact_key(docstore_path: str, entity: str) -> tuple[str | None, str]:
    """(fact key, '') or (None, why no fact is extracted for this entity from this file)."""
    saver_class = entity_saver_for(entity)
    if saver_class is None:
        return None, f"no entity saver for {entity!r}"
    parts = docstore_path.replace("\\", "/").strip("/").split("/")
    if len(parts) < 2:
        return None, f"{docstore_path!r} is not inside a scope folder"
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
