"""How a document binding finds its fact: the fact registry, the key a binding reads, the stored fact and the "answered" rule.

A binding `<Fact>.<field>` of a document template names the fact (FACT_SPECS), `fact_key` gives its fact key, `load_fact`
reads it and `is_answered` applies the same rule as `completeness.py`. Nothing here invents a value: an absent fact or an
unanswered field is a gap for the caller to report.
"""
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.models.not_applicable import NotApplicable


class BuildError(Exception):
    """Raised when a binding names a fact that FACT_SPECS does not know (a wrongly wired template)."""


def fact_key(app_id: str, fact_name: str) -> str:
    """The fact key a binding's fact name reads: Shared.<Fact> for shared facts, else <App>.<Fact>."""
    spec = FACT_SPECS.get(fact_name)
    if spec is None:
        raise BuildError(f"cannot load fact {fact_name!r}; add it to FACT_SPECS")
    return f"Shared.{fact_name}" if spec["shared"] else f"{app_id}.{fact_name}"


def load_fact(app_id: str, fact_name: str, cache: dict):
    """The stored fact object for `fact_name`, or None when its file does not exist (BundleError when the file cannot be trusted). Cached in `cache` (one dict per caller run)."""
    if fact_name not in cache:
        record = BundleStore().read_fact(fact_key(app_id, fact_name))
        cache[fact_name] = FACT_SPECS[fact_name]["model"].model_validate_json(record.value) if record else None
    return cache[fact_name]


def is_answered(source_field, value) -> bool:
    """A source field is answered when it is mandatory (guaranteed by validation), holds a NotApplicable, or differs from its own default."""
    if isinstance(value, NotApplicable) or source_field.is_required():
        return True
    return value != source_field.get_default(call_default_factory=True)
