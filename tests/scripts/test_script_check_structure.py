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


def test_a_class_named_saver_is_just_a_class_now(project):
    """Savers no longer exist: BundleStore is the only writer, so there is no saver rule and no saver folder."""
    saver = "from docfactory.models.doc_factory_model import DocFactoryModel\n\n\nclass WidgetSaver(DocFactoryModel):\n    \'\'\'x\'\'\'\n"
    assert "saver-name" not in rules(project, {"docfactory/models/widget_saver.py": saver})


def test_only_entitymodels_has_sub_folders_and_they_are_facts_or_items(project):
    for bad in ("documentmodels/sub/widget.py", "entitymodels/widget.py", "entitymodels/nested/widget.py", "entitymodels/items/deeper/widget.py"):
        target = f"docfactory/{bad}"
        assert "folder-layout" in rules_of(project, {target: GOOD_MODEL}, target), bad
    good = "docfactory/documentmodels/widget.py"
    assert "folder-layout" not in rules_of(project, {good: GOOD_MODEL}, good)


def test_missing_test_file_is_reported(project):
    (project / "docfactory/entitymodels/items").mkdir(parents=True)
    (project / "docfactory/entitymodels/items/widget.py").write_text(GOOD_MODEL, encoding="utf-8")
    findings = check_structure.collect([], want_tests=True)
    assert any(rule == "test-missing" and "widget" in message for _, _, rule, message in findings)



def registry(project, *names):
    """Write a fact registry that lists `names`."""
    target = project / "docfactory/bundle/fact_registry.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f'    "{name}": {{"model": {name}, "shared": False}},\n' for name in names)
    target.write_text("FACT_SPECS = {\n" + body + "}\n", encoding="utf-8")


def test_fact_item_placement(project):
    fact = "docfactory/entitymodels/facts/widget.py"
    item = "docfactory/entitymodels/items/widget.py"
    registry(project)
    assert "fact-item-placement" in rules_of(project, {fact: GOOD_MODEL}, fact)  # a fact that is not registered
    registry(project, "Widget")
    assert "fact-item-placement" not in rules_of(project, {}, fact)  # now it is
    assert "fact-item-placement" in rules_of(project, {item: GOOD_MODEL}, item)  # an item that is registered
    registry(project)
    assert "fact-item-placement" not in rules_of(project, {}, item)  # an item that is not registered is right
