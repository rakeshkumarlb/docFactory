class BundleError(Exception):
    """Raised when a file of the bundle cannot be trusted: it is not a fact file, its JSON no longer validates, or its hash no longer matches the JSON (it was edited by hand)."""
