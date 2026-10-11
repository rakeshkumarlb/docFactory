"""Checks a fact key before anything is written: it must match an entity's key pattern and be usable as a path."""
from docfactory.bundle.fact_registry import FACT_SPECS, entity_of_key, key_patterns_of
from docfactory.bundle.paths import fact_relpath
from docfactory.models.save_error import SaveError
from docfactory.validation_errors import json_text

KEY_DESCRIPTION = "The unique key of the fact: <Scope>.<Name>, where Scope is an application name or Shared."


def check_key(key) -> tuple[str | None, list[SaveError]]:
    """(entity name, errors). Any error means the save is rejected."""
    entity = entity_of_key(key)
    if entity is None:
        known = ", ".join(pattern for name in FACT_SPECS for pattern in key_patterns_of(name))
        return None, [SaveError(
            path="key",
            message=f"Key {key!r} does not match the key pattern of any fact",
            error_type="key_pattern_mismatch",
            received=json_text(key),
            expected=f"one of: {known}",
            field_description=KEY_DESCRIPTION,
            question="Which key should this fact be saved under? Its last segment is the entity name.",
        )]
    try:
        fact_relpath(key)
    except ValueError as error:
        return None, [SaveError(
            path="key",
            message=str(error),
            error_type="key_unsafe_path",
            received=json_text(key),
            expected="key segments that are legal file names: no slash, backslash, colon, asterisk, question mark, double quote, angle bracket or pipe, no leading or trailing spaces",
            field_description=KEY_DESCRIPTION,
            question="Which key should this fact be saved under? Every segment becomes a folder or file name in the bundle.",
        )]
    return entity, []
