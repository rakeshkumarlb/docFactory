class ChunksOutOfDateError(Exception):
    """Raised when an original no longer chunks the way it did at ingestion (the chunkers changed, or the file was altered on disk)."""
