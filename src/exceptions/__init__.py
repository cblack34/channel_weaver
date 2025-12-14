"""Exception hierarchy for Channel Weaver."""
from src.exceptions.base import ConfigError
from src.exceptions.config import (
    ConfigValidationError,
    DuplicateChannelError,
    ChannelOutOfRangeError,
    BusSlotOutOfRangeError,
    BusSlotDuplicateError,
    BusChannelConflictError,
    YAMLConfigError,
)
from src.exceptions.audio import AudioProcessingError

__all__ = [
    "ConfigError",
    "ConfigValidationError",
    "DuplicateChannelError",
    "ChannelOutOfRangeError",
    "BusSlotOutOfRangeError",
    "BusSlotDuplicateError",
    "BusChannelConflictError",
    "YAMLConfigError",
    "AudioProcessingError",
]