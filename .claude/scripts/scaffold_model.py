"""Usage: python .claude/scripts/scaffold_model.py <kind> <spec.json> [saver options] [--dry-run]

kind: entity-model | shared-model

Validates the spec (see field_spec.py), then writes the model file and its test file. With --scope it also registers the
model as a fact (an entry in docfactory/bundle/fact_registry.py) and writes the fact's test (tests/test_<model>_fact.py, through
BundleStore), all or nothing. Never overwrites.

An entity-model that is a fact goes to entitymodels/facts/; one that is not is an item and goes to entitymodels/items/.

Fact option (entity-model only; nested items and shared models are never facts):
    --scope app|shared      keys {app}.<Class> (+ {app}.Components.{component}.<Class>) or Shared.<Class>
A fact needs the package skeleton (the fact registry, tests/conftest.py with the tmp_bundle fixture). A fact is also tagged during
ingestion: add its entry to docfactory/ontology/signals.json afterwards (a test fails until every fact has one).
--dry-run prints every file and writes nothing. Exit 0 written, 1 rejected (problems listed), 2 usage.
"""
import argparse
import json
import sys

import conventions as C
import field_spec
import naming
import render_model
import registry_edit
import render_fact_test


def main(argv) -> int:
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("kind", choices=sorted(C.KINDS))
    parser.add_argument("spec")
    parser.add_argument("--scope", choices=["app", "shared"])
    parser.add_argument("--dry-run", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    kind = args.kind
    wants_fact = bool(args.scope)

    try:
        spec = field_spec.load_model_spec(args.spec)
    except field_spec.SpecError as error:
        print("SPEC REJECTED:", *error.problems, sep="\n  - ")
        return 1
    info = naming.resolve(kind, spec["class"], fact=wants_fact)
    problems = list(info["errors"])
    if info["exists"]:
        problems.append(f"{info['file']} already exists: use the docfactory-add-field skill to change it")
    if (C.ROOT / info["test_file"]).exists():
        problems.append(f"{info['test_file']} already exists")

    files = {}
    fact = patterns = registry_text = None
    if wants_fact:
        if kind == "shared-model":
            problems.append("shared models are never facts")
        else:
            patterns = naming.fact_pattern(spec["class"], args.scope)
            fact = naming.fact_target(kind, spec["class"], info["module"])
            if fact["registered"]:
                problems.append(f"{spec['class']} is already registered in {fact['registry_file']}")
            if (C.ROOT / fact["test_file"]).exists():
                problems.append(f"{fact['test_file']} already exists")
            if not naming.registry_path().exists():
                problems.append(f"{fact['registry_file']} is missing: build the package skeleton first")
            else:
                try:
                    registry_text = registry_edit.add_entry(naming.registry_path().read_text(encoding="utf-8"), spec["class"], info["module"], args.scope == "shared")
                except ValueError as error:
                    problems.append(str(error))
            if render_fact_test.changed_field(spec) is None:
                problems.append("fact tests need at least one field whose example is a plain string (used for the changed payload)")
            conftest = C.ROOT / "tests" / "conftest.py"
            if not conftest.exists() or "def tmp_bundle" not in conftest.read_text(encoding="utf-8"):
                problems.append("tests/conftest.py with a tmp_bundle fixture is missing: build the package skeleton first")
    if problems:
        print("CANNOT SCAFFOLD:", *problems, sep="\n  - ")
        return 1

    files[info["file"]] = render_model.render_model(spec)
    files[info["test_file"]] = render_model.render_model_test(spec, info["module"])
    if fact:
        files[fact["test_file"]] = render_fact_test.render_fact_test(fact, spec, args.scope)
        files[fact["registry_file"]] = registry_text
    if args.dry_run:
        for name, text in files.items():
            print(f"# {name}\n{text}")
        return 0

    leaves = [info["folder"]]
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
    report = {"created": [name for name in files if name != C.FACT_REGISTRY_FILE], "key_patterns": patterns}
    if fact:
        report["registered_in"] = C.FACT_REGISTRY_FILE
        report["next"] = f"add the tagging signals of {spec['class']} to docfactory/ontology/signals.json (a test fails until it has an entry)"
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
