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
    - Detect click onsets using envelope analysis and peak detection
    - Estimate BPM from inter-onset intervals
    - Identify section boundaries based on gaps between clicks
    - Detect trailing silence as speaking sections
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
            # Load entire audio file for holistic analysis
            audio, sr = sf.read(str(audio_path))
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            total_samples = len(audio)

            # Detect all onsets in the file
            onset_samples = self._detect_onsets(audio, sr)

            if not onset_samples:
                # No clicks detected - treat entire file as speaking section
                return self._create_single_speaking_section(total_samples)

            # Analyze sections based on onset gaps
            boundaries = self._analyze_sections(onset_samples, total_samples, sr)

            # Merge short sections if configured
            if self.config.min_section_length_seconds > 0:
                boundaries = self._merge_short_sections(boundaries, sr)

            return boundaries

        except Exception as e:
            raise AudioProcessingError(f"Failed to analyze click track: {e}") from e

    def _detect_onsets(self, audio: np.ndarray, sample_rate: int) -> list[int]:
        """Detect onset positions in the audio using envelope analysis.

        Args:
            audio: Audio samples (mono)
            sample_rate: Sample rate of the audio

        Returns:
            List of onset positions in samples
        """
        # Compute envelope using Hilbert transform
        envelope = np.abs(signal.hilbert(audio))

        # Smooth envelope with configurable window
        window_size = max(1, int(self.config.novelty_window * sample_rate))
        if window_size > 1:
            smoothed = signal.convolve(
                envelope, np.ones(window_size) / window_size, mode="same"
            )
        else:
            smoothed = envelope

        # Find onset peaks
        min_distance_samples = max(1, int(self.config.min_peak_distance * sample_rate))
        peaks, _ = signal.find_peaks(
            smoothed,
            distance=min_distance_samples,
            prominence=self.config.peak_prominence,
        )

        return peaks.tolist()

    def _analyze_sections(
        self, onset_samples: list[int], total_samples: int, sample_rate: int
    ) -> SectionBoundaries:
        """Analyze onset data to create section boundaries based on gaps and BPM changes.

        Gaps between click regions are treated as speaking sections.
        Leading and trailing silence are also treated as speaking sections.
        BPM changes within continuous click regions create new song sections.

        Args:
            onset_samples: List of onset positions in samples
            total_samples: Total number of samples in the file
            sample_rate: Sample rate

        Returns:
            SectionBoundaries with detected sections
        """
        boundaries = SectionBoundaries()

        if not onset_samples:
            return boundaries

        # Convert gap threshold to samples
        gap_threshold_samples = int(self.config.gap_threshold_seconds * sample_rate)

        # First, find song regions (clusters of onsets separated by gaps)
        song_regions: list[dict] = []
        current_onsets: list[int] = []

        for i, onset in enumerate(onset_samples):
            if i == 0:
                current_onsets.append(onset)
            else:
                gap = onset - onset_samples[i - 1]
                if gap >= gap_threshold_samples:
                    # Gap detected - finalize current song region
                    song_regions.append(
                        {
                            "start": current_onsets[0],
                            "end": current_onsets[-1] + int(0.1 * sample_rate),
                            "onsets": current_onsets.copy(),
                        }
                    )
                    current_onsets = [onset]
                else:
                    current_onsets.append(onset)

        # Add final song region
        if current_onsets:
            song_regions.append(
                {
                    "start": current_onsets[0],
                    "end": current_onsets[-1] + int(0.1 * sample_rate),
                    "onsets": current_onsets.copy(),
                }
            )

        # Split song regions by BPM changes
        split_song_regions: list[dict] = []
        for region in song_regions:
            sub_regions = self._split_by_bpm_changes(region, sample_rate)
            split_song_regions.extend(sub_regions)

        # Now build complete section list with speaking sections in gaps
        sections_data: list[dict] = []
        current_pos = 0

        for song_region in split_song_regions:
            # Check if there's a speaking section before this song
            if song_region["start"] - current_pos >= gap_threshold_samples:
                sections_data.append(
                    {
                        "start": current_pos,
                        "end": song_region["start"],
                        "onsets": [],
                        "type": SectionType.SPEAKING,
                    }
                )

            # Add the song section
            sections_data.append(
                {
                    "start": song_region["start"],
                    "end": song_region["end"],
                    "onsets": song_region["onsets"],
                    "type": SectionType.SONG,
                }
            )
            current_pos = song_region["end"]

        # Check for trailing silence (speaking section at end)
        if total_samples - current_pos >= gap_threshold_samples:
            sections_data.append(
                {
                    "start": current_pos,
                    "end": total_samples,
                    "onsets": [],
                    "type": SectionType.SPEAKING,
                }
            )

        # Calculate BPM and create SectionInfo objects
        for i, section_data in enumerate(sections_data, 1):
            bpm = None
            if (
                section_data["type"] == SectionType.SONG
                and len(section_data["onsets"]) >= 4
            ):
                bpm = self._estimate_bpm_from_onsets(
                    section_data["onsets"], sample_rate
                )

            boundaries.add_section(
                SectionInfo(
                    section_number=i,
                    start_sample=section_data["start"],
                    end_sample=section_data["end"],
                    section_type=section_data["type"],
                    bpm=int(round(bpm)) if bpm else None,
                )
            )

        return boundaries

    def _split_by_bpm_changes(
        self, region: dict, sample_rate: int
    ) -> list[dict]:
        """Split a song region into sub-regions based on BPM changes.

        Args:
            region: Dictionary with 'start', 'end', and 'onsets' keys
            sample_rate: Sample rate

        Returns:
            List of sub-region dictionaries
        """
        onsets = region["onsets"]

        # Need enough onsets to detect BPM changes
        if len(onsets) < 8:
            return [region]

        # Find BPM change points by analyzing inter-onset intervals
        change_indices = self._find_bpm_change_points(onsets, sample_rate)

        if not change_indices:
            return [region]

        # Split region at change points
        sub_regions: list[dict] = []
        prev_idx = 0

        for change_idx in change_indices:
            if change_idx > prev_idx and change_idx < len(onsets):
                sub_onsets = onsets[prev_idx:change_idx]
                if len(sub_onsets) >= 4:
                    sub_regions.append(
                        {
                            "start": sub_onsets[0],
                            "end": sub_onsets[-1] + int(0.1 * sample_rate),
                            "onsets": sub_onsets,
                        }
                    )
                prev_idx = change_idx

        # Add final sub-region
        if prev_idx < len(onsets):
            sub_onsets = onsets[prev_idx:]
            if len(sub_onsets) >= 4:
                sub_regions.append(
                    {
                        "start": sub_onsets[0],
                        "end": sub_onsets[-1] + int(0.1 * sample_rate),
                        "onsets": sub_onsets,
                    }
                )

        return sub_regions if sub_regions else [region]

    def _find_bpm_change_points(
        self, onsets: list[int], sample_rate: int
    ) -> list[int]:
        """Find indices where BPM changes significantly.

        Uses a sliding window to calculate local BPM and detects
        significant changes between consecutive windows.

        Args:
            onsets: List of onset sample positions
            sample_rate: Sample rate

        Returns:
            List of onset indices where BPM changes
        """
        if len(onsets) < 8:
            return []

        # Calculate inter-onset intervals
        iois = []
        for i in range(1, len(onsets)):
            ioi_seconds = (onsets[i] - onsets[i - 1]) / sample_rate
            if ioi_seconds > 0:
                iois.append(60.0 / ioi_seconds)  # Convert to BPM

        if len(iois) < 4:
            return []

        # Use a sliding window to calculate local median BPM
        window_size = max(4, min(16, len(iois) // 4))
        half_window = window_size // 2

        change_points: list[int] = []
        prev_bpm = None

        for i in range(len(iois)):
            # Calculate median BPM in window around this point
            start = max(0, i - half_window)
            end = min(len(iois), i + half_window + 1)
            window_bpms = iois[start:end]

            # Filter outliers (BPM outside valid range)
            valid_bpms = [
                b for b in window_bpms
                if self.config.min_bpm <= b <= self.config.max_bpm
            ]

            if not valid_bpms:
                continue

            current_bpm = float(np.median(valid_bpms))

            if prev_bpm is not None:
                bpm_diff = abs(current_bpm - prev_bpm)
                # Detect significant BPM change (threshold based on config)
                if bpm_diff >= self.config.bpm_change_threshold:
                    # Add 1 because iois index is offset from onsets index
                    change_points.append(i + 1)
                    prev_bpm = current_bpm
            else:
                prev_bpm = current_bpm

        # Filter out changes that are too close together (within 2 seconds)
        min_samples_between = int(2.0 * sample_rate)
        filtered_points: list[int] = []

        for idx in change_points:
            if idx >= len(onsets):
                continue
            if not filtered_points:
                filtered_points.append(idx)
            else:
                last_idx = filtered_points[-1]
                if onsets[idx] - onsets[last_idx] >= min_samples_between:
                    filtered_points.append(idx)

        return filtered_points

    def _estimate_bpm_from_onsets(
        self, onsets: list[int], sample_rate: int
    ) -> float | None:
        """Estimate BPM from a list of onset sample positions.

        Args:
            onsets: List of onset positions in samples
            sample_rate: Sample rate

        Returns:
            Estimated BPM or None if cannot be determined
        """
        if len(onsets) < 4:
            return None

        # Calculate inter-onset intervals in seconds
        iois = []
        for i in range(1, len(onsets)):
            ioi_seconds = (onsets[i] - onsets[i - 1]) / sample_rate
            iois.append(ioi_seconds)

        if not iois:
            return None

        # Use median IOI to estimate BPM
        median_ioi = float(np.median(iois))
        if median_ioi <= 0:
            return None

        bpm = 60.0 / median_ioi

        # Validate BPM range
        if self.config.min_bpm <= bpm <= self.config.max_bpm:
            return bpm

        return None

    def _create_single_speaking_section(self, total_samples: int) -> SectionBoundaries:
        """Create a single speaking section for files with no detected clicks.

        Args:
            total_samples: Total number of samples in the file

        Returns:
            SectionBoundaries with single speaking section
        """
        boundaries = SectionBoundaries()
        boundaries.add_section(
            SectionInfo(
                section_number=1,
                start_sample=0,
                end_sample=total_samples,
                section_type=SectionType.SPEAKING,
                bpm=None,
            )
        )
        return boundaries

    def _merge_short_sections(
        self, boundaries: SectionBoundaries, sample_rate: int
    ) -> SectionBoundaries:
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

    # Keep legacy methods for protocol compatibility
    def detect_onsets(self, audio_path: Path, sample_rate: int) -> list[int]:
        """Detect onset positions in the audio file.

        Args:
            audio_path: Path to the audio file to analyze
            sample_rate: Sample rate of the audio file

        Returns:
            List of onset positions in samples
        """
        try:
            audio, sr = sf.read(str(audio_path))
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            return self._detect_onsets(audio, sr)
        except Exception as e:
            raise AudioProcessingError(f"Failed to detect onsets: {e}") from e

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
            onset
            for onset in onset_samples
            if window_start_sample <= onset <= window_end_sample
        ]
        return self._estimate_bpm_from_onsets(window_onsets, sample_rate)
