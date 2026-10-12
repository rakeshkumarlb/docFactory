from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.note_entry import NoteEntry


class Note(DocFactoryModel):
    """The notes of an application: passages of its original documents that fit no knowledge entity of the ontology (cover pages, appendices, glossaries, remarks), kept as notes so that nothing is lost. Notes never feed a generated document."""

    overview: str = doc_field(
        default='',
        description="One sentence saying what the notes of this application cover, e.g. 'Cover page, revision history and appendices of the SRS.' Empty until written.",
        question="What do the notes of this application cover?",
    )
    notes: list[NoteEntry] = doc_field(
        default_factory=list,
        description="The notes, one per passage worth keeping, e.g. a 'Document revision history' note and an 'Open issues list' note. Empty when nothing was kept.",
        question="Which passages of the documents are kept as notes?",
    )
