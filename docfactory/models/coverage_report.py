from docfactory.models.chunk_coverage import ChunkCoverage
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class CoverageReport(DocFactoryModel):
    """The coverage of one ingested original: for every chunk, whether its content is in a fact or lost on the way (unmapped, skipped by scope, not extracted yet). Derived from the Source, the originals and the contributions on every run, never stored."""

    path: str = doc_field(
        description="Bundle path of the original, '<scope>/references/<file name>', e.g. 'AI-Driven-Job-Matching-Platform/references/Annex-A SRS.pdf'.",
        question="Which ingested original is this report about?",
        min_length=1,
    )
    chunks: list[ChunkCoverage] = doc_field(
        default_factory=list,
        description="One entry per chunk of the original, in document order, e.g. 76 entries for a 50-page SRS.",
        question="What became of each chunk of the original?",
    )
