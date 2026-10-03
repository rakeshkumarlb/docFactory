import re

SCOPE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def check_target(incoming_path: str, target_path: str) -> str | None:
    """Why `target_path` is not a valid DocStore target for `incoming_path`, or None when it is.

    A target is '<scope folder>/<file name>': exactly one folder made of letters, digits, '.', '_' or '-', and the file name is the
    original's name unchanged (identity = folder + file name, so renaming would break replace-in-place).
    """
    parts = target_path.split("/")
    if len(parts) != 2 or not all(parts):
        return "target_path must be exactly '<scope folder>/<file name>', e.g. ReadmeForge/SRS.pdf"
    scope, name = parts
    if not SCOPE_PATTERN.match(scope):
        return f"scope folder {scope!r} is not valid: use letters, digits, '.', '_' or '-' only (an application name, 'shared' or 'general')"
    original = incoming_path.rsplit("/", 1)[-1]
    if name != original:
        return f"the file name must stay exactly {original!r} (got {name!r}); use the name as listed by list_incoming"
    return None
