"""The document types generate knows: per type its body model, its body saver and the document's name (used in the title).

A new document type is a new body model (through the developer agent) and one line here; no new generation code.
"""
from docfactory.documentmodels.documents.overview_document import OverviewDocument
from docfactory.documentmodels.documents.smtd_document import SmtdDocument
from docfactory.documentmodels.documents.sop_document import SopDocument
from docfactory.documentmodels.documents.srs_document import SrsDocument
from docfactory.documentsaver.documents.overview_document_saver import OverviewDocumentSaver
from docfactory.documentsaver.documents.smtd_document_saver import SmtdDocumentSaver
from docfactory.documentsaver.documents.sop_document_saver import SopDocumentSaver
from docfactory.documentsaver.documents.srs_document_saver import SrsDocumentSaver

DOC_TYPES = {
    "Overview": {"model": OverviewDocument, "saver": OverviewDocumentSaver, "name": "Application Overview"},
    "SMTD": {"model": SmtdDocument, "saver": SmtdDocumentSaver, "name": "Software Maintenance and Transition Document"},
    "SRS": {"model": SrsDocument, "saver": SrsDocumentSaver, "name": "Software Requirements Specification"},
    "SOP": {"model": SopDocument, "saver": SopDocumentSaver, "name": "Standard Operating Procedures"},
}
