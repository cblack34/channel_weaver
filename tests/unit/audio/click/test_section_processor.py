"""Tests for section boundary processing and merging."""

import pytest

from src.audio.click.enums import SectionType
from src.audio.click.models import SectionInfo
from src.audio.click.section_processor import SectionProcessor


class TestSectionProcessor:
    """Test cases for SectionProcessor functionality."""

    @pytest.fixture
    def sample_rate(self) -> int:
        """Sample rate for testing."""
        return 44100

    @pytest.fixture
    def sample_sections(self, sample_rate: int) -> list[SectionInfo]:
        """Create sample sections for testing."""
        return [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,  # 10 seconds
                start_seconds=0.0,
                duration_seconds=10.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=20 * sample_rate,  # 10 seconds (not short)
                start_seconds=10.0,
                duration_seconds=10.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=3,
                start_sample=20 * sample_rate,
                end_sample=33 * sample_rate,  # 13 seconds
                start_seconds=20.0,
                duration_seconds=13.0,
                section_type=SectionType.SONG,
                bpm=100,
            ),
        ]

    def test_merge_short_sections_no_merging_needed(self, sample_sections: list[SectionInfo], sample_rate: int):
        """Test that sections above minimum length are not merged."""
        min_length = 5.0  # seconds
        result = SectionProcessor.merge_short_sections(sample_sections, min_length, sample_rate)

        # Should have same number of sections
        assert len(result) == 3
        assert result[0].section_number == 1
        assert result[1].section_number == 2
        assert result[2].section_number == 3

    def test_merge_short_sections_middle_section(self, sample_rate: int):
        """Test merging a short middle section into previous section."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,  # 10 seconds
                start_seconds=0.0,
                duration_seconds=10.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=12 * sample_rate,  # 2 seconds (short)
                start_seconds=10.0,
                duration_seconds=2.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=3,
                start_sample=12 * sample_rate,
                end_sample=25 * sample_rate,  # 13 seconds
                start_seconds=12.0,
                duration_seconds=13.0,
                section_type=SectionType.SONG,
                bpm=100,
            ),
        ]
        min_length = 3.0  # seconds - middle section is 2 seconds, should merge
        result = SectionProcessor.merge_short_sections(sections, min_length, sample_rate)

        # Should merge section 2 into section 1
        assert len(result) == 2
        assert result[0].section_number == 1
        assert result[0].start_sample == 0
        assert result[0].end_sample == 12 * 44100  # Merged up to end of section 2
        assert result[0].bpm == 120  # Keeps original BPM
        assert result[1].section_number == 2  # Renumbered
        assert result[1].start_sample == 12 * 44100

    def test_merge_short_sections_first_section(self, sample_rate: int):
        """Test merging a short first section into the next section."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=2 * sample_rate,  # 2 seconds (short)
                start_seconds=0.0,
                duration_seconds=2.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=2 * sample_rate,
                end_sample=15 * sample_rate,  # 13 seconds
                start_seconds=2.0,
                duration_seconds=13.0,
                section_type=SectionType.SONG,
                bpm=100,
            ),
        ]

        min_length = 3.0
        result = SectionProcessor.merge_short_sections(sections, min_length, sample_rate)

        # Should merge section 1 into section 2
        assert len(result) == 1
        assert result[0].section_number == 1  # Renumbered to 1
        assert result[0].start_sample == 0
        assert result[0].end_sample == 15 * sample_rate
        assert result[0].bpm == 100  # Uses next section's BPM (longer section)

    def test_merge_short_sections_last_section(self, sample_rate: int):
        """Test that a short last section gets merged into previous."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,  # 10 seconds
                start_seconds=0.0,
                duration_seconds=0.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=11 * sample_rate,  # 1 second (short)
                start_seconds=0.0,
                duration_seconds=0.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
        ]

        min_length = 2.0
        result = SectionProcessor.merge_short_sections(sections, min_length, sample_rate)

        # Should merge section 2 into section 1
        assert len(result) == 1
        assert result[0].section_number == 1
        assert result[0].start_sample == 0
        assert result[0].end_sample == 11 * sample_rate
        assert result[0].bpm == 120

    def test_merge_short_sections_all_short(self, sample_rate: int):
        """Test merging when all sections are short."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=1 * sample_rate,  # 1 second
                start_seconds=0.0,
                duration_seconds=1.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=1 * sample_rate,
                end_sample=2 * sample_rate,  # 1 second
                start_seconds=1.0,
                duration_seconds=1.0,
                section_type=SectionType.SONG,
                bpm=100,
            ),
            SectionInfo(
                section_number=3,
                start_sample=2 * sample_rate,
                end_sample=3 * sample_rate,  # 1 second
                start_seconds=2.0,
                duration_seconds=1.0,
                section_type=SectionType.SONG,
                bpm=110,
            ),
        ]

        min_length = 2.0
        result = SectionProcessor.merge_short_sections(sections, min_length, sample_rate)

        # Should merge all into one section
        assert len(result) == 1
        assert result[0].section_number == 1
        assert result[0].start_sample == 0
        assert result[0].end_sample == 3 * sample_rate
        assert result[0].bpm == 120  # Keeps first section's BPM

    def test_merge_short_sections_empty_list(self):
        """Test merging with empty section list."""
        result = SectionProcessor.merge_short_sections([], 5.0, 44100)
        assert result == []

    def test_merge_short_sections_single_section(self, sample_rate: int):
        """Test merging with single section."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,
                start_seconds=0.0,
                duration_seconds=10.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
        ]

        result = SectionProcessor.merge_short_sections(sections, 5.0, sample_rate)
        assert len(result) == 1
        assert result[0] == sections[0]

    def test_calculate_section_metadata(self, sample_rate: int):
        """Test metadata calculation for sections."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,  # 10 seconds
                start_seconds=0.0,
                duration_seconds=10.0,
                section_type=SectionType.SONG,
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=11 * sample_rate,  # 1 second (short)
                start_seconds=10.0,
                duration_seconds=1.0,
                section_type=SectionType.SPEAKING,
                bpm=None,
            ),
        ]

        result = SectionProcessor.calculate_section_metadata(sections, sample_rate)

        assert len(result) == 2

        # Check first section
        assert result[0].section_number == 1
        assert result[0].start_sample == 0
        assert result[0].end_sample == 10 * sample_rate
        assert abs(result[0].start_seconds - 0.0) < 0.001
        assert abs(result[0].duration_seconds - 10.0) < 0.001

        # Check second section
        assert result[1].section_number == 2
        assert result[1].start_sample == 10 * sample_rate
        assert result[1].end_sample == 11 * sample_rate
        assert abs(result[1].start_seconds - 10.0) < 0.001
        assert abs(result[1].duration_seconds - 1.0) < 0.001

    def test_classify_sections_with_bpm(self, sample_rate: int):
        """Test classifying sections that have BPM as song sections."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,
                section_type=SectionType.SONG,  # Will be overridden
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=20 * sample_rate,
                section_type=SectionType.SONG,  # Will be overridden
                bpm=100,
            ),
        ]

        result = SectionProcessor.classify_sections(sections)

        assert len(result) == 2
        assert result[0].section_type == SectionType.SONG
        assert result[1].section_type == SectionType.SONG

    def test_classify_sections_without_bpm(self, sample_rate: int):
        """Test classifying sections without BPM as speaking sections."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,
                section_type=SectionType.SONG,  # Will be overridden
                bpm=None,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=20 * sample_rate,
                section_type=SectionType.SONG,  # Will be overridden
                bpm=None,
            ),
        ]

        result = SectionProcessor.classify_sections(sections)

        assert len(result) == 2
        assert result[0].section_type == SectionType.SPEAKING
        assert result[1].section_type == SectionType.SPEAKING

    def test_classify_sections_mixed(self, sample_rate: int):
        """Test classifying sections with mixed BPM presence."""
        sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,
                section_type=SectionType.SPEAKING,  # Will be overridden
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=20 * sample_rate,
                section_type=SectionType.SONG,  # Will be overridden
                bpm=None,
            ),
        ]

        result = SectionProcessor.classify_sections(sections)

        assert len(result) == 2
        assert result[0].section_type == SectionType.SONG
        assert result[1].section_type == SectionType.SPEAKING

    def test_process_sections_complete_pipeline(self, sample_rate: int):
        """Test the complete section processing pipeline."""
        # Raw sections from analyzer (may have wrong types, short sections)
        raw_sections = [
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=10 * sample_rate,  # 10 seconds
                section_type=SectionType.SPEAKING,  # Wrong type initially
                bpm=120,
            ),
            SectionInfo(
                section_number=2,
                start_sample=10 * sample_rate,
                end_sample=12 * sample_rate,  # 2 seconds (short)
                section_type=SectionType.SPEAKING,  # Wrong type initially
                bpm=120,
            ),
            SectionInfo(
                section_number=3,
                start_sample=12 * sample_rate,
                end_sample=25 * sample_rate,  # 13 seconds
                section_type=SectionType.SPEAKING,  # Wrong type initially
                bpm=None,
            ),
        ]

        result = SectionProcessor.process_sections(
            raw_sections, sample_rate, min_section_length_seconds=3.0
        )

        # Should have 2 sections after merging
        assert len(result) == 2

        # First section: merged from 1+2, classified as song
        assert result[0].section_number == 1
        assert result[0].start_sample == 0
        assert result[0].end_sample == 12 * sample_rate
        assert result[0].section_type == SectionType.SONG
        assert result[0].bpm == 120
        assert abs(result[0].duration_seconds - 12.0) < 0.001

        # Second section: section 3, classified as speaking
        assert result[1].section_number == 2
        assert result[1].start_sample == 12 * sample_rate
        assert result[1].end_sample == 25 * sample_rate
        assert result[1].section_type == SectionType.SPEAKING
        assert result[1].bpm is None
        assert abs(result[1].duration_seconds - 13.0) < 0.001