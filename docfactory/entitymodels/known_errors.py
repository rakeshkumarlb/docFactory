from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.known_error import KnownError


class KnownErrors(DocFactoryModel):
    """The known errors of an application, each with its symptoms, workaround and fix status."""

    known_errors: list[KnownError] = doc_field(
        default_factory=list,
        description="The known errors, one entry each, e.g. an error titled 'Report export times out'. An empty list means none have been recorded yet.",
        question="Which known errors exist?",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the known errors as a whole, e.g. 'Reviewed at every release.' Leave empty when there is nothing to add.",
        question="Is there any additional context about the known errors?",
    )
