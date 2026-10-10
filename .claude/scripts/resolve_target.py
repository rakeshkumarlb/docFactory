"""Usage: python .claude/scripts/resolve_target.py <kind> <ClassName> [facts|items]

kind: entity-model | shared-model
entity-model: facts (has a saver: entitymodels/facts/) | items (no saver: entitymodels/items/, the default)
Prints JSON with folder, module, file, test file and any errors (bad name, bootstrap class, class
already defined elsewhere). Exit 1 when there are errors.
"""
import json
import sys

import conventions as C
import naming


def main(argv) -> int:
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    extra = argv[2] if len(argv) == 3 else None
    if argv[0] == "entity-model":
        if extra not in (None, *C.ENTITY_SUBFOLDERS):
            print(f"entity-model takes {' or '.join(C.ENTITY_SUBFOLDERS)} as its third argument (got {extra!r})")
            return 2
        info = naming.resolve(argv[0], argv[1], fact=extra == C.ENTITY_FACTS)
    else:
        info = naming.resolve(argv[0], argv[1])
    print(json.dumps(info, indent=2))
    return 1 if info["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
