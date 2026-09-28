from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class MissingInfo(DocFactoryModel):
    """One field build_document could not fill: which field, what to ask, and where the answer should come from."""

    field: str = doc_field(
        description="Dotted path of the missing field within the document object, e.g. 'application_summary.business_overview'. Identifies exactly which slot in the built document has no value yet.",
        question="Which document field is missing a value?",
        min_length=1,
        binding="caller",
    )
    question: str = doc_field(
        description="The question to ask to get this value, copied from the missing field's own metadata, e.g. 'What is the primary business purpose of this application?'.",
        question="What question should be asked to obtain this value?",
        min_length=1,
        binding="caller",
    )
    expected_source: str = doc_field(
        description="The fact key/field that should have supplied this value, e.g. 'ApplicationOverview.business_overview'. Points the caller at the knowledge fact to fill in.",
        question="Which fact key/field should supply this value?",
        min_length=1,
        binding="caller",
    )
