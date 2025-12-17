"""Configuration-related exceptions for Channel Weaver."""

from pydantic import ValidationError

from src.exceptions.base import ConfigError


class ConfigValidationError(ConfigError):
    """Raised when Pydantic validation fails for user data.

    This exception is raised when user-provided channel or bus configurations
    fail validation due to incorrect data types, missing required fields,
    or constraint violations defined in the Pydantic models.
    """

    def __init__(self, message: str, *, errors: ValidationError | None = None) -> None:
        super().__init__(message)
        self.errors = errors


class DuplicateChannelError(ConfigError):
    """Raised when channel numbers are defined more than once.

    This exception is raised during configuration loading when the same
    channel number appears multiple times in the user-defined channel list,
    violating the requirement for unique channel numbers.
    """

    def __init__(self, ch: int) -> None:
        super().__init__(f"Channel {ch} is defined multiple times; channel numbers must be unique.")
        self.ch = ch


class ChannelOutOfRangeError(ConfigError):
    """Raised when a channel number exceeds the detected channel count.

    This exception is raised when a user-defined channel configuration
    references a channel number that is higher than the number of channels
    detected in the input audio files.
    """

    def __init__(self, ch: int, detected: int) -> None:
        super().__init__(
            f"Channel {ch} is out of range for the detected input ({detected} channels)."
        )
        self.ch = ch
        self.detected = detected


class BusSlotOutOfRangeError(ConfigError):
    """Raised when a bus slot references a channel beyond the detected count.

    This exception is raised when a bus configuration assigns a channel
    number to a bus slot that exceeds the number of channels available
    in the input audio files.
    """

    def __init__(self, ch: int, detected: int) -> None:
        super().__init__(
            f"Bus slot references channel {ch}, which exceeds the detected input ({detected} channels)."
        )
        self.ch = ch
        self.detected = detected


class BusSlotDuplicateError(ConfigError):
    """Raised when the same channel is assigned to multiple bus slots.

    This exception is raised when multiple bus slots in the same bus
    configuration reference the same channel number, which would cause
    audio routing conflicts.
    """

    def __init__(self, ch: int) -> None:
        super().__init__(f"Channel {ch} is assigned to multiple bus slots; each slot must use a unique channel.")
        self.ch = ch


class BusChannelConflictError(ConfigError):
    """Raised when a bus-assigned channel is also marked for processing or skipping.

    This exception is raised when a channel is assigned to a bus slot but
    is also configured with an action of PROCESS or SKIP, creating a conflict
    in how the channel should be handled.
    """

    def __init__(self, ch: int) -> None:
        super().__init__(
            f"Channel {ch} is used in a bus but configured to PROCESS or SKIP. Set its action to BUS or remove it from buses."
        )
        self.ch = ch


class YAMLConfigError(ConfigValidationError):
    """Exception raised for YAML configuration file errors.
    
    This includes:
    - File not found
    - YAML parsing errors
    - Invalid structure (missing sections, wrong types)
    - Unsupported schema version
    """
    pass