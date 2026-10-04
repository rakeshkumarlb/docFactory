"""Slim JSON schemas for tool arguments: references inlined (a schema embedded in a tool argument has no $defs) and keys that only cost tokens dropped."""

# Schema keys that only add tokens: bookkeeping metadata of our fields and generic Pydantic output. The model sees the rest.
_NOISE_KEYS = {"$defs", "binding", "render_as", "scored", "title", "additionalProperties", "question"}  # a rejected save returns the question as feedback


def inline_refs(schema, defs: dict):
    """The JSON schema with every $ref replaced by its definition (a schema embedded in a tool argument has no dangling references),
    minus the keys that only cost tokens. `na_allowed` is kept only where it is true, empty defaults are dropped."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            return inline_refs(defs[schema["$ref"].rsplit("/", 1)[-1]], defs)
        slim = {n: v for n, v in schema.items() if n not in _NOISE_KEYS and not (n == "na_allowed" and v is False) and not (n == "default" and v in ("", [], None))}
        properties = slim.get("properties")
        if isinstance(properties, dict):  # a field called 'title' or 'scored' is data, not noise: only the schema's own keys are dropped
            slim["properties"] = {n: inline_refs(v, defs) for n, v in properties.items()}
            slim = {n: (inline_refs(v, defs) if n != "properties" else v) for n, v in slim.items()}
            return slim
        return {n: inline_refs(v, defs) for n, v in slim.items()}
    if isinstance(schema, list):
        return [inline_refs(item, defs) for item in schema]
    return schema
