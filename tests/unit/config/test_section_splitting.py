"""Unit tests for section splitting configuration models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config.models import SectionSplittingConfig
from src.config.enums import ChannelAction
from src.config.loader import ConfigLoader
from src.config.types import ChannelData, BusData
from src.exceptions import ConfigValidationError


class TestSectionSplittingConfig:
    """Tests for SectionSplittingConfig Pydantic model."""

    def test_default_config(self) -> None:
        """Test creating SectionSplittingConfig with defaults."""
        config = SectionSplittingConfig()

        assert config.enabled is False
        assert config.gap_threshold_seconds == 3.0
        assert config.min_section_length_seconds == 15.0
        assert config.bpm_change_threshold == 1

    def test_custom_config(self) -> None:
        """Test creating SectionSplittingConfig with custom values."""
        config = SectionSplittingConfig(
            enabled=True,
            gap_threshold_seconds=5.0,
            min_section_length_seconds=20.0,
            bpm_change_threshold=2,
        )

        assert config.enabled is True
        assert config.gap_threshold_seconds == 5.0
        assert config.min_section_length_seconds == 20.0
        assert config.bpm_change_threshold == 2

    @pytest.mark.parametrize("invalid_value", [0, -1, -0.5])
    def test_invalid_gap_threshold(self, invalid_value: float) -> None:
        """Test that gap_threshold_seconds must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            SectionSplittingConfig(gap_threshold_seconds=invalid_value)

        assert "gap_threshold_seconds" in str(exc_info.value)
        assert "greater_than" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_value", [0, -1, -0.5])
    def test_invalid_min_section_length(self, invalid_value: float) -> None:
        """Test that min_section_length_seconds must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            SectionSplittingConfig(min_section_length_seconds=invalid_value)

        assert "min_section_length_seconds" in str(exc_info.value)
        assert "greater_than" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_invalid_bpm_change_threshold(self, invalid_value: int) -> None:
        """Test that bpm_change_threshold must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            SectionSplittingConfig(bpm_change_threshold=invalid_value)

        assert "bpm_change_threshold" in str(exc_info.value)
        assert "greater_than_equal" in str(exc_info.value)

    def test_serialization(self) -> None:
        """Test that SectionSplittingConfig can be serialized to/from JSON."""
        config = SectionSplittingConfig(
            enabled=True,
            gap_threshold_seconds=5.0,
            min_section_length_seconds=20.0,
            bpm_change_threshold=2,
        )

        data = config.model_dump()
        assert data["enabled"] is True
        assert data["gap_threshold_seconds"] == 5.0
        assert data["min_section_length_seconds"] == 20.0
        assert data["bpm_change_threshold"] == 2

        # Test round-trip
        config2 = SectionSplittingConfig.model_validate(data)
        assert config2 == config


class TestClickChannelValidation:
    """Tests for click channel validation logic."""

    def test_click_channels_allowed_when_disabled(self) -> None:
        """Test that click channels are allowed even when section splitting is disabled."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Kick", "action": "PROCESS"},
            {"ch": 2, "name": "Snare", "action": "CLICK"},  # This should be allowed
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": False}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        
        # Should not raise an exception
        channels, buses, section_splitting = loader.load()
        
        # CLICK channel should be preserved (not converted to PROCESS)
        assert len(channels) == 2
        assert channels[1].action == ChannelAction.CLICK

    def test_multiple_click_channels_when_enabled(self) -> None:
        """Test that multiple click channels are not allowed when section splitting is enabled."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Kick", "action": "PROCESS"},
            {"ch": 2, "name": "Snare", "action": "CLICK"},
            {"ch": 3, "name": "Bass", "action": "CLICK"},  # This should fail
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)

        with pytest.raises(ConfigValidationError, match="multiple channels have action 'click'"):
            loader.load()

    def test_no_click_channels_when_enabled(self) -> None:
        """Test that at least one click channel is required when section splitting is enabled."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Kick", "action": "PROCESS"},
            {"ch": 2, "name": "Snare", "action": "PROCESS"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)

        with pytest.raises(ConfigValidationError, match="no channel has action 'click'"):
            loader.load()

    def test_valid_single_click_channel_when_enabled(self) -> None:
        """Test that a single click channel is allowed when section splitting is enabled."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Kick", "action": "PROCESS"},
            {"ch": 2, "name": "Snare", "action": "CLICK"},
            {"ch": 3, "name": "Bass", "action": "PROCESS"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": True}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        assert len(channels) == 3
        assert len([ch for ch in channels if ch.action == ChannelAction.CLICK]) == 1
        assert section_splitting.enabled is True

    def test_valid_no_click_channels_when_disabled(self) -> None:
        """Test that no click channels are allowed when section splitting is disabled."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Kick", "action": "PROCESS"},
            {"ch": 2, "name": "Snare", "action": "PROCESS"},
        ]
        buses_data: list[BusData] = []
        section_splitting_data = {"enabled": False}

        loader = ConfigLoader(channels_data, buses_data, section_splitting_data=section_splitting_data)
        channels, buses, section_splitting = loader.load()

        assert len(channels) == 2
        assert len([ch for ch in channels if ch.action == ChannelAction.CLICK]) == 0
        assert section_splitting.enabled is False

    def test_default_section_splitting_when_none_provided(self) -> None:
        """Test that default section splitting config is used when none provided."""
        channels_data: list[ChannelData] = [
            {"ch": 1, "name": "Kick", "action": "PROCESS"},
        ]
        buses_data: list[BusData] = []

        loader = ConfigLoader(channels_data, buses_data)
        channels, buses, section_splitting = loader.load()

        assert section_splitting.enabled is False
        assert section_splitting.gap_threshold_seconds == 3.0
        assert section_splitting.min_section_length_seconds == 15.0
        assert section_splitting.bpm_change_threshold == 1