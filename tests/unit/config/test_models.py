"""Unit tests for Pydantic configuration models.

Tests cover ChannelConfig and BusConfig validation and field processing.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config.models import ChannelConfig, BusConfig
from src.config.enums import ChannelAction, BusSlot, BusType


class TestChannelConfig:
    """Tests for ChannelConfig Pydantic model."""

    def test_valid_channel_creation(self) -> None:
        """Test creating a valid ChannelConfig with minimum required fields."""
        config = ChannelConfig(ch=1, name="Kick In")

        assert config.ch == 1
        assert config.name == "Kick_In"  # Note: spaces replaced with underscores
        assert config.action == ChannelAction.PROCESS  # Default value
        assert config.output_ch == 1  # Defaults to ch

    def test_name_whitespace_cleaning(self) -> None:
        """Test that channel names have whitespace trimmed and spaces replaced."""
        config = ChannelConfig(ch=1, name="  Kick In  ")

        assert config.name == "Kick_In"

    @pytest.mark.parametrize("action_str,expected_enum", [
        ("PROCESS", ChannelAction.PROCESS),
        ("process", ChannelAction.PROCESS),
        ("BUS", ChannelAction.BUS),
        ("bus", ChannelAction.BUS),
        ("SKIP", ChannelAction.SKIP),
        ("skip", ChannelAction.SKIP),
    ])
    def test_action_string_conversion(
        self,
        action_str: str,
        expected_enum: ChannelAction,
    ) -> None:
        """Test that action strings are converted to ChannelAction enums."""
        config = ChannelConfig(ch=1, name="Test", action=action_str)

        assert config.action == expected_enum

    def test_invalid_channel_number_zero(self) -> None:
        """Test that channel number 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ChannelConfig(ch=0, name="Invalid")

        assert "ch" in str(exc_info.value)

    def test_invalid_channel_number_negative(self) -> None:
        """Test that negative channel numbers raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ChannelConfig(ch=-1, name="Invalid")

        assert "ch" in str(exc_info.value)

    def test_custom_output_channel(self) -> None:
        """Test setting a custom output channel number."""
        config = ChannelConfig(ch=5, name="Routed", output_ch=3)

        assert config.ch == 5
        assert config.output_ch == 3

    def test_invalid_output_channel_zero(self) -> None:
        """Test that output channel number 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ChannelConfig(ch=1, name="Test", output_ch=0)

        assert "output_ch" in str(exc_info.value)

    def test_invalid_action_raises_error(self) -> None:
        """Test that invalid action strings raise ValidationError."""
        with pytest.raises(ValidationError):
            ChannelConfig(ch=1, name="Test", action="INVALID")

    def test_action_enum_direct_assignment(self) -> None:
        """Test that ChannelAction enums can be assigned directly."""
        config = ChannelConfig(ch=1, name="Test", action=ChannelAction.BUS)

        assert config.action == ChannelAction.BUS


class TestBusConfig:
    """Tests for BusConfig Pydantic model."""

    def test_valid_stereo_bus_creation(self) -> None:
        """Test creating a valid stereo BusConfig."""
        config = BusConfig(
            file_name="07_Overheads",
            type=BusType.STEREO,
            slots={BusSlot.LEFT: 7, BusSlot.RIGHT: 8},
        )

        assert config.file_name == "07_Overheads"
        assert config.type == BusType.STEREO
        assert config.slots[BusSlot.LEFT] == 7
        assert config.slots[BusSlot.RIGHT] == 8

    def test_slots_string_key_conversion(self) -> None:
        """Test that string slot keys are converted to BusSlot enums."""
        config = BusConfig(
            file_name="test",
            type="STEREO",
            slots={"LEFT": 1, "RIGHT": 2},
        )

        assert BusSlot.LEFT in config.slots
        assert BusSlot.RIGHT in config.slots

    def test_type_string_conversion(self) -> None:
        """Test that string type values are converted to BusType enums."""
        config = BusConfig(
            file_name="test",
            type="STEREO",
            slots={BusSlot.LEFT: 1, BusSlot.RIGHT: 2},
        )

        assert config.type == BusType.STEREO

    def test_missing_left_slot_raises_error(self) -> None:
        """Test that missing LEFT slot raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={BusSlot.RIGHT: 2},
            )

        assert "LEFT" in str(exc_info.value) or "slots" in str(exc_info.value)

    def test_missing_right_slot_raises_error(self) -> None:
        """Test that missing RIGHT slot raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={BusSlot.LEFT: 1},
            )

        assert "RIGHT" in str(exc_info.value) or "slots" in str(exc_info.value)

    def test_slot_channel_validation_zero(self) -> None:
        """Test that slot channel numbers must be >= 1."""
        with pytest.raises(ValidationError):
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={BusSlot.LEFT: 0, BusSlot.RIGHT: 2},
            )

    def test_slot_channel_validation_negative(self) -> None:
        """Test that slot channel numbers must be >= 1."""
        with pytest.raises(ValidationError):
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={BusSlot.LEFT: -1, BusSlot.RIGHT: 2},
            )

    def test_invalid_slot_key_raises_error(self) -> None:
        """Test that invalid slot keys raise ValidationError."""
        with pytest.raises(ValidationError):
            BusConfig(
                file_name="test",
                type=BusType.STEREO,
                slots={"INVALID": 1, BusSlot.RIGHT: 2},
            )

    def test_invalid_type_raises_error(self) -> None:
        """Test that invalid type strings raise ValidationError."""
        with pytest.raises(ValidationError):
            BusConfig(
                file_name="test",
                type="INVALID",
                slots={BusSlot.LEFT: 1, BusSlot.RIGHT: 2},
            )

    def test_type_enum_direct_assignment(self) -> None:
        """Test that BusType enums can be assigned directly."""
        config = BusConfig(
            file_name="test",
            type=BusType.STEREO,
            slots={BusSlot.LEFT: 1, BusSlot.RIGHT: 2},
        )

        assert config.type == BusType.STEREO