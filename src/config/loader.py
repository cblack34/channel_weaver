"""Configuration loader for Channel Weaver."""

from pathlib import Path
from typing import Any, Iterable

from src.config.models import ChannelConfig, BusConfig, SectionSplittingConfig, ProcessingOptions
from src.config.validators import ChannelValidator, BusValidator
from src.config.protocols import ConfigSource
from src.exceptions import ConfigValidationError
from src.config.types import ChannelData, BusData
from src.config.enums import ChannelAction


class ConfigLoader:
    """Load and validate user-editable channel and bus definitions.

    This class processes raw configuration dictionaries into validated Pydantic models,
    performs cross-validation between channels and buses, and auto-fills missing channels
    based on detected audio channel count.

    Attributes:
        _channels_data: Raw channel configuration dictionaries
        _buses_data: Raw bus configuration dictionaries
        _section_splitting_data: Raw section splitting configuration dictionary
        _detected_channels: Number of channels detected in input audio (optional)
        _channel_validator: Validator for channel configurations
        _bus_validator: Validator for bus configurations
    """

    def __init__(
            self,
            channels_data: Iterable[ChannelData],
            buses_data: Iterable[BusData],
            *,
            section_splitting_data: dict[str, Any] | None = None,
            detected_channel_count: int | None = None,
            channel_validator: ChannelValidator | None = None,
            bus_validator: BusValidator | None = None,
    ) -> None:
        """Initialize the configuration loader.

        Args:
            channels_data: Iterable of raw channel configuration dictionaries
            buses_data: Iterable of raw bus configuration dictionaries
            section_splitting_data: Raw section splitting configuration dictionary
            detected_channel_count: Number of channels detected in input audio files
            channel_validator: Custom channel validator (uses default if None)
            bus_validator: Custom bus validator (uses default if None)
        """
        self._channels_data = list(channels_data)
        self._buses_data = list(buses_data)
        self._section_splitting_data = section_splitting_data
        self._detected_channels = detected_channel_count
        # Use injected validators or create defaults
        self._channel_validator = channel_validator or (
            ChannelValidator(detected_channel_count) if detected_channel_count is not None else None
        )
        self._bus_validator = bus_validator or (
            BusValidator(detected_channel_count) if detected_channel_count is not None else None
        )

    @classmethod
    def from_source(
        cls,
        source: ConfigSource,
        *,
        detected_channel_count: int | None = None,
        channel_validator: ChannelValidator | None = None,
        bus_validator: BusValidator | None = None,
    ) -> "ConfigLoader":
        """Create a ConfigLoader from any ConfigSource implementation.

        This factory method follows the Dependency Inversion Principle,
        accepting any implementation of the ConfigSource protocol.

        Args:
            source: Configuration source implementing ConfigSource protocol
            detected_channel_count: Number of channels detected in input audio
            channel_validator: Custom channel validator (uses default if None)
            bus_validator: Custom bus validator (uses default if None)

        Returns:
            ConfigLoader instance initialized from the source
        """
        channels_data, buses_data, section_splitting_data, schema_version = source.load()

        return cls(
            channels_data=channels_data,  # type: ignore[arg-type]
            buses_data=buses_data,  # type: ignore[arg-type]
            section_splitting_data=section_splitting_data,
            detected_channel_count=detected_channel_count,
            channel_validator=channel_validator,
            bus_validator=bus_validator,
        )

    @classmethod
    def from_yaml(
        cls,
        config_path: Path,
        *,
        detected_channel_count: int | None = None,
        channel_validator: ChannelValidator | None = None,
        bus_validator: BusValidator | None = None,
    ) -> "ConfigLoader":
        """Create a ConfigLoader from a YAML configuration file.

        Convenience method that creates a YAMLConfigSource and delegates
        to from_source().

        Args:
            config_path: Path to the YAML configuration file
            detected_channel_count: Number of channels detected in input audio
            channel_validator: Custom channel validator (uses default if None)
            bus_validator: Custom bus validator (uses default if None)

        Returns:
            ConfigLoader instance initialized with YAML configuration
        """
        from src.config.yaml_source import YAMLConfigSource
        source = YAMLConfigSource(config_path)
        return cls.from_source(
            source,
            detected_channel_count=detected_channel_count,
            channel_validator=channel_validator,
            bus_validator=bus_validator,
        )

    def load(self) -> tuple[list[ChannelConfig], list[BusConfig], SectionSplittingConfig]:
        """Return validated channel, bus, and section splitting configurations.

        Processes raw configuration data through validation and normalization,
        ensuring all channels are accounted for and bus assignments are valid.

        Returns:
            Tuple of (channels, buses, section_splitting) where channels includes auto-created entries
            for any missing channels detected in the audio.

        Raises:
            ConfigValidationError: If channel or bus configuration is invalid
        """

        channels = self._load_channels()
        buses = self._load_buses()
        section_splitting = self._load_section_splitting()

        if self._channel_validator:
            self._channel_validator.validate(channels)
        bus_channels = self._collect_bus_channels(buses)
        if self._bus_validator:
            self._bus_validator.validate_channels(bus_channels)
            self._bus_validator.validate_no_conflicts(channels, bus_channels)

        # Validate click channel constraints
        self._validate_click_channel_constraints(channels, section_splitting)

        completed_channels = self._complete_channel_list(channels, bus_channels)
        return completed_channels, buses, section_splitting

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
                channel = ChannelConfig(**data)  # type: ignore[arg-type]
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
                bus = BusConfig(**data)  # type: ignore[arg-type]
                buses.append(bus)
            except Exception as e:
                raise ConfigValidationError(f"Invalid bus configuration: {data}") from e
        return buses

    def _load_section_splitting(self) -> SectionSplittingConfig:
        """Load section splitting configuration from raw data.

        Returns:
            SectionSplittingConfig object, using defaults if no data provided.

        Raises:
            ConfigValidationError: If section splitting data cannot be parsed
        """
        if self._section_splitting_data is None:
            return SectionSplittingConfig()
        try:
            return SectionSplittingConfig(**self._section_splitting_data)
        except Exception as e:
            raise ConfigValidationError(f"Invalid section splitting configuration: {self._section_splitting_data}") from e

    def _validate_click_channel_constraints(self, channels: list[ChannelConfig], section_splitting: SectionSplittingConfig) -> None:
        """Validate constraints related to click channels and section splitting.

        Args:
            channels: List of channel configurations
            section_splitting: Section splitting configuration

        Raises:
            ConfigValidationError: If constraints are violated
        """
        click_channels = [ch for ch in channels if ch.action == ChannelAction.CLICK]

        if section_splitting.enabled:
            if len(click_channels) == 0:
                raise ConfigValidationError(
                    "Section splitting is enabled but no channel has action 'click'"
                )
            if len(click_channels) > 1:
                raise ConfigValidationError(
                    f"Section splitting is enabled but multiple channels have action 'click': {[ch.ch for ch in click_channels]}"
                )
        else:
            # Convert CLICK channels to PROCESS when section splitting is disabled
            for ch in click_channels:
                ch.action = ChannelAction.PROCESS

    def _collect_bus_channels(self, buses: list[BusConfig]) -> list[int]:
        """Extract all channel numbers used in bus configurations.

        Args:
            buses: List of bus configurations to analyze

        Returns:
            Sorted list of unique channel numbers used in bus slots
        """
        channels: set[int] = set()
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
                    action=ChannelAction.BUS,
                    output_ch=None
                )

        # Add missing channels up to detected count
        for ch_num in range(1, self._detected_channels + 1):
            if ch_num not in existing:
                existing[ch_num] = ChannelConfig(
                    ch=ch_num,
                    name=f"Channel {ch_num}",
                    action=ChannelAction.PROCESS,
                    output_ch=None
                )

        # Return sorted by channel number
        return sorted(existing.values(), key=lambda ch: ch.ch)

    def merge_processing_options(
        self,
        channels: list[ChannelConfig],
        buses: list[BusConfig],
        section_splitting: SectionSplittingConfig,
        options: ProcessingOptions,
    ) -> tuple[list[ChannelConfig], list[BusConfig], SectionSplittingConfig]:
        """Merge CLI processing options with loaded configuration.

        CLI options take precedence over configuration file values.

        Args:
            channels: Loaded channel configurations
            buses: Loaded bus configurations
            section_splitting: Loaded section splitting configuration
            options: CLI processing options

        Returns:
            Tuple of (channels, buses, section_splitting) with CLI options applied
        """
        # Handle section_by_click option
        if options.section_by_click:
            # Check if there's already a CLICK channel
            click_channel_exists = any(channel.action == ChannelAction.CLICK for channel in channels)
            if not click_channel_exists:
                # Look for a channel named "Click" (case-insensitive) with PROCESS action
                click_channel_found = False
                for channel in channels:
                    if channel.name.lower() == "click" and channel.action == ChannelAction.PROCESS:
                        channel.action = ChannelAction.CLICK
                        click_channel_found = True
                        break
                if not click_channel_found:
                    raise ConfigValidationError(
                        "--section-by-click specified but no channel named 'Click' found to use as click track"
                    )
            section_splitting.enabled = True

        # Override gap threshold if provided
        if options.gap_threshold_seconds is not None:
            section_splitting.gap_threshold_seconds = options.gap_threshold_seconds

        # Validate click channel constraints after applying CLI options
        self._validate_click_channel_constraints(channels, section_splitting)

        return channels, buses, section_splitting