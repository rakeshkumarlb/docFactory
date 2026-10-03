"""Usage: python .claude/scripts/run_gate.py [--structure-only] [--no-tests-check]

The quality gate: (1) static structure check, (2) the whole pytest suite. Prints both results.
Exit 0 only when both pass. Do not report a task done unless this prints GATE PASSED.
"""
import subprocess
import sys
from pathlib import Path

import conventions as C

HERE = Path(__file__).resolve().parent


def run(command) -> int:
    print("$", " ".join(str(c) for c in command))
    return subprocess.run(command, cwd=C.ROOT).returncode


def main(argv) -> int:
    structure_command = [sys.executable, str(HERE / "check_structure.py")]
    if "--no-tests-check" in argv:
        structure_command.append("--no-tests")
    structure = run(structure_command)
    if "--structure-only" in argv:
        print("GATE PASSED (structure only)" if structure == 0 else "GATE FAILED: structure")
        return structure
    tests = run([sys.executable, "-m", "pytest", "-q"])
    if structure == 0 and tests == 0:
        print("GATE PASSED")
        return 0
    failed = [name for name, code in (("structure", structure), ("tests", tests)) if code]
    print(f"GATE FAILED: {', '.join(failed)}" + (" (pytest exit 5 = no tests collected)" if tests == 5 else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
