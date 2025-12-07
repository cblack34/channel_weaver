"""Configuration utilities for the Midas M32 processor CLI.

This module defines the user-facing channel/bus configuration schema and a
robust loader that validates, normalizes, and auto-fills channel definitions
based on a detected channel count.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Iterable
import warnings

from pydantic import BaseModel, Field, ValidationError, validator


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


class ChannelAction(Enum):
    """Possible actions that can be taken for a channel."""

    PROCESS = auto()
    BUS = auto()
    SKIP = auto()


class BusSlot(Enum):
    """Slot positions for stereo buses."""

    LEFT = auto()
    RIGHT = auto()


class BusType(Enum):
    """Supported bus types."""

    STEREO = auto()

    def required_slots(self) -> set[BusSlot]:
        """Return the set of slots required for this bus type."""

        if self is BusType.STEREO:
            return {BusSlot.LEFT, BusSlot.RIGHT}
        raise ValueError(f"Unsupported BusType: {self}")


class ChannelConfig(BaseModel):
    """User-editable channel configuration entry."""

    ch: int = Field(..., ge=1, description="Channel number (1-based)")
    name: str
    action: ChannelAction = ChannelAction.PROCESS

    @validator("action")
    def validate_action(cls, value: ChannelAction) -> ChannelAction:  # noqa: B902
        return value


class BusConfig(BaseModel):
    """User-editable bus configuration entry."""

    file_name: str = Field(..., description="Custom file name for output, e.g., '07_overheads'")
    type: BusType = BusType.STEREO
    slots: dict[BusSlot, int] = Field(..., description="Slot to channel mapping")

    @validator("slots")
    def validate_slots(cls, value: dict[BusSlot, int], values: dict[str, object]) -> dict[BusSlot, int]:  # noqa: B902
        bus_type = values.get("type", BusType.STEREO)
        if isinstance(bus_type, BusType):
            required = bus_type.required_slots()
            if set(value.keys()) != required:
                required_slots = ", ".join(slot.name for slot in sorted(required, key=lambda s: s.name))
                raise ValueError(f"{bus_type.name} buses require slots: {required_slots}")
        return value


class ConfigLoader:
    """Load and validate user-editable channel and bus definitions."""

    def __init__(
        self,
        channels_data: Iterable[dict[str, object]],
        buses_data: Iterable[dict[str, object]],
        *,
        detected_channel_count: int,
    ) -> None:
        self._channels_data = list(channels_data)
        self._buses_data = list(buses_data)
        self._detected_channels = detected_channel_count

    def load(self) -> tuple[list[ChannelConfig], list[BusConfig]]:
        """Return validated channel and bus configurations."""

        channels = self._load_channels()
        buses = self._load_buses()

        self._validate_channel_numbers(channels)
        bus_channels = self._collect_bus_channels(buses)
        self._validate_bus_channels(bus_channels)
        self._ensure_no_bus_conflicts(channels, bus_channels)

        completed_channels = self._complete_channel_list(channels, bus_channels)
        return completed_channels, buses

    def _load_channels(self) -> list[ChannelConfig]:
        try:
            return [ChannelConfig(**channel_dict) for channel_dict in self._channels_data]
        except ValidationError as exc:  # pragma: no cover - defensive
            raise ConfigValidationError("Invalid channel configuration.", errors=exc) from exc

    def _load_buses(self) -> list[BusConfig]:
        try:
            return [BusConfig(**bus_dict) for bus_dict in self._buses_data]
        except ValidationError as exc:  # pragma: no cover - defensive
            raise ConfigValidationError("Invalid bus configuration.", errors=exc) from exc

    def _validate_channel_numbers(self, channels: list[ChannelConfig]) -> None:
        seen: set[int] = set()
        for channel in channels:
            if channel.ch in seen:
                raise DuplicateChannelError(channel.ch)
            seen.add(channel.ch)
            if channel.ch > self._detected_channels:
                raise ChannelOutOfRangeError(channel.ch, self._detected_channels)

    def _collect_bus_channels(self, buses: list[BusConfig]) -> list[int]:
        channels: list[int] = []
        for bus in buses:
            channels.extend(bus.slots.values())
        return channels

    def _validate_bus_channels(self, bus_channels: list[int]) -> None:
        seen: set[int] = set()
        for ch in bus_channels:
            if ch > self._detected_channels:
                raise BusSlotOutOfRangeError(ch, self._detected_channels)
            if ch in seen:
                raise BusSlotDuplicateError(ch)
            seen.add(ch)

    def _ensure_no_bus_conflicts(self, channels: list[ChannelConfig], bus_channels: list[int]) -> None:
        channels_by_number = {channel.ch: channel for channel in channels}
        for ch in bus_channels:
            channel = channels_by_number.get(ch)
            if channel is not None and channel.action is not ChannelAction.BUS:
                raise BusChannelConflictError(ch)

    def _complete_channel_list(
        self, channels: list[ChannelConfig], bus_channels: list[int]
    ) -> list[ChannelConfig]:
        channels_by_number = {channel.ch: channel for channel in channels}

        for ch in bus_channels:
            if ch not in channels_by_number:
                warnings.warn(
                    f"Auto-creating channel {ch:02d} for bus assignment with action=BUS.",
                    stacklevel=2,
                )
                channels_by_number[ch] = ChannelConfig(ch=ch, name=f"Ch {ch:02d}", action=ChannelAction.BUS)

        for ch in range(1, self._detected_channels + 1):
            if ch not in channels_by_number:
                warnings.warn(
                    f"Auto-creating missing channel {ch:02d} with action=PROCESS.",
                    stacklevel=2,
                )
                channels_by_number[ch] = ChannelConfig(ch=ch, name=f"Ch {ch:02d}")

        return sorted(channels_by_number.values(), key=lambda config: config.ch)
