"""Unit tests for track builder orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from src.config import ChannelConfig, BusConfig, BusSlot, ChannelAction, BitDepth
from src.processing.builder import TrackBuilder
from src.config import SegmentMap


class TestTrackBuilder:
    """Tests for TrackBuilder class."""

    @pytest.fixture
    def mock_converter(self, mocker: MockerFixture) -> MagicMock:
        """Create a mock bit depth converter."""
        return mocker.MagicMock()

    @pytest.fixture
    def mock_output_handler(self, mocker: MockerFixture) -> MagicMock:
        """Create a mock output handler."""
        return mocker.MagicMock()

    @pytest.fixture
    def mock_mono_writer(self, mocker: MockerFixture) -> MagicMock:
        """Create a mock mono track writer."""
        return mocker.MagicMock()

    @pytest.fixture
    def mock_stereo_writer(self, mocker: MockerFixture) -> MagicMock:
        """Create a mock stereo track writer."""
        return mocker.MagicMock()

    def test_init_resolves_bit_depth_source(
        self,
        mock_converter,
        mock_output_handler,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test initialization resolves SOURCE bit depth."""
        # Mock the factory functions
        mock_get_converter = mocker.patch("src.processing.builder.get_converter", return_value=mock_converter)
        mock_resolve_bit_depth = mocker.patch("src.processing.builder.resolve_bit_depth", return_value=BitDepth.INT24)

        # Mock the writer classes
        mock_mono_class = mocker.patch("src.processing.builder.MonoTrackWriter", return_value=MagicMock())
        mock_stereo_class = mocker.patch("src.processing.builder.StereoTrackWriter", return_value=MagicMock())

        TrackBuilder(
            sample_rate=44100,
            bit_depth=BitDepth.SOURCE,
            source_bit_depth=BitDepth.INT24,
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "output",
            keep_temp=False,
            output_handler=mock_output_handler,
        )

        # Verify bit depth resolution
        mock_resolve_bit_depth.assert_called_once_with(BitDepth.SOURCE, BitDepth.INT24)

        # Verify converter creation
        mock_get_converter.assert_called_once_with(BitDepth.INT24)

        # Verify writers were created with correct parameters
        mock_mono_class.assert_called_once_with(
            sample_rate=44100,
            converter=mock_converter,
            output_dir=tmp_path / "output",
            output_handler=mock_output_handler
        )
        mock_stereo_class.assert_called_once_with(
            sample_rate=44100,
            converter=mock_converter,
            output_dir=tmp_path / "output",
            output_handler=mock_output_handler
        )

    def test_init_without_output_handler_creates_default(
        self,
        mock_converter,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test initialization creates default output handler when none provided."""
        # Mock the factory functions
        mocker.patch("src.processing.builder.get_converter", return_value=mock_converter)
        mocker.patch("src.processing.builder.resolve_bit_depth", return_value=BitDepth.FLOAT32)

        # Mock the writer classes
        mocker.patch("src.processing.builder.MonoTrackWriter")
        mocker.patch("src.processing.builder.StereoTrackWriter")

        # Mock ConsoleOutputHandler
        mock_console_handler = mocker.MagicMock()
        mocker.patch("src.processing.builder.ConsoleOutputHandler", return_value=mock_console_handler)

        TrackBuilder(
            sample_rate=44100,
            bit_depth=BitDepth.FLOAT32,
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "output",
        )

        # Verify ConsoleOutputHandler was created
        from src.processing.builder import ConsoleOutputHandler
        ConsoleOutputHandler.assert_called_once()

    def test_init_creates_output_directory(
        self,
        mock_converter,
        mock_output_handler,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test initialization creates output directory."""
        # Mock the factory functions
        mocker.patch("src.processing.builder.get_converter", return_value=mock_converter)
        mocker.patch("src.processing.builder.resolve_bit_depth", return_value=BitDepth.INT16)

        # Mock the writer classes
        mocker.patch("src.processing.builder.MonoTrackWriter")
        mocker.patch("src.processing.builder.StereoTrackWriter")

        output_dir = tmp_path / "output"
        assert not output_dir.exists()

        TrackBuilder(
            sample_rate=44100,
            bit_depth=BitDepth.INT16,
            temp_dir=tmp_path / "temp",
            output_dir=output_dir,
            output_handler=mock_output_handler,
        )

        assert output_dir.exists()

    def test_build_tracks_orchestrates_writers(
        self,
        mock_converter,
        mock_output_handler,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test build_tracks calls both mono and stereo writers."""
        # Mock the factory functions
        mocker.patch("src.processing.builder.get_converter", return_value=mock_converter)
        mocker.patch("src.processing.builder.resolve_bit_depth", return_value=BitDepth.INT16)

        # Create mock writers
        mock_mono_writer = mocker.MagicMock()
        mock_stereo_writer = mocker.MagicMock()

        # Mock the writer classes to return our mocks
        mocker.patch("src.processing.builder.MonoTrackWriter", return_value=mock_mono_writer)
        mocker.patch("src.processing.builder.StereoTrackWriter", return_value=mock_stereo_writer)

        builder = TrackBuilder(
            sample_rate=44100,
            bit_depth=BitDepth.INT16,
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "output",
            output_handler=mock_output_handler,
        )

        # Test data
        channels = [
            ChannelConfig(ch=1, name="Kick", action=ChannelAction.PROCESS),
        ]
        buses = [
            BusConfig(file_name="drums", type="STEREO", slots={BusSlot.LEFT: 1, BusSlot.RIGHT: 2}),
        ]
        segments: SegmentMap = {1: [tmp_path / "seg1.wav"]}

        builder.build_tracks(channels, buses, segments)

        # Verify both writers were called
        mock_mono_writer.write_tracks.assert_called_once_with(channels, segments)
        mock_stereo_writer.write_tracks.assert_called_once_with(buses, segments)

        # Verify output message
        mock_output_handler.info.assert_called_once_with(f"Tracks written to {tmp_path / 'output'}")

    def test_build_tracks_with_empty_lists(
        self,
        mock_converter,
        mock_output_handler,
        tmp_path: Path,
        mocker: MockerFixture,
    ) -> None:
        """Test build_tracks handles empty channel and bus lists."""
        # Mock the factory functions
        mocker.patch("src.processing.builder.get_converter", return_value=mock_converter)
        mocker.patch("src.processing.builder.resolve_bit_depth", return_value=BitDepth.FLOAT32)

        # Create mock writers
        mock_mono_writer = mocker.MagicMock()
        mock_stereo_writer = mocker.MagicMock()

        # Mock the writer classes
        mocker.patch("src.processing.builder.MonoTrackWriter", return_value=mock_mono_writer)
        mocker.patch("src.processing.builder.StereoTrackWriter", return_value=mock_stereo_writer)

        builder = TrackBuilder(
            sample_rate=44100,
            bit_depth=BitDepth.FLOAT32,
            temp_dir=tmp_path / "temp",
            output_dir=tmp_path / "output",
            output_handler=mock_output_handler,
        )

        builder.build_tracks([], [], {})

        # Verify writers were called with empty lists
        mock_mono_writer.write_tracks.assert_called_once_with([], {})
        mock_stereo_writer.write_tracks.assert_called_once_with([], {})