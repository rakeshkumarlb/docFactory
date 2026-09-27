"""Usage: python .claude/scripts/resolve_target.py <kind> <ClassName>

kind: entity-model | document-model | shared-model
Prints JSON with folder, module, file, test file and any errors (bad name, bootstrap class, class
already defined elsewhere). Exit 1 when there are errors.
"""
import json
import sys

import naming


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    info = naming.resolve(argv[0], argv[1])
    print(json.dumps(info, indent=2))
    return 1 if info["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
