"""Naming rules and target resolution: class name -> folder, module, file, test file."""
import ast
import re

import conventions as C


def to_snake(name: str) -> str:
    """`ApplicationOverview` -> `application_overview`, `HTTPServer` -> `http_server`."""
    step = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    return step.lower()


def is_pascal(name: str) -> bool:
    return re.fullmatch(r"[A-Z][A-Za-z0-9]*", name) is not None


def rel(path) -> str:
    return path.relative_to(C.ROOT).as_posix()


def package_files(folders=C.ALL_FOLDERS):
    for folder in folders:
        directory = C.ROOT / C.PACKAGE / folder
        if directory.is_dir():
            yield from sorted(p for p in directory.glob("*.py") if p.name != "__init__.py")


def find_class(class_name: str, folders=C.ALL_FOLDERS) -> list:
    """Every file under the package folders that defines a class with this name."""
    found = []
    for path in package_files(folders):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        if any(isinstance(n, ast.ClassDef) and n.name == class_name for n in ast.walk(tree)):
            found.append(path)
    return found


def resolve(kind: str, class_name: str) -> dict:
    """Where the files for a model class go: folder, module, file and test file, plus any errors."""
    if kind not in C.KINDS:
        return {"errors": [f"unknown kind {kind!r}; expected one of {sorted(C.KINDS)}"]}
    errors = []
    if not is_pascal(class_name):
        errors.append(f"{class_name!r} is not PascalCase (letters and digits, starts with a capital)")
    stem = to_snake(class_name)
    folder = C.KINDS[kind]["folder"]
    path = C.ROOT / C.PACKAGE / folder / f"{stem}.py"
    if class_name.endswith("Saver"):
        errors.append("a model class name must not end with 'Saver'")
    if class_name in C.BOOTSTRAP_CLASSES:
        errors.append(f"{class_name} is a bootstrap class: write it by hand (see the create-shared-model skill)")
    others = [rel(p) for p in find_class(class_name) if p != path]
    if others:
        errors.append(f"class {class_name} is already defined in {others}")
    return {
        "kind": kind,
        "class": class_name,
        "folder": f"{C.PACKAGE}/{folder}",
        "module": f"{C.PACKAGE}.{folder}.{stem}",
        "file": rel(path),
        "test_file": f"tests/test_{stem}.py",
        "exists": path.exists(),
        "errors": errors,
    }


def saver_target(kind: str, model_class: str, model_module: str) -> dict:
    """Where the saver for a model goes. `kind` is the MODEL kind (entity-model or document-model)."""
    stem = to_snake(model_class)
    folder = C.SAVERS[kind]["folder"]
    path = C.ROOT / C.PACKAGE / folder / f"{stem}_saver.py"
    return {
        "kind": kind,
        "model_class": model_class,
        "model_module": model_module,
        "saver_class": f"{model_class}Saver",
        "saver_module": f"{C.PACKAGE}.{folder}.{stem}_saver",
        "folder": f"{C.PACKAGE}/{folder}",
        "file": rel(path),
        "test_file": f"tests/test_{stem}_saver.py",
        "exists": path.exists(),
    }


SEGMENT = re.compile(r"[A-Za-z][A-Za-z0-9]*|\{(app|component|doctype)\}")


def pattern_problems(kind: str, pattern: str) -> list:
    """Rules for a key pattern. `kind` is the MODEL kind."""
    segments = pattern.split(".")
    problems = [f"pattern {pattern!r}: bad segment {s!r}" for s in segments if not SEGMENT.fullmatch(s)]
    if len(segments) < 2:
        problems.append(f"pattern {pattern!r}: needs at least <scope>.<name>")
    elif kind == "entity-model" and segments[0] not in ("{app}", "Shared"):
        problems.append(f"pattern {pattern!r}: entity keys start with {{app}} or Shared")
    elif kind == "document-model" and (segments[0] != "{app}" or len(segments) < 3 or segments[1] != "Outputs"):
        problems.append(f"pattern {pattern!r}: document keys look like {{app}}.Outputs.<...>")
    return problems


def sample_key(pattern: str) -> str:
    """A concrete key for a pattern, used by generated tests: {app} -> TestApp, ..."""
    return ".".join(C.SAMPLE_SEGMENTS.get(segment, segment) for segment in pattern.split("."))


def pattern_regex(pattern: str) -> re.Pattern:
    """Key pattern such as `{app}.Components.{component}.Architecture` -> compiled regex."""
    parts = []
    for segment in pattern.split("."):
        parts.append(r"[^.]+" if re.fullmatch(r"\{[a-z]+\}", segment) else re.escape(segment))
    return re.compile(r"\.".join(parts))


def key_matches(pattern: str, key: str) -> bool:
    return pattern_regex(pattern).fullmatch(key) is not None


def app_id_of(key: str):
    """`Shared.*` has no application; every other key's AppID is its first segment."""
    first = key.split(".")[0]
    return None if first == "Shared" else first
