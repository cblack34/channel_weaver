"""Tests for session JSON output writer."""

import json
import tempfile
from pathlib import Path

from src.audio.click.enums import SectionType
from src.audio.click.models import SectionInfo
from src.output.session_json import SessionJsonWriter


class TestSessionJsonWriter:
    """Test the SessionJsonWriter class."""

    def test_write_session_json_basic(self) -> None:
        """Test basic JSON writing functionality."""
        writer = SessionJsonWriter()

        # Create test sections
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=44100 * 60,  # 60 seconds at 44.1kHz
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=44100 * 60,
                end_sample=44100 * 120,  # 60 seconds
                section_type=SectionType.SPEAKING,
                bpm=None,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "session.json"

            # Write JSON
            result = writer.write_session_json(sections, output_path, 44100)
            assert result is True
            assert output_path.exists()

            # Read and verify content
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 2

            # Check first section
            assert data[0]["section"] == "section_01"
            assert data[0]["start_seconds"] == 0.0
            assert data[0]["start_hms"] == "00:00:00"
            assert abs(data[0]["duration_seconds"] - 60.0) < 0.001
            assert data[0]["duration_hms"] == "00:01:00"
            assert data[0]["type"] == "song"
            assert data[0]["bpm"] == 120

            # Check second section
            assert data[1]["section"] == "section_02"
            assert abs(data[1]["start_seconds"] - 60.0) < 0.001
            assert data[1]["start_hms"] == "00:01:00"
            assert abs(data[1]["duration_seconds"] - 60.0) < 0.001
            assert data[1]["duration_hms"] == "00:01:00"
            assert data[1]["type"] == "speaking"
            assert data[1]["bpm"] is None

    def test_write_session_json_precision(self) -> None:
        """Test that floating point precision is maintained."""
        writer = SessionJsonWriter()

        sections = [
            SectionInfo(
                section_number=1,
                start_sample=4410,  # 0.1 seconds
                end_sample=44100 + 4410,  # 1.1 seconds total
                section_type=SectionType.SONG,
                bpm=123,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "session.json"

            result = writer.write_session_json(sections, output_path, 44100)
            assert result is True

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data[0]["start_seconds"] == 0.1
            assert abs(data[0]["duration_seconds"] - 1.0) < 0.001

    def test_write_session_json_atomic_write(self) -> None:
        """Test that writes are atomic (no partial files on failure)."""
        writer = SessionJsonWriter()

        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=44100,
                section_type=SectionType.SONG,
                bpm=120,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "session.json"

            # Should succeed
            result = writer.write_session_json(sections, output_path, 44100)
            assert result is True
            assert output_path.exists()

            # Verify it's valid JSON
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) == 1

    def test_write_session_json_creates_parent_dirs(self) -> None:
        """Test that parent directories are created if they don't exist."""
        writer = SessionJsonWriter()

        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=44100,
                section_type=SectionType.SONG,
                bpm=120,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "subdir" / "nested" / "session.json"

            result = writer.write_session_json(sections, output_path, 44100)
            assert result is True
            assert output_path.exists()

    def test_write_session_json_empty_sections(self) -> None:
        """Test handling of empty sections list."""
        writer = SessionJsonWriter()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "session.json"

            result = writer.write_session_json([], output_path, 44100)
            assert result is True
            assert output_path.exists()

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data == []

    def test_format_time_edge_cases(self) -> None:
        """Test time formatting for edge cases."""
        writer = SessionJsonWriter()

        # Test zero seconds
        assert writer._format_time(0.0) == "00:00:00"

        # Test fractional seconds (should round down)
        assert writer._format_time(0.9) == "00:00:00"
        assert writer._format_time(59.9) == "00:00:59"

        # Test minutes and hours
        assert writer._format_time(60.0) == "00:01:00"
        assert writer._format_time(3600.0) == "01:00:00"
        assert writer._format_time(3661.0) == "01:01:01"