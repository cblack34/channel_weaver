"""Protocol definitions for click track analysis."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from src.audio.click.models import SectionBoundaries


@runtime_checkable
class ClickAnalyzerProtocol(Protocol):
    """Protocol for click track analysis implementations.

    This protocol defines the interface that all click analyzers must implement.
    Following the Dependency Inversion Principle, the section splitting logic
    depends on this abstraction rather than concrete implementations.

    Implementations include:
    - AubioClickAnalyzer: Uses aubio library for onset detection and BPM estimation
    - (Future) LibrosaClickAnalyzer, MockClickAnalyzer, etc.
    """

    def analyze(self, audio_path: Path, sample_rate: int) -> SectionBoundaries:
        """Analyze audio file and return section boundaries based on click track.

        Args:
            audio_path: Path to the audio file to analyze
            sample_rate: Sample rate of the audio file

        Returns:
            SectionBoundaries containing detected sections with timing and BPM info

        Raises:
            AudioProcessingError: If audio analysis fails
        """
        ...

    def detect_onsets(self, audio_path: Path, sample_rate: int) -> list[int]:
        """Detect onset positions in the audio file.

        Args:
            audio_path: Path to the audio file to analyze
            sample_rate: Sample rate of the audio file

        Returns:
            List of onset positions in samples (not seconds) for maximum precision

        Raises:
            AudioProcessingError: If onset detection fails
        """
        ...

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

        Raises:
            AudioProcessingError: If BPM estimation fails
        """
        ...