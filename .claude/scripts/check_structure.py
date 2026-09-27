"""Usage: python .claude/scripts/check_structure.py [paths...] [--no-tests]

Static check of the CLAUDE.md structure rules. No paths = the five package folders plus a scan of the
rest of the package for stray Pydantic classes. Prints `path:line: RULE message`, exit 1 on any finding.

Rules: syntax, one-class, file-name, saver-name, saver-base, saver-body, base-model, field-helper,
forbidden-type, layering, stray-model, class-docstring, test-missing.
"""
import ast
import sys
from pathlib import Path

import conventions as C
import field_spec
import naming


def base_names(cls: ast.ClassDef) -> set:
    names = set()
    for base in cls.bases:
        node = base.value if isinstance(base, ast.Subscript) else base
        names.add(node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", ast.unparse(node)))
    return names


def docstring_of(node):
    return ast.get_docstring(node)


def check_file(path: Path, folder: str, want_tests: bool) -> list:
    rel = naming.rel(path)
    out = []

    def add(line, rule, message):
        out.append((rel, line, rule, message))

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as error:
        return [(rel, error.lineno or 1, "syntax", error.msg)]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    if not classes:
        return [(rel, 1, "one-class", "module defines no class")] if path.stem != C.FIELD_HELPER else []
    for extra in classes[1:]:
        add(extra.lineno, "one-class", f"module defines more than one class ({extra.name})")
    cls = classes[0]
    is_saver_folder = folder in C.SAVER_FOLDERS
    bases = base_names(cls)

    if path.stem != naming.to_snake(cls.name):
        add(cls.lineno, "file-name", f"file {path.name} should be {naming.to_snake(cls.name)}.py for class {cls.name}")
    if is_saver_folder and not cls.name.endswith("Saver"):
        add(cls.lineno, "saver-name", f"class in {folder}/ must end with 'Saver' ({cls.name})")
    if not is_saver_folder and cls.name.endswith("Saver"):
        add(cls.lineno, "saver-name", f"a Saver belongs in entitysaver/ or documentsaver/, not {folder}/")
    if not docstring_of(cls) and not bases & C.ENUM_BASES:
        add(cls.lineno, "class-docstring", f"{cls.name} has no docstring")

    if is_saver_folder:
        if C.BASE_SAVER not in bases:
            add(cls.lineno, "saver-base", f"{cls.name} must inherit {C.BASE_SAVER}")
        assigned = set()
        for stmt in cls.body:
            is_doc = isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
            target = stmt.targets[0] if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 else None
            if isinstance(target, ast.Name) and target.id in ("model", "key_patterns"):
                assigned.add(target.id)
            elif not is_doc:
                add(stmt.lineno, "saver-body", "a saver declares only `model` and `key_patterns`; no logic")
        for needed in ("model", "key_patterns"):
            if needed not in assigned:
                add(cls.lineno, "saver-body", f"{cls.name} does not declare `{needed}`")
    else:
        if not bases:
            add(cls.lineno, "base-model", f"{cls.name} has no base class")
        if "BaseModel" in bases and path.stem != naming.to_snake(C.BASE_MODEL):
            add(cls.lineno, "base-model", f"derive from {C.BASE_MODEL}, not pydantic BaseModel")
        if not bases & C.ENUM_BASES:
            for stmt in cls.body:
                if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
                    continue
                annotation = ast.unparse(stmt.annotation)
                if annotation.startswith("ClassVar"):
                    continue
                for problem in field_spec.type_problems(annotation):
                    add(stmt.lineno, "forbidden-type", f"{stmt.target.id}: {problem}")
                call = stmt.value
                described = (
                    isinstance(call, ast.Call)
                    and getattr(call.func, "id", None) == C.FIELD_HELPER
                    and any(
                        k.arg == "description" and isinstance(k.value, ast.Constant) and str(k.value.value).strip()
                        for k in call.keywords
                    )
                )
                if not described:
                    add(stmt.lineno, "field-helper", f"{stmt.target.id}: use {C.FIELD_HELPER}(description=...) with a non-empty description")
        forbidden = {"models": ("entitymodels", "documentmodels"), "entitymodels": ("documentmodels",)}.get(folder, ())
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            if module and any(module.startswith(f"{C.PACKAGE}.{f}") for f in forbidden):
                add(node.lineno, "layering", f"{folder}/ must not import {module}")

    if want_tests and not (C.ROOT / "tests" / f"test_{path.stem}.py").exists():
        add(1, "test-missing", f"no tests/test_{path.stem}.py")
    return out


def stray_models() -> list:
    out = []
    package = C.ROOT / C.PACKAGE
    if not package.is_dir():
        return out
    for path in sorted(package.rglob("*.py")):
        if path.parent.name in C.ALL_FOLDERS and path.parent.parent == package:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and base_names(node) & {C.BASE_MODEL, "BaseModel"}:
                out.append((naming.rel(path), node.lineno, "stray-model", f"Pydantic class {node.name} must live in models/, entitymodels/ or documentmodels/"))
    return out


def collect(paths, want_tests):
    findings = []
    if not paths:
        for folder in C.ALL_FOLDERS:
            for path in naming.package_files((folder,)):
                findings += check_file(path, folder, want_tests)
        return findings + stray_models()
    for raw in paths:
        target = Path(raw).resolve()
        files = sorted(target.rglob("*.py")) if target.is_dir() else [target]
        for path in files:
            folder = path.parent.name
            if folder in C.ALL_FOLDERS and path.name != "__init__.py":
                findings += check_file(path, folder, want_tests)
    return findings


def main(argv) -> int:
    findings = collect([a for a in argv if not a.startswith("--")], "--no-tests" not in argv)
    for path, line, rule, message in sorted(findings):
        print(f"{path}:{line}: {rule} {message}")
    print(f"{len(findings)} finding(s)" if findings else "structure OK")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
