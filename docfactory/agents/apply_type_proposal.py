"""The gated developer step that turns a stored type proposal into code: `python -m docfactory.agents.apply_type_proposal <Entity> [--no-gate]` (`--list` shows the proposals).

Not a runtime LLM call and not an agent: deterministic code that runs the scaffold scripts of `.claude/scripts/` from the proposal's specs
(item type, then the fact with its registry entry and tests), adds the tagging signals to `signals.json`, regenerates `docs/ontology.md`, runs the
quality gate (structure check + the whole test suite) and tags the stored originals with the new entity. If any step fails, every file it touched is
restored and every file it created is removed. The result is left uncommitted in the working tree for a human (or the
`docfactory-pydantic-developer-agent`, skill `/docfactory-apply-type-proposal`) to review. Extraction of the new entity is run by hand afterwards.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from docfactory.agents.apply_error import ApplyError
from docfactory.ontology.proposal_spec import fact_spec, item_spec, signals_entry
from docfactory.ontology.proposal_store import APPLIED, ProposalStore
from docfactory.project_root import PROJECT_ROOT

SCRIPTS = PROJECT_ROOT / ".claude" / "scripts"
TOUCHED = ["docfactory/bundle/fact_registry.py", "docfactory/ontology/signals.json", "docs/ontology.md"]
WATCHED = ["docfactory/entitymodels", "tests"]


def _run(command: list[str]) -> str:
    done = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")
    if done.returncode:
        raise ApplyError(f"{' '.join(command[1:3])} failed ({done.returncode}):\n{(done.stdout + done.stderr).strip()[-2000:]}")
    return done.stdout.strip()


def _files() -> set[Path]:
    return {p for folder in WATCHED for p in (PROJECT_ROOT / folder).rglob("*.py")}


def _add_signals(text: str, entry: str) -> str:
    body = text.rstrip()
    if not body.endswith("]"):
        raise ApplyError("signals.json does not end with ']'")
    newline = "\r\n" if "\r\n" in text else "\n"
    return (body[:-1].rstrip() + ",\n" + entry + "\n]\n").replace("\n", newline)


def apply_proposal(entity: str, gate: bool = True) -> list[str]:
    """Create the model, registry entry, tests and signals of the stored proposal `entity`. Returns what was done, line by line.

    Raises ApplyError (after rolling back) when a step fails; FileNotFoundError when there is no pending proposal of that name.
    """
    found = ProposalStore().get(entity)
    if found is None:
        raise FileNotFoundError(f"no proposal for {entity!r}; stored proposals: {[p.entity for _, p in ProposalStore().list()]}")
    status, proposal = found
    if status == APPLIED:
        raise ApplyError(f"{entity} was applied already")
    saved = {name: (PROJECT_ROOT / name).read_bytes() for name in TOUCHED}
    before = _files()
    done = []
    try:
        with tempfile.TemporaryDirectory() as folder:
            for label, spec, options in (("item", item_spec(proposal), []), ("fact", fact_spec(proposal), ["--scope", proposal.scope])):
                if spec is None:
                    continue
                path = Path(folder) / f"{spec['class']}.spec.json"
                path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
                _run([sys.executable, str(SCRIPTS / "scaffold_model.py"), "entity-model", str(path), *options])
                done.append(f"created {label} model {spec['class']} with its tests")
        signals = PROJECT_ROOT / "docfactory/ontology/signals.json"
        signals.write_bytes(_add_signals(signals.read_bytes().decode("utf-8"), signals_entry(proposal)).encode("utf-8"))
        done.append("added the tagging signals")
        _run([sys.executable, "-m", "docfactory.ontology.ontology_render"])
        done.append("regenerated docs/ontology.md")
        if gate:
            _run([sys.executable, str(SCRIPTS / "run_gate.py")])
            done.append("quality gate passed")
        done.append(_run([sys.executable, "-m", "docfactory.ingest.retag_entity", entity]) or "no stored originals to tag")
    except Exception as error:
        for name, data in saved.items():
            (PROJECT_ROOT / name).write_bytes(data)
        for path in _files() - before:
            path.unlink()
        raise ApplyError(f"{error}\n(rolled back: restored {', '.join(TOUCHED)} and removed the files it created)") from error
    ProposalStore().mark_applied(entity)
    done.append(f"next: review the new files, then python -m docfactory.agents.run_extraction \"<bundle path>\" --entity {entity}")
    return done


def main(argv: list[str]) -> int:
    if argv == ["--list"] or not argv:
        for status, proposal in ProposalStore().list():
            print(f"{proposal.entity} ({status}): {proposal.doc} [{proposal.source_path}]")
        return 0
    try:
        for line in apply_proposal(argv[0], gate="--no-gate" not in argv):
            print(line)
    except (ApplyError, FileNotFoundError) as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
