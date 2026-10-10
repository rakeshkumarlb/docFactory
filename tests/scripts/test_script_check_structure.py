import check_structure

GOOD_MODEL = (
    "from docfactory.models.doc_factory_model import DocFactoryModel\n"
    "from docfactory.models.doc_field import doc_field\n\n\n"
    "class Widget(DocFactoryModel):\n"
    '    """A widget."""\n\n'
    '    name: str = doc_field(description="Name of the widget, e.g. Left.")\n'
)


def rules(project, files):
    for relative, content in files.items():
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return {rule for _, _, rule, _ in check_structure.collect([], want_tests=False)}


def rules_of(project, files, target):
    """Rules broken by one file only: findings accumulate across calls in a test."""
    rules(project, files)
    return {rule for path, _, rule, _ in check_structure.collect([], want_tests=False) if path == target}


def test_clean_project_has_no_findings(project):
    assert rules(project, {"docfactory/entitymodels/items/widget.py": GOOD_MODEL}) == set()


def test_two_classes_and_wrong_file_name(project):
    content = GOOD_MODEL + "\n\nclass Other(DocFactoryModel):\n    '''x'''\n"
    assert {"one-class"} <= rules(project, {"docfactory/entitymodels/items/widget.py": content})
    assert {"file-name"} <= rules(project, {"docfactory/entitymodels/items/gadget.py": GOOD_MODEL})


def test_field_rules(project):
    bad = GOOD_MODEL.replace('doc_field(description="Name of the widget, e.g. Left.")', "None")
    assert "field-helper" in rules(project, {"docfactory/entitymodels/items/widget.py": bad})
    bad = GOOD_MODEL.replace("name: str", "name: dict[str, str]")
    assert "forbidden-type" in rules(project, {"docfactory/entitymodels/items/widget.py": bad})
    bad = GOOD_MODEL.replace("DocFactoryModel)", "BaseModel)")
    assert "base-model" in rules(project, {"docfactory/entitymodels/items/widget.py": bad})


def test_layering_and_stray_models(project):
    bad = "from docfactory.documentmodels.x import X\n" + GOOD_MODEL
    assert "layering" in rules(project, {"docfactory/entitymodels/items/widget.py": bad})
    stray = "from docfactory.models.doc_factory_model import DocFactoryModel\n\n\nclass Loose(DocFactoryModel):\n    '''x'''\n"
    assert "stray-model" in rules(project, {"docfactory/loose.py": stray})


def test_saver_must_only_declare_model_and_patterns(project):
    saver = (
        "from docfactory.base_saver import BaseSaver\n\n\n"
        "class WidgetSaver(BaseSaver[Widget]):\n"
        '    """Saves widgets."""\n\n'
        "    model = Widget\n"
        '    key_patterns = ("{app}.Widget",)\n'
    )
    assert rules(project, {"docfactory/entitysaver/widget_saver.py": saver}) == set()
    logic = saver + "\n    def save(self):\n        pass\n"
    assert "saver-body" in rules(project, {"docfactory/entitysaver/widget_saver.py": logic})
    assert "saver-base" in rules(project, {"docfactory/entitysaver/widget_saver.py": saver.replace("BaseSaver[Widget]", "object")})


def test_only_entitymodels_has_sub_folders_and_they_are_facts_or_items(project):
    for bad in ("documentmodels/sub/widget.py", "entitymodels/widget.py", "entitymodels/nested/widget.py", "entitymodels/items/deeper/widget.py"):
        target = f"docfactory/{bad}"
        assert "folder-layout" in rules_of(project, {target: GOOD_MODEL}, target), bad
    good = "docfactory/documentmodels/widget.py"
    assert "folder-layout" not in rules_of(project, {good: GOOD_MODEL}, good)


def test_document_saver_mirrors_its_model(project):
    saver = (
        "from docfactory.base_saver import BaseSaver\n\n\n"
        "class WidgetSaver(BaseSaver[Widget]):\n"
        '    """Saves widgets."""\n\n'
        "    model = Widget\n"
        '    key_patterns = ("{app}.Outputs.Widget",)\n'
    )
    files = {"docfactory/documentmodels/widget.py": GOOD_MODEL, "docfactory/documentsaver/widget_saver.py": saver}
    assert rules(project, files) == set()
    lonely = "docfactory/documentsaver/gadget_saver.py"
    assert "saver-mirror" in rules_of(project, {lonely: saver.replace("Widget", "Gadget")}, lonely)


def test_missing_test_file_is_reported(project):
    (project / "docfactory/entitymodels/items").mkdir(parents=True)
    (project / "docfactory/entitymodels/items/widget.py").write_text(GOOD_MODEL, encoding="utf-8")
    findings = check_structure.collect([], want_tests=True)
    assert any(rule == "test-missing" and "widget" in message for _, _, rule, message in findings)



SAVER = """from docfactory.base_saver import BaseSaver


class WidgetSaver(BaseSaver[Widget]):
    '''Saves widgets.'''

    model = Widget
    key_patterns = ("{app}.Widget",)
"""


def test_fact_item_placement(project):
    fact = "docfactory/entitymodels/facts/widget.py"
    item = "docfactory/entitymodels/items/widget.py"
    saver = "docfactory/entitysaver/widget_saver.py"
    assert "fact-item-placement" in rules_of(project, {fact: GOOD_MODEL}, fact)  # a fact without a saver
    assert "fact-item-placement" not in rules_of(project, {saver: SAVER}, fact)  # now it has one
    assert "fact-item-placement" in rules_of(project, {item: GOOD_MODEL}, item)  # an item whose saver exists
    (project / saver).unlink()
    assert "fact-item-placement" not in rules_of(project, {}, item)  # an item without a saver is right
