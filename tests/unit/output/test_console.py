
"""Unit tests for console output handler."""

from unittest.mock import MagicMock

import pytest
from rich.console import Console

from src.audio.click.enums import SectionType
from src.audio.click.models import SectionInfo
from src.output.console import ConsoleOutputHandler


class TestConsoleOutputHandler:
    """Tests for ConsoleOutputHandler."""

    @pytest.fixture
    def mock_console(self) -> MagicMock:
        """Create a mock Rich console."""
        return MagicMock(spec=Console)

    @pytest.fixture
    def handler(self, mock_console: MagicMock) -> ConsoleOutputHandler:
        """Create a ConsoleOutputHandler with mocked console."""
        return ConsoleOutputHandler(mock_console)

    def test_print_section_summary_with_sections(self, handler: ConsoleOutputHandler, mock_console: MagicMock) -> None:
        """Test printing section summary with valid sections."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=44100,
                start_seconds=0.0,
                duration_seconds=1.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=44100,
                end_sample=88200,
                start_seconds=1.0,
                duration_seconds=1.0,
                section_type=SectionType.SPEAKING,
                bpm=None,
            ),
        ]

        handler.print_section_summary(sections)

        # Verify console.print was called (table output)
        assert mock_console.print.call_count >= 3  # Title, table, empty line

    def test_print_section_summary_empty_sections(self, handler: ConsoleOutputHandler, mock_console: MagicMock) -> None:
        """Test printing section summary with empty sections list."""
        handler.print_section_summary([])

        # Should print warning message
        mock_console.print.assert_called_with("[yellow]Warning:[/yellow] No sections detected")

    def test_format_time(self, handler: ConsoleOutputHandler) -> None:
        """Test time formatting helper method."""
        # Test various time values
        assert handler._format_time(0) == "00:00:00"
        assert handler._format_time(1) == "00:00:01"
        assert handler._format_time(59) == "00:00:59"
        assert handler._format_time(60) == "00:01:00"
        assert handler._format_time(61) == "00:01:01"
        assert handler._format_time(3599) == "00:59:59"
        assert handler._format_time(3600) == "01:00:00"
        assert handler._format_time(3661) == "01:01:01"
        assert handler._format_time(7265) == "02:01:05"

    def test_format_time_with_floats(self, handler: ConsoleOutputHandler) -> None:
        """Test time formatting with floating point seconds."""
        assert handler._format_time(1.5) == "00:00:01"
        assert handler._format_time(90.7) == "00:01:30"
        assert handler._format_time(3661.9) == "01:01:01"