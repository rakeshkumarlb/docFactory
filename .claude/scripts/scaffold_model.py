"""Usage: python .claude/scripts/scaffold_model.py <kind> <spec.json> [saver options] [--dry-run]

kind: entity-model | document-model | shared-model

Validates the spec (see field_spec.py), then writes the model file and its test file. With a saver
option it also writes the saver and its test file, all or nothing. Never overwrites.

A document-model spec carries a `role` that picks the sub-folder: documents/ (a document body), shared/
(reused by every document type) or entitybound/ (a section bound to entity facts). Its saver mirrors it in
documentsaver/<role>/; an entitybound section gets no saver.

An entity-model with a saver is a fact and goes to entitymodels/facts/; without one it is an item and goes
to entitymodels/items/.

Saver options (entity-model and document-model only; nested items, sections and shared models get none):
    --scope app|shared      entity: keys {app}.<Class> (+ {app}.Components.{component}.<Class>) or Shared.<Class>
    --doctype <Name>        document body: key {app}.Outputs.<Name>
    --pattern <pattern>     explicit key pattern, repeatable (e.g. "{app}.Outputs.{doctype}.DocumentControl");
                            replaces --scope/--doctype
A saver needs the package skeleton (BaseSaver, tools, tests/conftest.py with the tmp_db fixture).
--dry-run prints every file and writes nothing. Exit 0 written, 1 rejected (problems listed), 2 usage.
"""
import argparse
import json
import sys

import conventions as C
import field_spec
import naming
import render_model
import render_saver


def saver_patterns(args, kind, class_name):
    if args.pattern:
        return list(args.pattern), []
    if kind == "entity-model" and args.scope == "app":
        return [f"{{app}}.{class_name}", f"{{app}}.Components.{{component}}.{class_name}"], []
    if kind == "entity-model" and args.scope == "shared":
        return [f"Shared.{class_name}"], []
    if kind == "document-model" and args.doctype:
        return [f"{{app}}.Outputs.{args.doctype}"], []
    hint = "--scope app|shared" if kind == "entity-model" else "--doctype <Name> or --pattern <pattern>"
    return [], [f"a saver needs its key pattern(s): pass {hint}"]


def main(argv) -> int:
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("kind", choices=sorted(C.KINDS))
    parser.add_argument("spec")
    parser.add_argument("--scope", choices=["app", "shared"])
    parser.add_argument("--doctype")
    parser.add_argument("--pattern", action="append")
    parser.add_argument("--dry-run", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    kind = args.kind
    wants_saver = bool(args.scope or args.doctype or args.pattern)

    try:
        spec = field_spec.load_model_spec(args.spec, kind)
    except field_spec.SpecError as error:
        print("SPEC REJECTED:", *error.problems, sep="\n  - ")
        return 1
    info = naming.resolve(kind, spec["class"], spec.get("role"), fact=wants_saver)
    problems = list(info["errors"])
    if kind == "document-model":
        problems += field_spec.binding_problems(spec["fields"])
    if info["exists"]:
        problems.append(f"{info['file']} already exists: use the docfactory-add-field skill to change it")
    if (C.ROOT / info["test_file"]).exists():
        problems.append(f"{info['test_file']} already exists")

    files = {}
    saver = patterns = None
    if wants_saver:
        if kind == "shared-model":
            problems.append("shared models get no saver")
        elif spec.get("role") not in (None, *C.SAVER_ROLES):
            problems.append(f"a {spec['role']} model gets no saver: it is stored inside its document body")
        else:
            patterns, pattern_errors = saver_patterns(args, kind, spec["class"])
            problems += pattern_errors
            problems += [p for pattern in patterns for p in naming.pattern_problems(kind, pattern)]
            saver = naming.saver_target(kind, spec["class"], info["module"], spec.get("role"))
            if saver["exists"] or (C.ROOT / saver["test_file"]).exists():
                problems.append(f"{saver['file']} or {saver['test_file']} already exists")
            if render_saver.changed_field(spec) is None:
                problems.append("saver tests need at least one field whose example is a plain string (used for the changed payload)")
            conftest = C.ROOT / "tests" / "conftest.py"
            if not conftest.exists() or "def tmp_db" not in conftest.read_text(encoding="utf-8"):
                problems.append("tests/conftest.py with a tmp_db fixture is missing: build the package skeleton first")
    if problems:
        print("CANNOT SCAFFOLD:", *problems, sep="\n  - ")
        return 1

    files[info["file"]] = render_model.render_model(spec)
    files[info["test_file"]] = render_model.render_model_test(spec, info["module"])
    if saver:
        files[saver["file"]] = render_saver.render_saver(saver, patterns)
        files[saver["test_file"]] = render_saver.render_saver_test(saver, spec, patterns)
    if args.dry_run:
        for name, text in files.items():
            print(f"# {name}\n{text}")
        return 0

    leaves = [info["folder"]] + ([saver["folder"]] if saver else [])
    folders = {C.PACKAGE}
    for leaf in leaves:  # every package on the way down gets an __init__.py
        parts = leaf.split("/")
        folders |= {"/".join(parts[:n]) for n in range(1, len(parts) + 1)}
    for folder in sorted(folders):
        (C.ROOT / folder).mkdir(parents=True, exist_ok=True)
        (C.ROOT / folder / "__init__.py").touch()
    for name, text in files.items():
        target = C.ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    print(json.dumps({"created": list(files), "key_patterns": patterns}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
