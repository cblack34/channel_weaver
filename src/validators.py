"""Validation utilities for Channel Weaver configuration."""

from src.models import ChannelConfig, BusConfig, ChannelAction
from src.exceptions import (
    DuplicateChannelError, ChannelOutOfRangeError,
    BusSlotOutOfRangeError, BusSlotDuplicateError, BusChannelConflictError
)


class ChannelValidator:
    """Validates channel configuration against detected channel count."""

    def __init__(self, detected_channel_count: int) -> None:
        self._detected_channels = detected_channel_count

    def validate(self, channels: list[ChannelConfig]) -> None:
        """Validate channel numbers are unique and within range."""
        seen: set[int] = set()
        for channel in channels:
            if channel.ch in seen:
                raise DuplicateChannelError(channel.ch)
            seen.add(channel.ch)
            if channel.ch > self._detected_channels:
                raise ChannelOutOfRangeError(channel.ch, self._detected_channels)


class BusValidator:
    """Validates bus configuration against detected channel count."""

    def __init__(self, detected_channel_count: int) -> None:
        self._detected_channels = detected_channel_count

    def validate_channels(self, bus_channels: list[int]) -> None:
        """Validate bus channel numbers are within range and unique."""
        seen: set[int] = set()
        for ch in bus_channels:
            if ch > self._detected_channels:
                raise BusSlotOutOfRangeError(ch, self._detected_channels)
            if ch in seen:
                raise BusSlotDuplicateError(ch)
            seen.add(ch)

    def validate_no_conflicts(self, channels: list[ChannelConfig], bus_channels: list[int]) -> None:
        """Ensure no conflicts between channel actions and bus assignments."""
        channels_by_number = {channel.ch: channel for channel in channels}
        for ch in bus_channels:
            channel = channels_by_number.get(ch)
            if channel is not None and channel.action is not ChannelAction.BUS:
                raise BusChannelConflictError(ch)