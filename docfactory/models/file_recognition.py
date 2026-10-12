from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.window_recognition import WindowRecognition


class FileRecognition(DocFactoryModel):
    """What recognition found in one ingested original, window by window (a recognition concept file of the bundle, written only by the recognition pipeline). The entity graph is the deterministic merge of the recognitions of all originals, so re-recognizing one file replaces only its own share. Infrastructure; holds no fact values."""

    resource: str = doc_field(
        description="Bundle path of the original, e.g. 'Acme/references/srs.pdf'.",
        question="Which ingested original was recognized?",
        min_length=1,
    )
    windows: list[WindowRecognition] = doc_field(
        default_factory=list,
        description="The accepted recognition of each window, in document order, e.g. one entry per window of about 2000 words. A window whose call failed is absent and is retried on the next run.",
        question="What was recognized in each window?",
    )
    hashcode: str = doc_field(
        description="SHA-256 hex of the canonical JSON of windows, 64 lower-case hex characters, e.g. the sha256_hex of that text; a file whose windows no longer match it was edited outside the system.",
        question="What is the SHA-256 hex of the windows?",
        pattern="^[0-9a-f]{64}$",
    )
    generated_by: str = doc_field(
        description="Actor that produced the recognition, <producer>/<version>, e.g. 'okf-recognition-agent/gemma4:31b'.",
        question="Which actor produced this recognition?",
        min_length=1,
    )
    timestamp: str = doc_field(
        description="When the recognition was written, ISO 8601 with UTC offset, e.g. '2026-10-12T09:30:00+00:00'.",
        question="When was this recognition written?",
        min_length=1,
    )
