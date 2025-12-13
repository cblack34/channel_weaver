"""Audio processing exceptions for Channel Weaver."""

from src.exceptions.base import ConfigError


class AudioProcessingError(ConfigError):
    """Raised when audio file operations fail during processing.

    This exception is raised for issues such as:
    - Missing or corrupted WAV files
    - Inconsistent audio parameters across files
    - File system errors during reading/writing
    - Unsupported audio formats or parameters
    """