"""Audio parameter validation for Channel Weaver."""

from pathlib import Path
from typing import List

from tqdm import tqdm

from src.audio.info import AudioInfoRetriever
from src.config import BitDepth
from src.exceptions import AudioProcessingError


class AudioValidator:
    """Validate audio file parameters for consistency.

    Ensures all WAV files in a batch have consistent sample rate,
    channel count, and bit depth.
    """

    def __init__(self) -> None:
        """Initialize the audio validator."""
        self.info_retriever = AudioInfoRetriever()

    def validate_files(self, files: List[Path]) -> tuple[int, int, BitDepth]:
        """Validate that all WAV files have consistent audio parameters.

        Args:
            files: List of WAV file paths to validate

        Returns:
            Tuple of (sample_rate, channels, bit_depth) for the validated files

        Raises:
            AudioProcessingError: If files have inconsistent parameters or other issues
        """
        if not files:
            raise AudioProcessingError("No files to validate")

        expected_rate: int | None = None
        expected_channels: int | None = None
        expected_subtype: str | None = None

        for path in tqdm(files, desc="Validating audio files", unit="file"):
            if not path.exists():
                raise AudioProcessingError(f"Audio file does not exist: {path}")

            file_size = path.stat().st_size
            if file_size == 0:
                raise AudioProcessingError(f"Audio file is empty: {path}")

            info = self.info_retriever.get_info(path)

            # Set expected values from first file
            expected_rate = expected_rate or info.samplerate
            expected_channels = expected_channels or info.channels
            expected_subtype = expected_subtype or info.subtype

            # Validate consistency
            if info.samplerate != expected_rate:
                raise AudioProcessingError(
                    f"Sample rate mismatch: {path.name} has {info.samplerate} Hz "
                    f"(expected {expected_rate})."
                )
            if info.channels != expected_channels:
                raise AudioProcessingError(
                    f"Channel count mismatch: {path.name} has {info.channels} channels "
                    f"(expected {expected_channels})."
                )
            if info.subtype != expected_subtype:
                raise AudioProcessingError(
                    f"Bit depth mismatch: {path.name} uses {info.subtype} "
                    f"(expected {expected_subtype})."
                )

        # Convert subtype to BitDepth enum
        bit_depth = self._bit_depth_from_subtype(expected_subtype or "")

        return expected_rate, expected_channels, bit_depth

    def _bit_depth_from_subtype(self, subtype: str) -> BitDepth:
        """Convert soundfile subtype string to BitDepth enum.

        Args:
            subtype: Soundfile subtype string

        Returns:
            Corresponding BitDepth enum value
        """
        mapping = {
            "PCM_16": BitDepth.INT16,
            "PCM_24": BitDepth.INT24,
            "PCM_32": BitDepth.SOURCE,  # 32-bit signed integer
            "FLOAT": BitDepth.FLOAT32,
            "DOUBLE": BitDepth.FLOAT32,
        }
        return mapping.get(subtype.upper(), BitDepth.FLOAT32)