"""Unit tests for CLI processing options."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.models import ProcessingOptions


class TestProcessingOptions:
    """Tests for ProcessingOptions Pydantic model."""

    def test_default_values(self) -> None:
        """Test creating ProcessingOptions with defaults."""
        options = ProcessingOptions()

        assert options.section_by_click is False
        assert options.gap_threshold_seconds is None
        assert options.session_json_path is None

    def test_section_by_click_enabled(self) -> None:
        """Test creating ProcessingOptions with section_by_click enabled."""
        options = ProcessingOptions(section_by_click=True)

        assert options.section_by_click is True
        assert options.gap_threshold_seconds is None
        assert options.session_json_path is None

    def test_gap_threshold_positive(self) -> None:
        """Test setting a valid gap_threshold_seconds."""
        options = ProcessingOptions(gap_threshold_seconds=5.0)

        assert options.section_by_click is False
        assert options.gap_threshold_seconds == 5.0
        assert options.session_json_path is None

    def test_gap_threshold_zero_invalid(self) -> None:
        """Test that gap_threshold_seconds=0 raises validation error."""
        with pytest.raises(ValidationError, match="greater than 0"):
            ProcessingOptions(gap_threshold_seconds=0)

    def test_gap_threshold_negative_invalid(self) -> None:
        """Test that negative gap_threshold_seconds raises validation error."""
        with pytest.raises(ValidationError, match="greater than 0"):
            ProcessingOptions(gap_threshold_seconds=-1.0)

    def test_session_json_path(self) -> None:
        """Test setting a session_json_path."""
        json_path = Path("/path/to/session.json")
        options = ProcessingOptions(session_json_path=json_path)

        assert options.section_by_click is False
        assert options.gap_threshold_seconds is None
        assert options.session_json_path == json_path

    def test_all_options_together(self) -> None:
        """Test setting all options together."""
        json_path = Path("/path/to/output.json")
        options = ProcessingOptions(
            section_by_click=True,
            gap_threshold_seconds=2.5,
            session_json_path=json_path,
        )

        assert options.section_by_click is True
        assert options.gap_threshold_seconds == 2.5
        assert options.session_json_path == json_path

    def test_model_dump(self) -> None:
        """Test serializing ProcessingOptions to dict."""
        json_path = Path("/path/to/session.json")
        options = ProcessingOptions(
            section_by_click=True,
            gap_threshold_seconds=3.0,
            session_json_path=json_path,
        )

        data = options.model_dump()

        assert data["section_by_click"] is True
        assert data["gap_threshold_seconds"] == 3.0
        assert data["session_json_path"] == json_path

    def test_model_validate(self) -> None:
        """Test creating ProcessingOptions from dict."""
        data = {
            "section_by_click": True,
            "gap_threshold_seconds": 4.0,
            "session_json_path": Path("/test/path.json"),
        }

        options = ProcessingOptions.model_validate(data)

        assert options.section_by_click is True
        assert options.gap_threshold_seconds == 4.0
        assert options.session_json_path == Path("/test/path.json")
