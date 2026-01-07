"""NumPy/SciPy-based implementation of click track analysis."""

from pathlib import Path

import numpy as np
from scipy import signal
import soundfile as sf

from src.audio.click.enums import SectionType
from src.audio.click.models import SectionBoundaries, SectionInfo
from src.audio.click.protocols import ClickAnalyzerProtocol
from src.config.models import SectionSplittingConfig
from src.exceptions import AudioProcessingError


class ScipyClickAnalyzer(ClickAnalyzerProtocol):
    """Click track analyzer using NumPy/SciPy for onset detection and BPM estimation.

    This implementation uses signal processing techniques to:
    - Detect click onsets using bandpass filtering and peak detection
    - Estimate BPM from inter-onset intervals
    - Identify section boundaries based on click presence and BPM changes
    - Merge short sections according to configuration
    """

    def __init__(self, config: SectionSplittingConfig) -> None:
        """Initialize the analyzer with configuration.

        Args:
            config: Section splitting configuration
        """
        self.config = config

    def analyze(self, audio_path: Path, sample_rate: int) -> SectionBoundaries:
        """Analyze audio file and return section boundaries based on click track.

        Args:
            audio_path: Path to the audio file to analyze
            sample_rate: Sample rate of the audio file

        Returns:
            SectionBoundaries containing detected sections

        Raises:
            AudioProcessingError: If audio analysis fails
        """
        try:
            # Detect all onsets in the file
            onset_samples = self.detect_onsets(audio_path, sample_rate)

            if not onset_samples:
                # No clicks detected - treat entire file as speaking section
                return self._create_single_speaking_section(audio_path, sample_rate)

            # Analyze sections based on onsets and BPM changes
            boundaries = self._analyze_sections(onset_samples, sample_rate)

            # Merge short sections if configured
            if self.config.min_section_length_seconds > 0:
                boundaries = self._merge_short_sections(boundaries, sample_rate)

            return boundaries

        except Exception as e:
            raise AudioProcessingError(f"Failed to analyze click track: {e}") from e

    def detect_onsets(self, audio_path: Path, sample_rate: int) -> list[int]:
        """Detect onset positions in the audio file using signal processing.

        Args:
            audio_path: Path to the audio file to analyze
            sample_rate: Sample rate of the audio file

        Returns:
            List of onset positions in samples

        Raises:
            AudioProcessingError: If onset detection fails
        """
        try:
            onset_samples = []

            # Process audio in blocks for memory efficiency
            block_size = int(sample_rate * 0.1)  # 100ms blocks
            total_samples = 0

            with sf.SoundFile(str(audio_path)) as audio_file:
                for block in audio_file.blocks(blocksize=block_size, dtype='float32'):
                    # Convert to mono if stereo
                    if block.ndim > 1:
                        block = np.mean(block, axis=1)

                    # Detect onsets in this block
                    block_onsets = self._detect_onsets_in_block(block, sample_rate)
                    
                    # Convert block-relative samples to file-absolute samples
                    for onset in block_onsets:
                        onset_samples.append(total_samples + onset)

                    total_samples += len(block)

            return onset_samples

        except Exception as e:
            raise AudioProcessingError(f"Failed to detect onsets: {e}") from e

    def _detect_onsets_in_block(self, audio_block: np.ndarray, sample_rate: int) -> list[int]:
        """Detect onset positions within a single audio block.

        Args:
            audio_block: Audio samples for this block
            sample_rate: Sample rate of the audio

        Returns:
            List of onset positions relative to the start of the block
        """
        # Apply bandpass filter to isolate click frequencies
        filtered = self._apply_bandpass_filter(audio_block, sample_rate)

        # Compute envelope using Hilbert transform
        envelope = np.abs(signal.hilbert(filtered))

        # Compute novelty function (first derivative of envelope)
        novelty = np.diff(envelope, prepend=envelope[0])

        # Rectify and smooth novelty function
        novelty = np.maximum(novelty, 0)
        window_size = int(self.config.novelty_window * sample_rate)
        if window_size > 0:
            novelty = signal.convolve(novelty, np.ones(window_size)/window_size, mode='same')

        # Find peaks in novelty function
        min_distance_samples = int(self.config.min_peak_distance * sample_rate)
        peaks, _ = signal.find_peaks(
            novelty,
            distance=min_distance_samples,
            prominence=self.config.peak_prominence
        )

        return peaks.tolist()

    def _apply_bandpass_filter(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply bandpass filter to isolate click frequencies.

        Args:
            audio: Input audio signal
            sample_rate: Sample rate of the audio

        Returns:
            Filtered audio signal
        """
        # Design bandpass filter
        sos = signal.butter(
            self.config.filter_order,
            [self.config.bandpass_low, self.config.bandpass_high],
            btype='bandpass',
            fs=sample_rate,
            output='sos'
        )

        # Apply filter
        filtered = signal.sosfilt(sos, audio)
        return filtered

    def estimate_bpm(
        self,
        onset_samples: list[int],
        sample_rate: int,
        window_start_sample: int,
        window_end_sample: int,
    ) -> float | None:
        """Estimate BPM for a specific sample range using onset data.

        Args:
            onset_samples: List of onset positions in samples
            sample_rate: Sample rate of the audio
            window_start_sample: Start of the analysis window in samples
            window_end_sample: End of the analysis window in samples

        Returns:
            Estimated BPM as float, or None if estimation fails
        """
        # Filter onsets within the window
        window_onsets = [
            onset for onset in onset_samples
            if window_start_sample <= onset <= window_end_sample
        ]

        if len(window_onsets) < 4:  # Need at least 4 onsets for reliable BPM
            return None

        # Calculate inter-onset intervals (IOI) in seconds
        iois = []
        for i in range(1, len(window_onsets)):
            ioi_seconds = (window_onsets[i] - window_onsets[i-1]) / sample_rate
            iois.append(ioi_seconds)

        if not iois:
            return None

        # Estimate BPM from median IOI
        # BPM = 60 / median_IOI
        median_ioi = np.median(iois)
        bpm = 60.0 / median_ioi

        # Validate BPM range (reasonable for music: 60-200 BPM)
        if self.config.min_bpm <= bpm <= self.config.max_bpm:
            return float(bpm)

        return None

    def _create_single_speaking_section(self, audio_path: Path, sample_rate: int) -> SectionBoundaries:
        """Create a single speaking section for files with no detected clicks.

        Args:
            audio_path: Path to the audio file
            sample_rate: Sample rate

        Returns:
            SectionBoundaries with single speaking section
        """
        # Get total samples (this is approximate, but good enough for sectioning)
        import soundfile as sf
        with sf.SoundFile(str(audio_path)) as sf_file:
            total_samples = len(sf_file)

        boundaries = SectionBoundaries()
        boundaries.add_section(SectionInfo(
            section_number=1,
            start_sample=0,
            end_sample=total_samples,
            section_type=SectionType.SPEAKING,
            bpm=None
        ))
        return boundaries

    def _analyze_sections(self, onset_samples: list[int], sample_rate: int) -> SectionBoundaries:
        """Analyze onset data to create section boundaries.

        Args:
            onset_samples: List of onset positions in samples
            sample_rate: Sample rate

        Returns:
            SectionBoundaries with detected sections
        """
        boundaries = SectionBoundaries()

        if not onset_samples:
            return boundaries

        # Convert gap threshold to samples
        gap_threshold_samples = int(self.config.gap_threshold_seconds * sample_rate)

        # Initialize section tracking
        current_section_start = 0
        current_bpm = None
        section_number = 1

        # Process onsets to find section boundaries
        for i, onset in enumerate(onset_samples):
            # Check if this onset starts a new section
            if i == 0:
                # First onset - start first section
                current_section_start = 0
            else:
                # Check gap before this onset
                gap_samples = onset - onset_samples[i-1]
                if gap_samples >= gap_threshold_samples:
                    # Gap detected - end current section and start new one
                    self._add_section(
                        boundaries, section_number, current_section_start,
                        onset_samples[i-1], current_bpm, sample_rate
                    )
                    section_number += 1
                    current_section_start = onset
                    current_bpm = None

            # Estimate BPM for current section
            if current_bpm is None:
                # Try to estimate BPM from recent onsets
                bpm_window_samples = int(self.config.bpm_window_seconds * sample_rate)
                window_start = max(0, onset - bpm_window_samples // 2)
                window_end = onset + bpm_window_samples // 2

                estimated_bpm = self.estimate_bpm(
                    onset_samples, sample_rate, window_start, window_end
                )

                if estimated_bpm is not None:
                    # Check if BPM changed significantly
                    if current_bpm is not None:
                        bpm_change = abs(estimated_bpm - current_bpm)
                        if bpm_change >= self.config.bpm_change_threshold:
                            # BPM change detected - split section
                            self._add_section(
                                boundaries, section_number, current_section_start,
                                onset, current_bpm, sample_rate
                            )
                            section_number += 1
                            current_section_start = onset

                    current_bpm = estimated_bpm

        # Add final section
        if onset_samples:
            self._add_section(
                boundaries, section_number, current_section_start,
                onset_samples[-1], current_bpm, sample_rate
            )

        return boundaries

    def _add_section(
        self,
        boundaries: SectionBoundaries,
        section_number: int,
        start_sample: int,
        end_sample: int,
        bpm: float | None,
        sample_rate: int
    ) -> None:
        """Add a section to the boundaries.

        Args:
            boundaries: SectionBoundaries to add to
            section_number: Section number
            start_sample: Start sample
            end_sample: End sample
            bpm: BPM estimate
            sample_rate: Sample rate
        """
        section_type = SectionType.SONG if bpm is not None else SectionType.SPEAKING
        bpm_int = int(round(bpm)) if bpm is not None else None

        boundaries.add_section(SectionInfo(
            section_number=section_number,
            start_sample=start_sample,
            end_sample=end_sample,
            section_type=section_type,
            bpm=bpm_int
        ))

    def _merge_short_sections(self, boundaries: SectionBoundaries, sample_rate: int) -> SectionBoundaries:
        """Merge sections that are shorter than minimum length.

        Args:
            boundaries: Original section boundaries
            sample_rate: Sample rate

        Returns:
            Merged section boundaries
        """
        if not boundaries.sections:
            return boundaries

        merged = SectionBoundaries()
        current_section = boundaries.sections[0]

        for next_section in boundaries.sections[1:]:
            current_duration = current_section.get_duration_seconds(sample_rate)

            if current_duration < self.config.min_section_length_seconds:
                # Merge current section into next section
                next_section.start_sample = current_section.start_sample
                # Update section number and type based on merged content
                if current_section.section_type == SectionType.SONG:
                    next_section.section_type = SectionType.SONG
                    next_section.bpm = current_section.bpm
                current_section = next_section
            else:
                # Keep current section and start new merge group
                merged.add_section(current_section)
                current_section = next_section

        # Add the last section
        merged.add_section(current_section)

        # Renumber sections
        for i, section in enumerate(merged.sections, 1):
            section.section_number = i

        return merged