"""Configuration loader for Channel Weaver."""

from typing import Iterable

from src.config.models import ChannelConfig, BusConfig, ChannelAction
from src.config.validators import ChannelValidator, BusValidator
from src.exceptions import ConfigValidationError
from src.types import ChannelData, BusData


class ConfigLoader:
    """Load and validate user-editable channel and bus definitions.

    This class processes raw configuration dictionaries into validated Pydantic models,
    performs cross-validation between channels and buses, and auto-fills missing channels
    based on detected audio channel count.

    Attributes:
        _channels_data: Raw channel configuration dictionaries
        _buses_data: Raw bus configuration dictionaries
        _detected_channels: Number of channels detected in input audio (optional)
        _channel_validator: Validator for channel configurations
        _bus_validator: Validator for bus configurations
    """

    def __init__(
            self,
            channels_data: Iterable[ChannelData],
            buses_data: Iterable[BusData],
            *,
            detected_channel_count: int | None = None,
            channel_validator: ChannelValidator | None = None,
            bus_validator: BusValidator | None = None,
    ) -> None:
        """Initialize the configuration loader.

        Args:
            channels_data: Iterable of raw channel configuration dictionaries
            buses_data: Iterable of raw bus configuration dictionaries
            detected_channel_count: Number of channels detected in input audio files
            channel_validator: Custom channel validator (uses default if None)
            bus_validator: Custom bus validator (uses default if None)
        """
        self._channels_data = list(channels_data)
        self._buses_data = list(buses_data)
        self._detected_channels = detected_channel_count
        # Use injected validators or create defaults
        self._channel_validator = channel_validator or (
            ChannelValidator(detected_channel_count) if detected_channel_count is not None else None
        )
        self._bus_validator = bus_validator or (
            BusValidator(detected_channel_count) if detected_channel_count is not None else None
        )

    def load(self) -> tuple[list[ChannelConfig], list[BusConfig]]:
        """Return validated channel and bus configurations.

        Processes raw configuration data through validation and normalization,
        ensuring all channels are accounted for and bus assignments are valid.

        Returns:
            Tuple of (channels, buses) where channels includes auto-created entries
            for any missing channels detected in the audio.

        Raises:
            ConfigValidationError: If channel or bus configuration is invalid
        """

        channels = self._load_channels()
        buses = self._load_buses()

        self._channel_validator.validate(channels)
        bus_channels = self._collect_bus_channels(buses)
        self._bus_validator.validate_channels(bus_channels)
        self._bus_validator.validate_no_conflicts(channels, bus_channels)

        completed_channels = self._complete_channel_list(channels, bus_channels)
        return completed_channels, buses

    def _load_channels(self) -> list[ChannelConfig]:
        """Load channel configurations from raw data.

        Returns:
            List of ChannelConfig objects parsed from raw dictionaries.

        Raises:
            ConfigValidationError: If channel data cannot be parsed
        """
        channels = []
        for data in self._channels_data:
            try:
                channel = ChannelConfig(**data)
                channels.append(channel)
            except Exception as e:
                raise ConfigValidationError(f"Invalid channel configuration: {data}") from e
        return channels

    def _load_buses(self) -> list[BusConfig]:
        """Load bus configurations from raw data.

        Returns:
            List of BusConfig objects parsed from raw dictionaries.

        Raises:
            ConfigValidationError: If bus data cannot be parsed
        """
        buses = []
        for data in self._buses_data:
            try:
                bus = BusConfig(**data)
                buses.append(bus)
            except Exception as e:
                raise ConfigValidationError(f"Invalid bus configuration: {data}") from e
        return buses

    def _collect_bus_channels(self, buses: list[BusConfig]) -> list[int]:
        """Extract all channel numbers used in bus configurations.

        Args:
            buses: List of bus configurations to analyze

        Returns:
            Sorted list of unique channel numbers used in bus slots
        """
        channels = set()
        for bus in buses:
            channels.update(bus.slots.values())
        return sorted(channels)

    def _complete_channel_list(
            self, channels: list[ChannelConfig], bus_channels: list[int]
    ) -> list[ChannelConfig]:
        """Complete channel list with auto-created entries for missing channels.

        Args:
            channels: Existing channel configurations
            bus_channels: Channel numbers referenced in bus configurations

        Returns:
            Complete list including auto-created channels for bus assignments
            and any missing channels up to detected_channel_count
        """
        if self._detected_channels is None:
            return channels

        # Create a dict of existing channels by number
        existing = {ch.ch: ch for ch in channels}

        # Add missing channels for bus assignments
        for ch_num in bus_channels:
            if ch_num not in existing:
                existing[ch_num] = ChannelConfig(
                    ch=ch_num,
                    name=f"Channel {ch_num}",
                    action=ChannelAction.BUS
                )

        # Add missing channels up to detected count
        for ch_num in range(1, self._detected_channels + 1):
            if ch_num not in existing:
                existing[ch_num] = ChannelConfig(
                    ch=ch_num,
                    name=f"Channel {ch_num}",
                    action=ChannelAction.PROCESS
                )

        # Return sorted by channel number
        return sorted(existing.values(), key=lambda ch: ch.ch)