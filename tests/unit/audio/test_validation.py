"""Unit tests for audio file validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.audio.validation import AudioValidator
from src.config.enums import BitDepth
from src.exceptions import AudioProcessingError


class TestAudioValidator:
    """Tests for AudioValidator class."""

    @pytest.fixture
    def validator(self) -> AudioValidator:
        """Create AudioValidator instance."""
        return AudioValidator()

    def test_validate_empty_file_list_raises_error(self, validator: AudioValidator) -> None:
        """Test that empty file list raises AudioProcessingError."""
        with pytest.raises(AudioProcessingError, match="No files to validate"):
            validator.validate_files([])

    def test_validate_nonexistent_file_raises_error(
        self,
        validator: AudioValidator,
        tmp_path: Path,
    ) -> None:
        """Test that nonexistent file raises AudioProcessingError."""
        fake_path = tmp_path / "nonexistent.wav"

        with pytest.raises(AudioProcessingError, match="does not exist"):
            validator.validate_files([fake_path])

    def test_validate_empty_file_raises_error(
        self,
        validator: AudioValidator,
        tmp_path: Path,
    ) -> None:
        """Test that empty file raises AudioProcessingError."""
        empty_file = tmp_path / "empty.wav"
        empty_file.write_bytes(b"")

        with pytest.raises(AudioProcessingError, match="is empty"):
            validator.validate_files([empty_file])

    def test_validate_consistent_files_succeeds(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test that consistent audio files pass validation."""
        # Create mock files
        file1 = tmp_path / "file1.wav"
        file2 = tmp_path / "file2.wav"
        file1.write_bytes(b"\x00" * 100)
        file2.write_bytes(b"\x00" * 100)

        # Mock AudioInfoRetriever.get_info method
        mock_info = mocker.MagicMock()
        mock_info.samplerate = 48000
        mock_info.channels = 32
        mock_info.subtype = "PCM_24"

        mocker.patch.object(validator.info_retriever, "get_info", return_value=mock_info)

        # Mock tqdm to return the files list (avoid progress bar output)
        mocker.patch("src.audio.validation.tqdm", return_value=[file1, file2])

        # Should not raise
        rate, channels, bit_depth = validator.validate_files([file1, file2])

        assert rate == 48000
        assert channels == 32
        assert bit_depth == BitDepth.INT24

        # Verify get_info was called for each file
        assert validator.info_retriever.get_info.call_count == 2  # type: ignore[attr-defined]

    def test_validate_sample_rate_mismatch_raises_error(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test that sample rate mismatch raises AudioProcessingError."""
        file1 = tmp_path / "file1.wav"
        file2 = tmp_path / "file2.wav"
        file1.write_bytes(b"\x00" * 100)
        file2.write_bytes(b"\x00" * 100)

        # Mock different sample rates
        mock_info1 = mocker.MagicMock()
        mock_info1.samplerate = 48000
        mock_info1.channels = 32
        mock_info1.subtype = "PCM_24"

        mock_info2 = mocker.MagicMock()
        mock_info2.samplerate = 44100  # Different!
        mock_info2.channels = 32
        mock_info2.subtype = "PCM_24"

        mocker.patch.object(validator.info_retriever, "get_info", side_effect=[mock_info1, mock_info2])

        mocker.patch("src.audio.validation.tqdm", return_value=[file1, file2])

        with pytest.raises(AudioProcessingError, match="Sample rate mismatch"):
            validator.validate_files([file1, file2])

    def test_validate_channel_count_mismatch_raises_error(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test that channel count mismatch raises AudioProcessingError."""
        file1 = tmp_path / "file1.wav"
        file2 = tmp_path / "file2.wav"
        file1.write_bytes(b"\x00" * 100)
        file2.write_bytes(b"\x00" * 100)

        # Mock different channel counts
        mock_info1 = mocker.MagicMock()
        mock_info1.samplerate = 48000
        mock_info1.channels = 32
        mock_info1.subtype = "PCM_24"

        mock_info2 = mocker.MagicMock()
        mock_info2.samplerate = 48000
        mock_info2.channels = 16  # Different!
        mock_info2.subtype = "PCM_24"

        mocker.patch.object(validator.info_retriever, "get_info", side_effect=[mock_info1, mock_info2])

        mocker.patch("src.audio.validation.tqdm", return_value=[file1, file2])

        with pytest.raises(AudioProcessingError, match="Channel count mismatch"):
            validator.validate_files([file1, file2])

    def test_validate_bit_depth_mismatch_raises_error(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test that bit depth mismatch raises AudioProcessingError."""
        file1 = tmp_path / "file1.wav"
        file2 = tmp_path / "file2.wav"
        file1.write_bytes(b"\x00" * 100)
        file2.write_bytes(b"\x00" * 100)

        # Mock different subtypes
        mock_info1 = mocker.MagicMock()
        mock_info1.samplerate = 48000
        mock_info1.channels = 32
        mock_info1.subtype = "PCM_24"

        mock_info2 = mocker.MagicMock()
        mock_info2.samplerate = 48000
        mock_info2.channels = 32
        mock_info2.subtype = "PCM_16"  # Different!

        mocker.patch.object(validator.info_retriever, "get_info", side_effect=[mock_info1, mock_info2])

        mocker.patch("src.audio.validation.tqdm", return_value=[file1, file2])

        with pytest.raises(AudioProcessingError, match="Bit depth mismatch"):
            validator.validate_files([file1, file2])

    @pytest.mark.parametrize("subtype,expected_depth", [
        ("PCM_16", BitDepth.INT16),
        ("PCM_24", BitDepth.INT24),
        ("PCM_32", BitDepth.SOURCE),
        ("FLOAT", BitDepth.FLOAT32),
        ("DOUBLE", BitDepth.FLOAT32),
        ("pcm_16", BitDepth.INT16),  # Test case insensitivity
        ("unknown", BitDepth.FLOAT32),  # Test default fallback
    ])
    def test_bit_depth_conversion(
        self,
        validator: AudioValidator,
        subtype: str,
        expected_depth: BitDepth,
    ) -> None:
        """Test conversion from soundfile subtype to BitDepth enum."""
        result = validator._bit_depth_from_subtype(subtype)

        assert result == expected_depth

    def test_validate_single_file_succeeds(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test validation with single file works correctly."""
        file1 = tmp_path / "file1.wav"
        file1.write_bytes(b"\x00" * 100)

        mock_info = mocker.MagicMock()
        mock_info.samplerate = 44100
        mock_info.channels = 2
        mock_info.subtype = "FLOAT"

        mocker.patch.object(validator.info_retriever, "get_info", return_value=mock_info)

        mocker.patch("src.audio.validation.tqdm", return_value=[file1])

        rate, channels, bit_depth = validator.validate_files([file1])

        assert rate == 44100
        assert channels == 2
        assert bit_depth == BitDepth.FLOAT32

    def test_validate_multiple_consistent_files(
        self,
        validator: AudioValidator,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test validation with multiple consistent files."""
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.wav"
            f.write_bytes(b"\x00" * 100)
            files.append(f)

        mock_info = mocker.MagicMock()
        mock_info.samplerate = 96000
        mock_info.channels = 64
        mock_info.subtype = "PCM_32"

        mocker.patch.object(validator.info_retriever, "get_info", return_value=mock_info)

        mocker.patch("src.audio.validation.tqdm", return_value=files)

        rate, channels, bit_depth = validator.validate_files(files)

        assert rate == 96000
        assert channels == 64
        assert bit_depth == BitDepth.SOURCE

        # Verify get_info was called for each file
        assert validator.info_retriever.get_info.call_count == 3  # type: ignore[attr-defined]