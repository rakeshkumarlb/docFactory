"""Deterministic markdown body of an OKF concept file, rendered from a fact's JSON, fields in the order of the JSON: same JSON in, same text out."""
import json


def _label(name: str) -> str:
    return name.replace("_", " ").capitalize()


def _empty(value) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _is_na(value) -> bool:
    return isinstance(value, dict) and list(value) == ["reason"]


def _scalar(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _lines(value, depth: int) -> list[str]:
    pad = "  " * depth
    if isinstance(value, dict):
        out = []
        for name, item in value.items():
            if _empty(item):
                continue
            if _is_na(item):
                out.append(f"{pad}- **{_label(name)}:** N/A - {item['reason']}")
            elif isinstance(item, (dict, list)):
                out += [f"{pad}- **{_label(name)}:**", *_lines(item, depth + 1)]
            else:
                out.append(f"{pad}- **{_label(name)}:** {_scalar(item)}")
        return out
    out = []
    for number, item in enumerate(value, start=1):
        if isinstance(item, (dict, list)):
            out += [f"{pad}- Item {number}", *_lines(item, depth + 1)]
        else:
            out.append(f"{pad}- {_scalar(item)}")
    return out


def render_body(title: str, value_json: str) -> str:
    """`# <title>` then one section per answered top-level field. Unanswered (empty) fields are left out, never invented."""
    data = json.loads(value_json)
    blocks = [f"# {title}"]
    for name, item in data.items():
        if _empty(item):
            continue
        if _is_na(item):
            body = [f"N/A - {item['reason']}"]
        elif isinstance(item, (dict, list)):
            body = _lines(item, 0)
        else:
            body = [_scalar(item)]
        blocks.append("\n".join([f"## {_label(name)}", "", *body]))
    return "\n\n".join(blocks) + "\n"
