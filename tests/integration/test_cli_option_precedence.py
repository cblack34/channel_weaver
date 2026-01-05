"""Integration tests for CLI option precedence and merging."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.enums import ChannelAction
from src.config.loader import ConfigLoader
from src.config.models import ProcessingOptions
from src.config.types import ChannelData, BusData
from src.exceptions import ConfigValidationError


class TestProcessingOptionsMerging:
    """Tests for merging CLI options with config values."""

    def test_section_by_click_overrides_config_disabled(self) -> None:
        """Test that --section-by-click flag overrides config enabled=false."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Click", "action": "CLICK"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True}  # Must be enabled when CLICK channels present

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        # Initially enabled
        assert section_splitting.enabled is True

        # Test that setting section_by_click=True keeps it enabled
        options = ProcessingOptions(section_by_click=True)
        channels, buses, section_splitting = loader.merge_processing_options(
            channels, buses, section_splitting, options
        )

        assert section_splitting.enabled is True

    def test_section_by_click_false_preserves_config_enabled(self) -> None:
        """Test that --section-by-click=false preserves config enabled=true."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Click", "action": "CLICK"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        # Initially enabled
        assert section_splitting.enabled is True

        # CLI option doesn't change it (false = no override)
        options = ProcessingOptions(section_by_click=False)
        channels, buses, section_splitting = loader.merge_processing_options(
            channels, buses, section_splitting, options
        )

        # Should remain enabled from config
        assert section_splitting.enabled is True

    def test_gap_threshold_overrides_config_value(self) -> None:
        """Test that --gap-threshold overrides config value."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Click", "action": "CLICK"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True, "gap_threshold_seconds": 3.0}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        # Initially 3.0 from config
        assert section_splitting.gap_threshold_seconds == 3.0

        # CLI option overrides to 5.0
        options = ProcessingOptions(gap_threshold_seconds=5.0)
        channels, buses, section_splitting = loader.merge_processing_options(
            channels, buses, section_splitting, options
        )

        assert section_splitting.gap_threshold_seconds == 5.0

    def test_gap_threshold_none_preserves_config_value(self) -> None:
        """Test that gap_threshold=None preserves config value."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Click", "action": "CLICK"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True, "gap_threshold_seconds": 2.5}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        # Initially 2.5 from config
        assert section_splitting.gap_threshold_seconds == 2.5

        # CLI option is None (no override)
        options = ProcessingOptions(gap_threshold_seconds=None)
        channels, buses, section_splitting = loader.merge_processing_options(
            channels, buses, section_splitting, options
        )

        # Should remain 2.5 from config
        assert section_splitting.gap_threshold_seconds == 2.5

    def test_merge_validates_click_channel_constraints(self) -> None:
        """Test that merge_processing_options validates click channel constraints."""
        # No click channels but trying to enable section splitting
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Bass", "action": "PROCESS"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": False}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        # Try to enable via CLI without a click channel
        options = ProcessingOptions(section_by_click=True)

        with pytest.raises(ConfigValidationError, match="--section-by-click specified but no channel named 'Click' found"):
            loader.merge_processing_options(channels, buses, section_splitting, options)

    def test_merge_enables_section_splitting_with_click_channel(self) -> None:
        """Test that --section-by-click enables splitting when a 'Click' channel exists."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Click", "action": "PROCESS"},  # Initially PROCESS
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": False}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        # Enable via CLI with a 'Click' channel present
        options = ProcessingOptions(section_by_click=True)

        merged_channels, merged_buses, merged_section_splitting = loader.merge_processing_options(
            channels, buses, section_splitting, options
        )

        # Should be enabled
        assert merged_section_splitting.enabled is True
        # Click channel should be changed to CLICK action
        click_channel = next(ch for ch in merged_channels if ch.name == "Click")
        assert click_channel.action == ChannelAction.CLICK

    def test_merge_with_all_options(self) -> None:
        """Test merging with all options specified."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Click", "action": "CLICK"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {
            "enabled": True,  # Must be enabled when CLICK channels present
            "gap_threshold_seconds": 3.0,
            "min_section_length_seconds": 15.0,
        }

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        # Apply all CLI options
        json_path = Path("/output/session.json")
        options = ProcessingOptions(
            section_by_click=True,
            gap_threshold_seconds=4.5,
            session_json_path=json_path,
        )
        channels, buses, section_splitting = loader.merge_processing_options(
            channels, buses, section_splitting, options
        )

        # Verify overrides applied
        assert section_splitting.enabled is True
        assert section_splitting.gap_threshold_seconds == 4.5
        # Min section length should remain from config (not overridden)
        assert section_splitting.min_section_length_seconds == 15.0

    def test_merge_with_default_options(self) -> None:
        """Test merging with default ProcessingOptions (no overrides)."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Audio", "action": "PROCESS"},
            {"ch": 2, "name": "Click", "action": "CLICK"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True, "gap_threshold_seconds": 2.0}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        original_enabled = section_splitting.enabled
        original_gap = section_splitting.gap_threshold_seconds

        # Merge with default options (all None/False)
        options = ProcessingOptions()
        channels, buses, section_splitting = loader.merge_processing_options(
            channels, buses, section_splitting, options
        )

        # Nothing should change
        assert section_splitting.enabled == original_enabled
        assert section_splitting.gap_threshold_seconds == original_gap
