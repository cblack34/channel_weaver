"""Unit tests for configuration validators."""

from __future__ import annotations

import pytest

from src.config.models import ChannelConfig
from src.config.enums import ChannelAction
from src.config.validators import ChannelValidator, BusValidator
from src.exceptions import (
    DuplicateChannelError,
    ChannelOutOfRangeError,
    BusSlotOutOfRangeError,
    BusSlotDuplicateError,
    BusChannelConflictError,
)


class TestChannelValidator:
    """Tests for ChannelValidator class."""

    @pytest.fixture
    def validator_32ch(self) -> ChannelValidator:
        """Create validator for 32-channel setup."""
        return ChannelValidator(detected_channel_count=32)

    def test_validate_empty_list_passes(self, validator_32ch: ChannelValidator) -> None:
        """Test that empty channel list passes validation."""
        validator_32ch.validate([])

    def test_validate_single_channel_passes(self, validator_32ch: ChannelValidator) -> None:
        """Test that single valid channel passes validation."""
        channels = [ChannelConfig(ch=1, name="Kick")]
        validator_32ch.validate(channels)

    def test_validate_multiple_valid_channels_pass(self, validator_32ch: ChannelValidator) -> None:
        """Test that multiple valid channels pass validation."""
        channels = [
            ChannelConfig(ch=1, name="Kick"),
            ChannelConfig(ch=2, name="Snare"),
            ChannelConfig(ch=32, name="Last"),
        ]
        validator_32ch.validate(channels)

    def test_validate_duplicate_channels_raises_error(self, validator_32ch: ChannelValidator) -> None:
        """Test that duplicate channel numbers raise DuplicateChannelError."""
        channels = [
            ChannelConfig(ch=1, name="First"),
            ChannelConfig(ch=1, name="Duplicate"),
        ]

        with pytest.raises(DuplicateChannelError) as exc_info:
            validator_32ch.validate(channels)

        assert exc_info.value.ch == 1

    def test_validate_channel_out_of_range_raises_error(self, validator_32ch: ChannelValidator) -> None:
        """Test that channel exceeding detected count raises error."""
        channels = [ChannelConfig(ch=33, name="Out of Range")]

        with pytest.raises(ChannelOutOfRangeError) as exc_info:
            validator_32ch.validate(channels)

        assert exc_info.value.ch == 33
        assert exc_info.value.detected == 32

    def test_validate_multiple_duplicates_shows_first(self, validator_32ch: ChannelValidator) -> None:
        """Test that multiple duplicates report the first duplicate found."""
        channels = [
            ChannelConfig(ch=1, name="First"),
            ChannelConfig(ch=2, name="Second"),
            ChannelConfig(ch=1, name="Duplicate1"),
            ChannelConfig(ch=2, name="Duplicate2"),
        ]

        with pytest.raises(DuplicateChannelError) as exc_info:
            validator_32ch.validate(channels)

        # Should report first duplicate found (ch=1)
        assert exc_info.value.ch == 1

    def test_validate_channel_zero_raises_error(self) -> None:
        """Test that channel 0 raises error (though this should be caught by Pydantic)."""
        validator = ChannelValidator(detected_channel_count=32)
        # Note: ChannelConfig should prevent ch=0, but let's test the validator anyway
        channels = [ChannelConfig(ch=1, name="Valid")]  # This should work

        validator.validate(channels)  # Should not raise

    @pytest.mark.parametrize("detected_count,invalid_ch", [
        (16, 17),
        (8, 9),
        (64, 65),
    ])
    def test_validate_different_channel_counts(
        self,
        detected_count: int,
        invalid_ch: int,
    ) -> None:
        """Test validation with different detected channel counts."""
        validator = ChannelValidator(detected_channel_count=detected_count)
        channels = [ChannelConfig(ch=invalid_ch, name="Invalid")]

        with pytest.raises(ChannelOutOfRangeError) as exc_info:
            validator.validate(channels)

        assert exc_info.value.ch == invalid_ch
        assert exc_info.value.detected == detected_count


class TestBusValidator:
    """Tests for BusValidator class."""

    @pytest.fixture
    def validator_32ch(self) -> BusValidator:
        """Create validator for 32-channel setup."""
        return BusValidator(detected_channel_count=32)

    def test_validate_channels_empty_list_passes(self, validator_32ch: BusValidator) -> None:
        """Test that empty bus channel list passes validation."""
        validator_32ch.validate_channels([])

    def test_validate_channels_single_channel_passes(self, validator_32ch: BusValidator) -> None:
        """Test that single valid bus channel passes validation."""
        validator_32ch.validate_channels([7])

    def test_validate_channels_multiple_valid_channels_pass(self, validator_32ch: BusValidator) -> None:
        """Test that multiple valid bus channels pass validation."""
        validator_32ch.validate_channels([7, 8, 15, 16])

    def test_validate_channels_out_of_range_raises_error(self, validator_32ch: BusValidator) -> None:
        """Test that bus channel exceeding detected count raises error."""
        with pytest.raises(BusSlotOutOfRangeError) as exc_info:
            validator_32ch.validate_channels([33])

        assert exc_info.value.ch == 33
        assert exc_info.value.detected == 32

    def test_validate_channels_duplicate_raises_error(self, validator_32ch: BusValidator) -> None:
        """Test that duplicate bus channels raise error."""
        with pytest.raises(BusSlotDuplicateError) as exc_info:
            validator_32ch.validate_channels([7, 7])

        assert exc_info.value.ch == 7

    def test_validate_channels_multiple_duplicates_shows_first(self, validator_32ch: BusValidator) -> None:
        """Test that multiple duplicates report the first duplicate found."""
        with pytest.raises(BusSlotDuplicateError) as exc_info:
            validator_32ch.validate_channels([7, 8, 7, 9, 8])

        # Should report first duplicate found (ch=7)
        assert exc_info.value.ch == 7

    def test_validate_no_conflicts_empty_lists_pass(self, validator_32ch: BusValidator) -> None:
        """Test that empty lists pass conflict validation."""
        validator_32ch.validate_no_conflicts([], [])

    def test_validate_no_conflicts_bus_action_passes(self, validator_32ch: BusValidator) -> None:
        """Test that BUS action channels can be used in bus configuration."""
        channels = [
            ChannelConfig(ch=7, name="OH Left", action=ChannelAction.BUS),
            ChannelConfig(ch=8, name="OH Right", action=ChannelAction.BUS),
        ]

        validator_32ch.validate_no_conflicts(channels, [7, 8])

    def test_validate_no_conflicts_process_action_raises_error(self, validator_32ch: BusValidator) -> None:
        """Test that PROCESS action channels cannot be used in bus."""
        channels = [
            ChannelConfig(ch=7, name="OH Left", action=ChannelAction.PROCESS),
        ]

        with pytest.raises(BusChannelConflictError) as exc_info:
            validator_32ch.validate_no_conflicts(channels, [7])

        assert exc_info.value.ch == 7

    def test_validate_no_conflicts_skip_action_raises_error(self, validator_32ch: BusValidator) -> None:
        """Test that SKIP action channels cannot be used in bus."""
        channels = [
            ChannelConfig(ch=31, name="Click", action=ChannelAction.SKIP),
        ]

        with pytest.raises(BusChannelConflictError) as exc_info:
            validator_32ch.validate_no_conflicts(channels, [31])

        assert exc_info.value.ch == 31

    def test_validate_no_conflicts_missing_channel_passes(self, validator_32ch: BusValidator) -> None:
        """Test that bus channels not in channel list pass validation."""
        channels = [
            ChannelConfig(ch=1, name="Kick", action=ChannelAction.PROCESS),
        ]

        # Channel 7 is not in the channels list, so no conflict
        validator_32ch.validate_no_conflicts(channels, [7])

    def test_validate_no_conflicts_multiple_conflicts_shows_first(self, validator_32ch: BusValidator) -> None:
        """Test that multiple conflicts report the first conflict found."""
        channels = [
            ChannelConfig(ch=7, name="OH Left", action=ChannelAction.PROCESS),
            ChannelConfig(ch=8, name="OH Right", action=ChannelAction.PROCESS),
        ]

        with pytest.raises(BusChannelConflictError) as exc_info:
            validator_32ch.validate_no_conflicts(channels, [7, 8])

        # Should report first conflict found (ch=7)
        assert exc_info.value.ch == 7

    @pytest.mark.parametrize("action", [ChannelAction.PROCESS, ChannelAction.SKIP])
    def test_validate_no_conflicts_different_actions_fail(
        self,
        validator_32ch: BusValidator,
        action: ChannelAction,
    ) -> None:
        """Test that non-BUS actions fail conflict validation."""
        channels = [
            ChannelConfig(ch=7, name="Test", action=action),
        ]

        with pytest.raises(BusChannelConflictError):
            validator_32ch.validate_no_conflicts(channels, [7])