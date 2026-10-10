"""Usage: python .claude/scripts/add_field.py <ModelClass> <field.json> [--allow-mandatory] [--dry-run]

field.json is one field spec (see field_spec.py) plus an optional "imports" list.
Inserts the field after the class's last statement and adds missing imports. A mandatory field
(default REQUIRED) breaks every stored payload, so it needs --allow-mandatory.
Prints the lines to add to MINIMAL / FULL in the model's test file. Exit 0 done, 1 rejected, 2 usage.
"""
import ast
import json
import sys

import conventions as C
import field_spec
import naming
import render_model


def main(argv) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2
    class_name, spec_path = args
    dry_run, allow_mandatory = "--dry-run" in argv, "--allow-mandatory" in argv
    try:
        field = field_spec.load_json(spec_path)
    except field_spec.SpecError as error:
        print("SPEC REJECTED:", *error.problems, sep="\n  - ")
        return 1
    imports = field.pop("imports", []) if isinstance(field, dict) else []

    files = naming.find_class(class_name, C.MODEL_FOLDERS)
    problems = []
    if len(files) != 1:
        problems.append(f"expected exactly one model class {class_name} in {list(C.MODEL_FOLDERS)}, found {len(files)}")
        print("CANNOT ADD:", *problems, sep="\n  - ")
        return 1
    path = files[0]
    problems += field_spec.validate_field(field)
    for line in imports:
        problems += field_spec.validate_import(line)
    if problems:
        print("SPEC REJECTED:", *problems, sep="\n  - ")
        return 1

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name)
    existing = {n.target.id for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    if field["name"] in existing:
        problems.append(f"field {field['name']!r} already exists in {class_name}")
    if field_spec.default_of(field)[0] and not allow_mandatory:
        problems.append("a mandatory field breaks all stored payloads; make it optional or pass --allow-mandatory")
    if problems:
        print("CANNOT ADD:", *problems, sep="\n  - ")
        return 1

    lines = source.split("\n")
    lines[cls.end_lineno:cls.end_lineno] = ["", *render_model.render_field(field).split("\n")]
    wanted = render_model.merge_imports(render_model.field_import_lines([field]), imports)
    present = {ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))}
    missing = [line for line in wanted if ast.unparse(ast.parse(line).body[0]) not in present]
    if missing:
        last_import = max((n.end_lineno for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))), default=0)
        lines[last_import:last_import] = missing
    new_source = "\n".join(lines)
    ast.parse(new_source)  # never write a file that does not parse

    entry = f'    {json.dumps(field["name"])}: {field["example"]},'
    report = {
        "file": naming.rel(path),
        "imports_added": missing,
        "test_file": f"tests/test_{naming.to_snake(class_name)}.py",
        "add_to_FULL": entry,
        "add_to_MINIMAL": entry if field_spec.default_of(field)[0] else None,
        "saver_test": (
            f"tests/test_{naming.to_snake(class_name)}_saver.py"
            if (C.ROOT / f"tests/test_{naming.to_snake(class_name)}_saver.py").exists()
            else None
        ),
        "hand_edit_tests": "extend the parametrized lists and the defaults test; add the entry to _FULL in the saver test too",
    }
    if dry_run:
        print(new_source)
    else:
        path.write_text(new_source, encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
