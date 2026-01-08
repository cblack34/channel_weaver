"""Click track analysis specific exceptions."""


class ClickChannelNotFoundError(Exception):
    """Raised when no click channel is defined in configuration but section splitting is enabled."""

    def __init__(self, message="No click channel defined"):
        super().__init__(message)


class ClickDetectionError(Exception):
    """Raised when click track analysis fails to detect valid onsets."""

    def __init__(self, message="Click detection failed"):
        super().__init__(message)


class SectionProcessingError(Exception):
    """Raised when section processing encounters an error."""

    def __init__(self, message="Section processing failed"):
        super().__init__(message)

