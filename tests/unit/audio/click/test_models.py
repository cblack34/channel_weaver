"""Unit tests for click track analysis models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.audio.click.models import SectionInfo, SectionBoundaries
from src.audio.click.enums import SectionType


class TestSectionInfo:
    """Tests for SectionInfo Pydantic model."""

    def test_valid_section_creation(self) -> None:
        """Test creating a valid SectionInfo with minimum required fields."""
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=SectionType.SONG,
            bpm=120,
        )

        assert section.section_number == 1
        assert section.start_sample == 0
        assert section.end_sample == 44100
        assert section.section_type == SectionType.SONG
        assert section.bpm == 120

    def test_section_without_bpm(self) -> None:
        """Test creating a SectionInfo without BPM (None is allowed)."""
        section = SectionInfo(
            section_number=2,
            start_sample=44100,
            end_sample=88200,
            section_type=SectionType.SPEAKING,
            bpm=None,
        )

        assert section.bpm is None

    @pytest.mark.parametrize("section_type_str,expected_enum", [
        ("song", SectionType.SONG),
        ("SONG", SectionType.SONG),
        ("speaking", SectionType.SPEAKING),
        ("SPEAKING", SectionType.SPEAKING),
    ])
    def test_section_type_string_conversion(
        self,
        section_type_str: str,
        expected_enum: SectionType,
    ) -> None:
        """Test that section type strings are converted to SectionType enums."""
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=section_type_str,  # type: ignore[arg-type]
            bpm=None,
        )

        assert section.section_type == expected_enum

    def test_invalid_section_number(self) -> None:
        """Test that section_number must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            SectionInfo(
                section_number=0,
                start_sample=0,
                end_sample=44100,
                section_type=SectionType.SONG,
                bpm=None,
            )

        assert "section_number" in str(exc_info.value)
        assert "greater_than_equal" in str(exc_info.value)

    def test_invalid_start_sample(self) -> None:
        """Test that start_sample must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            SectionInfo(
                section_number=1,
                start_sample=-1,
                end_sample=44100,
                section_type=SectionType.SONG,
                bpm=None,
            )

        assert "start_sample" in str(exc_info.value)
        assert "greater_than_equal" in str(exc_info.value)

    def test_invalid_end_sample(self) -> None:
        """Test that end_sample must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=-1,
                section_type=SectionType.SONG,
                bpm=None,
            )

        assert "end_sample" in str(exc_info.value)
        assert "greater_than_equal" in str(exc_info.value)

    def test_end_sample_before_start_sample(self) -> None:
        """Test that end_sample must be greater than start_sample."""
        with pytest.raises(ValidationError) as exc_info:
            SectionInfo(
                section_number=1,
                start_sample=44100,
                end_sample=22050,
                section_type=SectionType.SONG,
                bpm=None,
            )

        assert "end_sample" in str(exc_info.value)
        assert "must be greater than" in str(exc_info.value)

    def test_invalid_bpm(self) -> None:
        """Test that bpm must be >= 1 if provided."""
        with pytest.raises(ValidationError) as exc_info:
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=44100,
                section_type=SectionType.SONG,
                bpm=0,
            )

        assert "bpm" in str(exc_info.value)
        assert "greater_than_equal" in str(exc_info.value)

    def test_serialization(self) -> None:
        """Test that SectionInfo can be serialized to/from JSON."""
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=SectionType.SONG,
            bpm=120,
        )

        data = section.model_dump()
        assert data["section_number"] == 1
        assert data["start_sample"] == 0
        assert data["end_sample"] == 44100
        assert data["section_type"] == SectionType.SONG  # Enum object
        assert data["bpm"] == 120

        # Test JSON serialization
        json_data = section.model_dump_json()
        assert '"section_type":"song"' in json_data

        # Test round-trip
        section2 = SectionInfo.model_validate(data)
        assert section2 == section


class TestSectionBoundaries:
    """Tests for SectionBoundaries Pydantic model."""

    def test_empty_boundaries(self) -> None:
        """Test creating empty SectionBoundaries."""
        boundaries = SectionBoundaries()

        assert boundaries.sections == []
        assert boundaries.get_section_count() == 0
        assert boundaries.get_total_duration_samples() == 0

    def test_add_section(self) -> None:
        """Test adding sections to boundaries."""
        boundaries = SectionBoundaries()
        section1 = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=SectionType.SONG,
            bpm=None,
        )
        section2 = SectionInfo(
            section_number=2,
            start_sample=44100,
            end_sample=88200,
            section_type=SectionType.SPEAKING,
            bpm=None,
        )

        boundaries.add_section(section1)
        boundaries.add_section(section2)

        assert boundaries.get_section_count() == 2
        assert boundaries.sections[0] == section1
        assert boundaries.sections[1] == section2

    def test_get_sections_by_type(self) -> None:
        """Test filtering sections by type."""
        boundaries = SectionBoundaries()
        song_section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=SectionType.SONG,
            bpm=None,
        )
        speaking_section = SectionInfo(
            section_number=2,
            start_sample=44100,
            end_sample=88200,
            section_type=SectionType.SPEAKING,
            bpm=None,
        )

        boundaries.add_section(song_section)
        boundaries.add_section(speaking_section)

        songs = boundaries.get_sections_by_type(SectionType.SONG)
        assert len(songs) == 1
        assert songs[0] == song_section

        speaking = boundaries.get_sections_by_type(SectionType.SPEAKING)
        assert len(speaking) == 1
        assert speaking[0] == speaking_section

    def test_get_total_duration_samples(self) -> None:
        """Test calculating total duration covered by sections."""
        boundaries = SectionBoundaries()
        section1 = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=SectionType.SONG,
            bpm=None,
        )
        section2 = SectionInfo(
            section_number=2,
            start_sample=44100,
            end_sample=88200,
            section_type=SectionType.SPEAKING,
            bpm=None,
        )

        boundaries.add_section(section1)
        boundaries.add_section(section2)

        # Total duration should be from 0 to 88200 = 88200 samples
        assert boundaries.get_total_duration_samples() == 88200

    def test_serialization(self) -> None:
        """Test that SectionBoundaries can be serialized to/from JSON."""
        boundaries = SectionBoundaries()
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=SectionType.SONG,
            bpm=120,
        )
        boundaries.add_section(section)

        data = boundaries.model_dump()
        assert len(data["sections"]) == 1
        assert data["sections"][0]["section_number"] == 1

        # Test round-trip
        boundaries2 = SectionBoundaries.model_validate(data)
        assert boundaries2.sections[0] == section

    def test_from_dict_to_dict_round_trip(self) -> None:
        """Test the from_dict and to_dict helper methods."""
        boundaries = SectionBoundaries()
        section = SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=44100,
            section_type=SectionType.SONG,
            bpm=None,
        )
        boundaries.add_section(section)

        data = boundaries.to_dict()
        boundaries2 = SectionBoundaries.from_dict(data)

        assert boundaries2.sections[0] == section