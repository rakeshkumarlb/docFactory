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
    assert rules(project, {"docfactory/entitymodels/widget.py": GOOD_MODEL}) == set()


def test_two_classes_and_wrong_file_name(project):
    content = GOOD_MODEL + "\n\nclass Other(DocFactoryModel):\n    '''x'''\n"
    assert {"one-class"} <= rules(project, {"docfactory/entitymodels/widget.py": content})
    assert {"file-name"} <= rules(project, {"docfactory/entitymodels/gadget.py": GOOD_MODEL})


def test_field_rules(project):
    bad = GOOD_MODEL.replace('doc_field(description="Name of the widget, e.g. Left.")', "None")
    assert "field-helper" in rules(project, {"docfactory/entitymodels/widget.py": bad})
    bad = GOOD_MODEL.replace("name: str", "name: dict[str, str]")
    assert "forbidden-type" in rules(project, {"docfactory/entitymodels/widget.py": bad})
    bad = GOOD_MODEL.replace("DocFactoryModel)", "BaseModel)")
    assert "base-model" in rules(project, {"docfactory/entitymodels/widget.py": bad})


def test_layering_and_stray_models(project):
    bad = "from docfactory.documentmodels.shared.x import X\n" + GOOD_MODEL
    assert "layering" in rules(project, {"docfactory/entitymodels/widget.py": bad})
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


def test_document_models_and_savers_must_sit_in_a_role_folder(project):
    for bad in ("documentmodels/widget.py", "documentmodels/sections/widget.py", "entitymodels/nested/widget.py"):
        target = f"docfactory/{bad}"
        assert "role-folder" in rules_of(project, {target: GOOD_MODEL}, target), bad
    good = "docfactory/documentmodels/entitybound/widget.py"
    assert "role-folder" not in rules_of(project, {good: GOOD_MODEL}, good)


def test_role_layering_inside_documentmodels(project):
    section = "from docfactory.documentmodels.documents.x import X\n" + GOOD_MODEL
    assert "layering" in rules(project, {"docfactory/documentmodels/entitybound/widget.py": section})
    assert "layering" in rules(project, {"docfactory/documentmodels/shared/widget.py": section})
    shared = "from docfactory.documentmodels.entitybound.x import X\n" + GOOD_MODEL
    assert "layering" in rules(project, {"docfactory/documentmodels/shared/widget.py": shared})
    compose = (
        "from docfactory.documentmodels.entitybound.x import X\n"
        "from docfactory.documentmodels.shared.y import Y\n" + GOOD_MODEL
    )
    target = "docfactory/documentmodels/documents/widget.py"
    assert "layering" not in rules_of(project, {target: compose}, target)


def test_document_saver_mirrors_its_models_role_and_entitybound_has_no_saver(project):
    saver = (
        "from docfactory.base_saver import BaseSaver\n\n\n"
        "class WidgetSaver(BaseSaver[Widget]):\n"
        '    """Saves widgets."""\n\n'
        "    model = Widget\n"
        '    key_patterns = ("{app}.Outputs.Widget",)\n'
    )
    files = {"docfactory/documentmodels/shared/widget.py": GOOD_MODEL, "docfactory/documentsaver/shared/widget_saver.py": saver}
    assert rules(project, files) == set()
    wrong_role = "docfactory/documentsaver/documents/widget_saver.py"
    assert "saver-mirror" in rules_of(project, {wrong_role: saver}, wrong_role)
    entitybound = "docfactory/documentsaver/entitybound/widget_saver.py"
    assert "role-folder" in rules_of(project, {entitybound: saver}, entitybound)


def test_missing_test_file_is_reported(project):
    (project / "docfactory/entitymodels/widget.py").write_text(GOOD_MODEL, encoding="utf-8")
    findings = check_structure.collect([], want_tests=True)
    assert any(rule == "test-missing" and "widget" in message for _, _, rule, message in findings)
