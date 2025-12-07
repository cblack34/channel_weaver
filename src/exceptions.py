"""Custom exceptions for Channel Weaver."""

from pydantic import ValidationError


class ConfigError(Exception):
    """Base class for user-facing configuration errors."""


class ConfigValidationError(ConfigError):
    """Raised when Pydantic validation fails for user data."""

    def __init__(self, message: str, *, errors: ValidationError | None = None) -> None:
        super().__init__(message)
        self.errors = errors


class DuplicateChannelError(ConfigError):
    """Raised when channel numbers are defined more than once."""

    def __init__(self, ch: int) -> None:
        super().__init__(f"Channel {ch} is defined multiple times; channel numbers must be unique.")
        self.ch = ch


class ChannelOutOfRangeError(ConfigError):
    """Raised when a channel number exceeds the detected channel count."""

    def __init__(self, ch: int, detected: int) -> None:
        super().__init__(
            f"Channel {ch} is out of range for the detected input ({detected} channels)."
        )
        self.ch = ch
        self.detected = detected


class BusSlotOutOfRangeError(ConfigError):
    """Raised when a bus slot references a channel beyond the detected count."""

    def __init__(self, ch: int, detected: int) -> None:
        super().__init__(
            f"Bus slot references channel {ch}, which exceeds the detected input ({detected} channels)."
        )
        self.ch = ch
        self.detected = detected


class BusSlotDuplicateError(ConfigError):
    """Raised when the same channel is assigned to multiple bus slots."""

    def __init__(self, ch: int) -> None:
        super().__init__(f"Channel {ch} is assigned to multiple bus slots; each slot must use a unique channel.")
        self.ch = ch


class BusChannelConflictError(ConfigError):
    """Raised when a bus-assigned channel is also marked for processing or skipping."""

    def __init__(self, ch: int) -> None:
        super().__init__(
            f"Channel {ch} is used in a bus but configured to PROCESS or SKIP. Set its action to BUS or remove it from buses."
        )
        self.ch = ch