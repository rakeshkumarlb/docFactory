"""Field shapes used by merging and grounding (Phase 3 redesign, step 1)."""
from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.extract.model_shapes import identity_field, is_enum, item_model
from docfactory.saver_resolution import entity_saver_classes


def test_item_model_and_enum_detection():
    assert item_model(FunctionalRequirements.model_fields["requirements"].annotation).__name__ == "Requirement"
    assert item_model(FunctionalRequirements.model_fields["out_of_scope"].annotation) is None
    assert item_model(Architecture.model_fields["components"].annotation).__name__ == "Component"
    requirement = item_model(FunctionalRequirements.model_fields["requirements"].annotation)
    assert is_enum(requirement.model_fields["priority"].annotation) and not is_enum(requirement.model_fields["title"].annotation)


def test_every_list_item_of_every_fact_has_a_text_identity_field():
    """Merging unions list items by identity: the first mandatory field of every item model must be a str."""
    for saver_class in entity_saver_classes():
        for field in saver_class.model.model_fields.values():
            items = item_model(field.annotation)
            if items is not None:
                assert items.model_fields[identity_field(items)].annotation is str, items.__name__
