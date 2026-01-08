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
from src.exceptions.click import (
    ClickChannelNotFoundError,
    ClickDetectionError,
    SectionProcessingError,
)

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
    "ClickChannelNotFoundError",
    "ClickDetectionError",
    "SectionProcessingError",
]