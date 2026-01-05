"""Unit tests for configuration enums.

Tests cover enum values, methods, and string representations.
"""

from __future__ import annotations

from src.config.enums import ChannelAction, BusSlot, BusType, BitDepth


class TestChannelAction:
    """Tests for ChannelAction enum."""

    def test_channel_action_values(self) -> None:
        """Test that ChannelAction has the expected values."""
        assert ChannelAction.PROCESS.value == 1
        assert ChannelAction.BUS.value == 2
        assert ChannelAction.SKIP.value == 3

    def test_channel_action_names(self) -> None:
        """Test that ChannelAction has the expected names."""
        assert ChannelAction.PROCESS.name == "PROCESS"
        assert ChannelAction.BUS.name == "BUS"
        assert ChannelAction.SKIP.name == "SKIP"

    def test_channel_action_members(self) -> None:
        """Test that all expected members exist."""
        expected_members = {"PROCESS", "BUS", "SKIP", "CLICK"}
        actual_members = {member.name for member in ChannelAction}
        assert actual_members == expected_members


class TestBusSlot:
    """Tests for BusSlot enum."""

    def test_bus_slot_values(self) -> None:
        """Test that BusSlot has the expected values."""
        assert BusSlot.LEFT.value == 1
        assert BusSlot.RIGHT.value == 2

    def test_bus_slot_names(self) -> None:
        """Test that BusSlot has the expected names."""
        assert BusSlot.LEFT.name == "LEFT"
        assert BusSlot.RIGHT.name == "RIGHT"

    def test_bus_slot_members(self) -> None:
        """Test that all expected members exist."""
        expected_members = {"LEFT", "RIGHT"}
        actual_members = {member.name for member in BusSlot}
        assert actual_members == expected_members


class TestBusType:
    """Tests for BusType enum."""

    def test_bus_type_values(self) -> None:
        """Test that BusType has the expected values."""
        assert BusType.STEREO.value == 1

    def test_bus_type_names(self) -> None:
        """Test that BusType has the expected names."""
        assert BusType.STEREO.name == "STEREO"

    def test_bus_type_members(self) -> None:
        """Test that all expected members exist."""
        expected_members = {"STEREO"}
        actual_members = {member.name for member in BusType}
        assert actual_members == expected_members

    def test_stereo_required_slots(self) -> None:
        """Test that STEREO bus type requires LEFT and RIGHT slots."""
        required = BusType.STEREO.required_slots()
        expected = {BusSlot.LEFT, BusSlot.RIGHT}
        assert required == expected


class TestBitDepth:
    """Tests for BitDepth enum."""

    def test_bit_depth_values(self) -> None:
        """Test that BitDepth has the expected string values."""
        assert BitDepth.SOURCE.value == "source"
        assert BitDepth.FLOAT32.value == "32float"
        assert BitDepth.INT24.value == "24"
        assert BitDepth.INT16.value == "16"

    def test_bit_depth_names(self) -> None:
        """Test that BitDepth has the expected names."""
        assert BitDepth.SOURCE.name == "SOURCE"
        assert BitDepth.FLOAT32.name == "FLOAT32"
        assert BitDepth.INT24.name == "INT24"
        assert BitDepth.INT16.name == "INT16"

    def test_bit_depth_members(self) -> None:
        """Test that all expected members exist."""
        expected_members = {"SOURCE", "FLOAT32", "INT24", "INT16"}
        actual_members = {member.name for member in BitDepth}
        assert actual_members == expected_members

    def test_bit_depth_string_representation(self) -> None:
        """Test that BitDepth instances convert to strings properly."""
        assert str(BitDepth.SOURCE) == "source"
        assert str(BitDepth.FLOAT32) == "32float"
        assert str(BitDepth.INT24) == "24"
        assert str(BitDepth.INT16) == "16"

    def test_bit_depth_is_str_enum(self) -> None:
        """Test that BitDepth is a string enum."""
        assert isinstance(BitDepth.SOURCE, str)
        assert isinstance(BitDepth.FLOAT32, str)
        assert isinstance(BitDepth.INT24, str)
        assert isinstance(BitDepth.INT16, str)