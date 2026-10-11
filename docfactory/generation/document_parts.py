"""The four stored parts of a generated document, the model of each and the key it is known by.

Every document is four validated objects (state files under output/<App>/state/):
the body (all sections), the document control, the revision history and the needs list. Keys keep the old shape
`<App>.Outputs.<DocType>[.<Part>]`, which the reports and tests use.
"""
from docfactory.documentmodels.document_body import DocumentBody
from docfactory.documentmodels.document_control import DocumentControl
from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.documentmodels.revision_history import RevisionHistory

BODY, CONTROL, HISTORY, NEEDS = "body", "control", "history", "needs"

PART_MODELS = {BODY: DocumentBody, CONTROL: DocumentControl, HISTORY: RevisionHistory, NEEDS: MissingInfo}
KEY_SUFFIXES = {BODY: "", CONTROL: ".DocumentControl", HISTORY: ".RevisionHistory", NEEDS: ".MissingInfo"}


def part_key(app_id: str, doc_type: str, part: str) -> str:
    """The key of one part of a document: `<App>.Outputs.<DocType>` for the body, plus '.DocumentControl', '.RevisionHistory' or '.MissingInfo'."""
    return f"{app_id}.Outputs.{doc_type}{KEY_SUFFIXES[part]}"
