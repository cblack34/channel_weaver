"""Unit tests for ScipyClickAnalyzer."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from src.audio.click.analyzer import ScipyClickAnalyzer
from src.audio.click.enums import SectionType
from src.audio.click.models import SectionBoundaries
from src.config.models import SectionSplittingConfig
from src.exceptions import AudioProcessingError


class TestScipyClickAnalyzer:
    """Tests for ScipyClickAnalyzer."""

    @pytest.fixture
    def config(self) -> SectionSplittingConfig:
        """Create test configuration."""
        return SectionSplittingConfig(
            enabled=True,
            gap_threshold_seconds=3.0,
            min_section_length_seconds=15.0,
            bpm_change_threshold=1
        )

    @pytest.fixture
    def analyzer(self, config: SectionSplittingConfig) -> ScipyClickAnalyzer:
        """Create test analyzer."""
        return ScipyClickAnalyzer(config)

    def test_init_success(self, config: SectionSplittingConfig) -> None:
        """Test analyzer initialization."""
        analyzer = ScipyClickAnalyzer(config)
        assert analyzer.config == config
        assert analyzer.config.bandpass_low == 20
        assert analyzer.config.bandpass_high == 20000

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.read')
    def test_detect_onsets_success(
        self, mock_read, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test successful onset detection."""
        # Create a simple audio signal with some peaks
        duration = 5.0
        num_samples = int(duration * sample_rate)
        audio = np.zeros(num_samples)
        
        # Add some peaks
        for i in range(0, num_samples, int(0.5 * sample_rate)):
            if i < num_samples:
                audio[i] = 0.5
        
        mock_read.return_value = (audio, sample_rate)
        
        audio_path = Path("test.wav")
        onsets = analyzer.detect_onsets(audio_path, sample_rate)
        
        # Should detect some onsets
        assert isinstance(onsets, list)
        mock_read.assert_called_once_with(str(audio_path))

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.read')
    def test_detect_onsets_failure(
        self, mock_read, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test onset detection failure."""
        mock_read.side_effect = Exception("Soundfile error")

        with pytest.raises(AudioProcessingError, match="Failed to detect onsets"):
            analyzer.detect_onsets(Path("test.wav"), sample_rate)

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_estimate_bpm_success(
        self, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test successful BPM estimation."""
        # Calculate onset samples for 120 BPM at given sample rate
        # 120 BPM = 2 beats per second, IOI = 0.5 seconds
        ioi_samples = int(0.5 * sample_rate)
        onset_samples = [0, ioi_samples, 2 * ioi_samples, 3 * ioi_samples]

        bpm = analyzer.estimate_bpm(onset_samples, sample_rate, 0, 3 * ioi_samples)

        assert bpm == 120.0

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_estimate_bpm_insufficient_onsets(
        self, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test BPM estimation with insufficient onsets."""
        onset_samples = [0, int(0.5 * sample_rate)]  # Only 2 onsets
        window_end = int(1.0 * sample_rate)

        bpm = analyzer.estimate_bpm(onset_samples, sample_rate, 0, window_end)

        assert bpm is None

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_estimate_bpm_out_of_range(
        self, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test BPM estimation with out-of-range result."""
        onset_samples = [0, 100]  # Very fast tempo
        window_end = 200

        bpm = analyzer.estimate_bpm(onset_samples, sample_rate, 0, window_end)

        assert bpm is None  # BPM would be > 300

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_create_single_speaking_section(
        self, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test creating single speaking section for no-click files."""
        total_samples = 100000

        boundaries = analyzer._create_single_speaking_section(total_samples)

        assert len(boundaries.sections) == 1
        section = boundaries.sections[0]
        assert section.section_number == 1
        assert section.start_sample == 0
        assert section.end_sample == 100000
        assert section.section_type == SectionType.SPEAKING
        assert section.bpm is None

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_analyze_sections_with_gap(
        self, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test section analysis with gaps creates speaking sections between songs."""
        # Create onsets with a gap
        interval = int(0.5 * sample_rate)  # 0.5 second intervals
        gap_samples = int(5.0 * sample_rate)  # 5 second gap
        
        onsets = [0, interval, 2 * interval, 3 * interval]
        # Add gap then more onsets
        onsets += [3 * interval + gap_samples + interval * i for i in range(4)]
        
        total_samples = onsets[-1] + interval

        boundaries = analyzer._analyze_sections(onsets, total_samples, sample_rate)

        # Should have 3 sections: song, speaking (gap), song
        assert len(boundaries.sections) == 3
        assert boundaries.sections[0].section_type == SectionType.SONG
        assert boundaries.sections[1].section_type == SectionType.SPEAKING
        assert boundaries.sections[2].section_type == SectionType.SONG

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_analyze_sections_with_trailing_silence(
        self, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test section analysis detects trailing silence as speaking."""
        interval = int(0.5 * sample_rate)
        onsets = [0, interval, 2 * interval, 3 * interval]
        
        # Total samples includes a 10 second silence at the end
        silence_samples = int(10.0 * sample_rate)
        total_samples = onsets[-1] + interval + silence_samples

        boundaries = analyzer._analyze_sections(onsets, total_samples, sample_rate)

        # Should have 2 sections: song + speaking
        assert len(boundaries.sections) == 2
        assert boundaries.sections[0].section_type == SectionType.SONG
        assert boundaries.sections[1].section_type == SectionType.SPEAKING

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_merge_short_sections(
        self, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test merging short sections."""
        # Create boundaries with a short section and a normal section
        from src.audio.click.models import SectionInfo
        
        boundaries = SectionBoundaries()
        # Short section (5 seconds < 15 second minimum)
        boundaries.add_section(SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=int(5.0 * sample_rate),
            section_type=SectionType.SONG,
            bpm=120
        ))
        # Normal section (60 seconds)
        boundaries.add_section(SectionInfo(
            section_number=2,
            start_sample=int(5.0 * sample_rate),
            end_sample=int(65.0 * sample_rate),
            section_type=SectionType.SONG,
            bpm=120
        ))

        merged = analyzer._merge_short_sections(boundaries, sample_rate)

        # Should merge into 1 section
        assert len(merged.sections) == 1
        assert merged.sections[0].start_sample == 0
        assert merged.sections[0].end_sample == int(65.0 * sample_rate)

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.read')
    def test_analyze_no_onsets(
        self, mock_read, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test analysis with no detected onsets."""
        # Create silent audio
        num_samples = int(10.0 * sample_rate)
        audio = np.zeros(num_samples)
        mock_read.return_value = (audio, sample_rate)

        boundaries = analyzer.analyze(Path("test.wav"), sample_rate)

        assert len(boundaries.sections) == 1
        assert boundaries.sections[0].section_type == SectionType.SPEAKING

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.read')
    def test_analyze_with_onsets(
        self, mock_read, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test analysis with detected onsets."""
        # Create audio with clear peaks
        duration = 60.0
        num_samples = int(duration * sample_rate)
        audio = np.zeros(num_samples)
        
        # Add peaks every 0.5 seconds (120 BPM) for first 30 seconds
        for i in range(60):
            sample_idx = int(i * 0.5 * sample_rate)
            if sample_idx < num_samples:
                audio[sample_idx] = 0.8
        
        mock_read.return_value = (audio, sample_rate)

        boundaries = analyzer.analyze(Path("test.wav"), sample_rate)

        # Should detect at least 1 section
        assert len(boundaries.sections) >= 1

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.read')
    def test_analyze_failure(
        self, mock_read, analyzer: ScipyClickAnalyzer, sample_rate: int
    ) -> None:
        """Test analysis failure."""
        mock_read.side_effect = Exception("Test error")

        with pytest.raises(AudioProcessingError, match="Failed to analyze click track"):
            analyzer.analyze(Path("test.wav"), sample_rate)

    def test_estimate_bpm_from_onsets_empty(
        self, analyzer: ScipyClickAnalyzer
    ) -> None:
        """Test BPM estimation with empty onset list."""
        bpm = analyzer._estimate_bpm_from_onsets([], 48000)
        assert bpm is None

    def test_estimate_bpm_from_onsets_few(
        self, analyzer: ScipyClickAnalyzer
    ) -> None:
        """Test BPM estimation with few onsets."""
        bpm = analyzer._estimate_bpm_from_onsets([0, 1000], 48000)
        assert bpm is None  # Need at least 4 onsets
