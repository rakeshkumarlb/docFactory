class ApplyError(Exception):
    """A step of applying a type proposal failed; everything it changed has been rolled back."""
