"""Summarise a usage log written with DOCFACTORY_USAGE_LOG: `python -m docfactory.agents.run_usage <usage.jsonl>`.

One line per step (the tool the call offered: submit_recognition, submit_extraction, ...): calls, prompt tokens, output tokens; then the total.
"""
import json
import sys
from pathlib import Path

STEPS = {"submit_chunk_tags": "ingestion fallback (tags)", "submit_scope": "ingestion fallback (scope)", "submit_recognition": "recognition",
         "submit_merges": "entity resolution", "submit_extraction": "extraction (batches and entity items)", "submit_discovery": "notes",
         "submit_type_proposal": "type proposals", "submit_needs": "needs lists"}


def summarise(path: Path) -> str:
    """The plain-text summary of the usage log at `path`."""
    rows: dict[str, list[int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            row = rows.setdefault(entry["tool"], [0, 0, 0])
            row[0] += 1
            row[1] += entry["prompt_tokens"]
            row[2] += entry["output_tokens"]
    lines = [f"{'step':40} {'calls':>7} {'prompt tokens':>14} {'output tokens':>14}"]
    for tool, (calls, prompt, output) in sorted(rows.items(), key=lambda kv: -kv[1][1]):
        lines.append(f"{STEPS.get(tool, tool or '(no tool)'):40} {calls:>7} {prompt:>14,} {output:>14,}")
    total = [sum(r[i] for r in rows.values()) for i in range(3)]
    lines.append(f"{'total':40} {total[0]:>7} {total[1]:>14,} {total[2]:>14,}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    print(summarise(Path(argv[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
