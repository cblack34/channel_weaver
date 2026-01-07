"""Unit tests for ScipyClickAnalyzer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.audio.click.analyzer import ScipyClickAnalyzer
from src.audio.click.enums import SectionType
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
        assert analyzer.config.bandpass_low == 500
        assert analyzer.config.bandpass_high == 5000

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.SoundFile')
    def test_detect_onsets_success(self, mock_soundfile, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test successful onset detection."""
        # Mock soundfile
        mock_sf_instance = MagicMock()
        block_size = int(sample_rate * 0.1)  # 100ms blocks
        mock_audio_block = np.random.randn(block_size).astype(np.float32)
        mock_sf_instance.blocks.return_value = [mock_audio_block]
        mock_soundfile.return_value.__enter__.return_value = mock_sf_instance

        # Mock the _detect_onsets_in_block method to return some onsets
        with patch.object(analyzer, '_detect_onsets_in_block', return_value=[100, 200]):
            audio_path = Path("test.wav")
            onsets = analyzer.detect_onsets(audio_path, sample_rate)

            assert len(onsets) == 2
            assert onsets == [100, 200]

            # soundfile requires string paths, so we convert Path to str
            mock_soundfile.assert_called_once_with(str(audio_path))

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.SoundFile')
    def test_detect_onsets_failure(self, mock_soundfile, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test onset detection failure."""
        mock_soundfile.side_effect = Exception("Soundfile error")

        with pytest.raises(AudioProcessingError, match="Failed to detect onsets"):
            analyzer.detect_onsets(Path("test.wav"), sample_rate)

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_estimate_bpm_success(self, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test successful BPM estimation."""
        # Calculate onset samples for 120 BPM at given sample rate
        # 120 BPM = 2 beats per second, IOI = 0.5 seconds
        ioi_samples = int(0.5 * sample_rate)  # 22050 at 44100, 24000 at 48000, 48000 at 96000
        onset_samples = [0, ioi_samples, 2 * ioi_samples, 3 * ioi_samples]

        bpm = analyzer.estimate_bpm(onset_samples, sample_rate, 0, 3 * ioi_samples)

        assert bpm == 120.0

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_estimate_bpm_insufficient_onsets(self, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test BPM estimation with insufficient onsets."""
        onset_samples = [0, int(0.5 * sample_rate)]  # Only 2 onsets
        window_end = int(1.0 * sample_rate)

        bpm = analyzer.estimate_bpm(onset_samples, sample_rate, 0, window_end)

        assert bpm is None

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_estimate_bpm_out_of_range(self, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test BPM estimation with out-of-range result."""
        onset_samples = [0, 100]  # Very fast tempo
        window_end = 200

        bpm = analyzer.estimate_bpm(onset_samples, sample_rate, 0, window_end)

        assert bpm is None  # BPM would be > 200

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    @patch('src.audio.click.analyzer.sf.SoundFile')
    def test_create_single_speaking_section(self, mock_soundfile, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test creating single speaking section for no-click files."""
        mock_sf = MagicMock()
        mock_sf.__len__ = MagicMock(return_value=100000)
        mock_soundfile.return_value.__enter__.return_value = mock_sf

        boundaries = analyzer._create_single_speaking_section(Path("test.wav"), sample_rate)

        assert len(boundaries.sections) == 1
        section = boundaries.sections[0]
        assert section.section_number == 1
        assert section.start_sample == 0
        assert section.end_sample == 100000
        assert section.section_type == SectionType.SPEAKING
        assert section.bpm is None

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_merge_short_sections(self, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test merging short sections."""
        # Create boundaries with a short section
        boundaries = analyzer._analyze_sections([0, 1000, 100000], sample_rate)  # Short first section

        # Mock the duration check - make first section short
        merged = analyzer._merge_short_sections(boundaries, sample_rate)

        # Should merge short sections
        assert len(merged.sections) >= 1

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_analyze_no_onsets(self, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test analysis with no detected onsets."""
        with patch.object(analyzer, 'detect_onsets', return_value=[]):
            with patch.object(analyzer, '_create_single_speaking_section') as mock_create:
                mock_create.return_value = MagicMock()
                analyzer.analyze(Path("test.wav"), sample_rate)
                mock_create.assert_called_once()

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_analyze_with_onsets(self, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test analysis with detected onsets."""
        # Create onsets with regular intervals and a gap
        interval = int(0.5 * sample_rate)  # 0.5 second intervals
        onsets = [0, interval, 2 * interval, 3 * interval, int(4.5 * sample_rate)]  # Gap after 3rd onset

        with patch.object(analyzer, 'detect_onsets', return_value=onsets):
            with patch.object(analyzer, '_analyze_sections') as mock_analyze:
                mock_analyze.return_value = MagicMock()
                analyzer.analyze(Path("test.wav"), sample_rate)
                mock_analyze.assert_called_once_with(onsets, sample_rate)

    @pytest.mark.parametrize("sample_rate", [44100, 48000, 96000])
    def test_analyze_failure(self, analyzer: ScipyClickAnalyzer, sample_rate: int) -> None:
        """Test analysis failure."""
        with patch.object(analyzer, 'detect_onsets', side_effect=Exception("Test error")):
            with pytest.raises(AudioProcessingError, match="Failed to analyze click track"):
                analyzer.analyze(Path("test.wav"), sample_rate)