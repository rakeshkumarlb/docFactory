"""Is an extracted value grounded in the chunk text it came from? (Phase 3.) Deterministic, no LLM.

Identifiers of list items (FR-12, a component name) must appear in the text: the model may not mint them. Other text values are
checked loosely, since a description may be lightly rephrased: a value is grounded when it appears in the text or when most of its
words do. Ungrounded values are reported for a human to review, never silently dropped.
"""
import re

from pydantic import BaseModel

from docfactory.extract.model_shapes import identity_field, is_enum, item_model, nested_model

WORD = re.compile(r"[a-z0-9]+")
MIN_WORD = 3
WORD_SHARE = 0.8
_DASHES = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
                         "‘": "'", "’": "'", "“": '"', "”": '"'})


def normalize(text: str) -> str:
    """Case-folded, dashes and quotes unified, whitespace collapsed."""
    return " ".join(text.translate(_DASHES).casefold().split())


def normal_identity(value: str) -> str:
    """An identifier as compared: normalized, without trailing punctuation ('FR-01.' and 'fr-01' are the same requirement)."""
    return normalize(value).rstrip(".:;,)")


def identity_in_text(value: str, text: str) -> bool:
    return normal_identity(value) in normalize(text)


def grounded(value: str, text: str) -> bool:
    """True when `value` appears in `text`, or at least 80% of its words (3+ characters) do."""
    norm_value, norm_text = normalize(value), normalize(text)
    if norm_value in norm_text:
        return True
    words = [w for w in WORD.findall(norm_value) if len(w) >= MIN_WORD]
    if not words:
        return False
    present = set(WORD.findall(norm_text))
    return sum(w in present for w in words) / len(words) >= WORD_SHARE


def _leaves(model: type[BaseModel], data: dict, path: str):
    """(path, text, is_identity) for every free-text leaf of `data`; enum values and NotApplicable reasons are not text from the document."""
    for name, field in model.model_fields.items():
        if name not in data or is_enum(field.annotation):
            continue
        value, here = data[name], f"{path}{name}"
        items, nested = item_model(field.annotation), nested_model(field.annotation)
        if isinstance(value, str):
            yield here, value, False
        elif isinstance(value, list) and items is not None:
            identity = identity_field(items)
            for index, item in enumerate(value):
                if isinstance(item.get(identity), str):
                    yield f"{here}[{index}].{identity}", item[identity], True
                yield from _leaves(items, {k: v for k, v in item.items() if k != identity}, f"{here}[{index}].")
        elif isinstance(value, list):
            yield from ((f"{here}[{i}]", v, False) for i, v in enumerate(value) if isinstance(v, str))
        elif isinstance(value, dict) and nested is not None and "reason" not in value:
            yield from _leaves(nested, value, f"{here}.")


def unknown_identities(model: type[BaseModel], data: dict, text: str) -> list[str]:
    """Item identifiers in `data` that do not appear in `text`, as 'path: value'."""
    return [f"{path}: {value!r}" for path, value, is_identity in _leaves(model, data, "") if is_identity and not identity_in_text(value, text)]


def ungrounded_values(model: type[BaseModel], data: dict, text: str) -> list[str]:
    """Free-text values in `data` (identifiers excluded) that are not grounded in `text`, as 'path: value'."""
    return [f"{path}: {value!r}" for path, value, is_identity in _leaves(model, data, "") if not is_identity and not grounded(value, text)]
