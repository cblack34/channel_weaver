"""Unit tests for audio file discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.audio.discovery import AudioFileDiscovery


class TestAudioFileDiscovery:
    """Tests for AudioFileDiscovery class."""

    @pytest.fixture
    def discovery(self, tmp_input_dir: Path) -> AudioFileDiscovery:
        """Create AudioFileDiscovery instance with temp directory."""
        return AudioFileDiscovery(tmp_input_dir)

    def test_discover_empty_directory(self, discovery: AudioFileDiscovery) -> None:
        """Test discovery returns empty list for empty directory."""
        files = discovery.discover_files()

        assert files == []

    def test_discover_single_wav_file(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test discovery finds single WAV file."""
        wav_file = tmp_input_dir / "00000001.WAV"
        wav_file.write_bytes(b"\x00" * 100)

        files = discovery.discover_files()

        assert len(files) == 1
        assert files[0] == wav_file

    def test_discover_multiple_files_sorted(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test discovery returns files in numeric order."""
        # Create files in non-sequential order
        (tmp_input_dir / "00000003.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "00000002.WAV").write_bytes(b"\x00")

        files = discovery.discover_files()

        assert len(files) == 3
        assert files[0].name == "00000001.WAV"
        assert files[1].name == "00000002.WAV"
        assert files[2].name == "00000003.WAV"

    def test_discover_case_insensitive_extensions(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test discovery finds both .wav and .WAV extensions."""
        (tmp_input_dir / "file1.wav").write_bytes(b"\x00")
        (tmp_input_dir / "file2.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "file3.Wav").write_bytes(b"\x00")

        files = discovery.discover_files()

        assert len(files) == 3
        # Should be sorted by the _sort_key method
        file_names = [f.name for f in files]
        assert "file1.wav" in file_names
        assert "file2.WAV" in file_names
        assert "file3.Wav" in file_names

    def test_discover_non_wav_files_ignored(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test that non-WAV files are ignored."""
        (tmp_input_dir / "readme.txt").write_bytes(b"\x00")
        (tmp_input_dir / "audio.mp3").write_bytes(b"\x00")
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00")

        files = discovery.discover_files()

        assert len(files) == 1
        assert files[0].name == "00000001.WAV"

    def test_discover_files_without_numbers(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test discovery handles files without numbers (sorted to end)."""
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "no_numbers.wav").write_bytes(b"\x00")
        (tmp_input_dir / "another_no_num.WAV").write_bytes(b"\x00")

        files = discovery.discover_files()

        assert len(files) == 3
        assert files[0].name == "00000001.WAV"
        # Files without numbers should come after numbered ones
        assert files[1].name in ["no_numbers.wav", "another_no_num.WAV"]
        assert files[2].name in ["no_numbers.wav", "another_no_num.WAV"]

    def test_discover_large_number_sequence(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test discovery handles large sequence numbers."""
        (tmp_input_dir / "00999999.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "01000000.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "00999998.WAV").write_bytes(b"\x00")

        files = discovery.discover_files()

        assert len(files) == 3
        assert files[0].name == "00999998.WAV"
        assert files[1].name == "00999999.WAV"
        assert files[2].name == "01000000.WAV"

    def test_discover_mixed_filename_patterns(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test discovery with various filename patterns."""
        (tmp_input_dir / "track_001.wav").write_bytes(b"\x00")
        (tmp_input_dir / "02_backup.WAV").write_bytes(b"\x00")
        (tmp_input_dir / "session-003.Wav").write_bytes(b"\x00")
        (tmp_input_dir / "no_number_here.wav").write_bytes(b"\x00")

        files = discovery.discover_files()

        assert len(files) == 4
        # Should be sorted by first number found
        assert files[0].name == "track_001.wav"
        assert files[1].name == "02_backup.WAV"
        assert files[2].name == "session-003.Wav"
        assert files[3].name == "no_number_here.wav"

    def test_sort_key_numeric_extraction(self, discovery: AudioFileDiscovery) -> None:
        """Test _sort_key extracts numbers correctly."""
        # Test various filename patterns
        test_cases = [
            ("00000001.WAV", (1, "00000001")),
            ("track_001.wav", (1, "track_001")),
            ("02_backup.WAV", (2, "02_backup")),
            ("session-003.Wav", (3, "session-003")),
            ("no_number_here.wav", (float('inf'), "no_number_here")),
            ("abc123def.wav", (123, "abc123def")),
        ]

        for filename, expected in test_cases:
            path = Path(filename)
            key = discovery._sort_key(path)
            assert key == expected

    def test_sort_key_stable_sort(self, discovery: AudioFileDiscovery) -> None:
        """Test _sort_key provides stable sorting for same numbers."""
        # Files with same number should be sorted by filename
        path1 = Path("001_first.wav")
        path2 = Path("001_second.wav")

        key1 = discovery._sort_key(path1)
        key2 = discovery._sort_key(path2)

        assert key1[0] == key2[0] == 1  # Same number
        assert key1[1] < key2[1]  # "001_first" < "001_second"

    def test_discover_subdirectory_files_ignored(self, discovery: AudioFileDiscovery, tmp_input_dir: Path) -> None:
        """Test that files in subdirectories are not discovered."""
        # Create subdirectory
        subdir = tmp_input_dir / "subdir"
        subdir.mkdir()

        # Create files in root and subdirectory
        (tmp_input_dir / "00000001.WAV").write_bytes(b"\x00")
        (subdir / "00000002.WAV").write_bytes(b"\x00")

        files = discovery.discover_files()

        assert len(files) == 1
        assert files[0].name == "00000001.WAV"
        assert files[0].parent == tmp_input_dir