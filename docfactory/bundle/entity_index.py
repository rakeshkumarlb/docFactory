"""The index.md of a fact's item folder (OKF section 8): the items by list field, each a link with its identifier, for progressive disclosure."""
from docfactory.bundle.item_file_render import items_section


def entity_index_text(title: str, fields: list[tuple[str, list[tuple[str, str]]]]) -> str:
    """The folder index: a title line, then per list field the links to its items. `fields` = [(field, [(item id, bundle-relative path)])]."""
    return f"# {title}\n\n" + items_section(fields).replace("# Items\n\n", "", 1)
