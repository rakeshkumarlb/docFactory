from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DataStore(DocFactoryModel):
    """One place where an application keeps data (e.g. a relational database, an object storage bucket, a file share)."""

    name: str = doc_field(
        description="Short name of the data store, e.g. 'Orders database'. Identifies the data store within the application.",
        question="What is the name of this data store?",
        min_length=1,
    )
    store_type: str = doc_field(
        default='',
        description="Kind of store, e.g. 'relational database', 'object storage', 'message queue', 'file share'. Leave empty when not yet known.",
        question="What type of data store is this?",
    )
    technology: str = doc_field(
        default='',
        description="Product and version of the store, e.g. 'PostgreSQL 16'. Leave empty when not yet known.",
        question="Which technology or product implements this data store?",
    )
    contents: str = doc_field(
        default='',
        description="What data the store holds, e.g. 'Customer orders and order line items.' A good value describes the data, not just the technology.",
        question="What data does this data store hold?",
    )
