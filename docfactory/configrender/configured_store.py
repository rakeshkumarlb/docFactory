"""Where the configuration-based documents are stored: the ConfiguredDocuments table, keys `<App>.Configured.<DocType>[.<Part>]`."""
import json

from docfactory import db

TABLE = "ConfiguredDocuments"


def prefix(app_id: str, doc_type: str) -> str:
    """The key of the document body; its parts add '.DocumentControl', '.RevisionHistory' or '.MissingInfo'."""
    return f"{app_id}.Configured.{doc_type}"


def stored_row(key: str):
    """The stored ConfiguredDocuments row for `key`, or None."""
    return db.get_row(TABLE, key)


def stored_model(model, key: str):
    """The stored object for `key` validated as `model`, or None when there is no row."""
    row = stored_row(key)
    return model.model_validate(json.loads(row["Value"])) if row else None
