"""Reads the YAML frontmatter of a concept file. ISO 8601 instants stay text (YAML would turn them into datetime objects)."""
import yaml

_TextTimestampLoader = type("TextTimestampLoader", (yaml.SafeLoader,), {})
_TextTimestampLoader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_frontmatter(text: str) -> dict:
    """The frontmatter mapping; ValueError when the text is not YAML or not a mapping."""
    try:
        loaded = yaml.load(text, Loader=_TextTimestampLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"frontmatter is not valid YAML: {error}") from error
    if not isinstance(loaded, dict):
        raise ValueError("frontmatter is not a mapping")
    return loaded
