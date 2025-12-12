"""Stereo bus track writing for Channel Weaver."""

from pathlib import Path

import numpy as np
import soundfile as sf
from tqdm import tqdm

from src.config import BusConfig, BusSlot
from src.constants import AUDIO_CHUNK_SIZE
from src.exceptions import AudioProcessingError
from src.output.naming import build_bus_output_path
from src.processing.converters.protocols import BitDepthConverter
from src.protocols import OutputHandler
from src.types import SegmentMap


class StereoTrackWriter:
    """Write stereo bus tracks by combining left and right channel segments."""

    def __init__(
        self,
        sample_rate: int,
        converter: BitDepthConverter,
        output_dir: Path,
        output_handler: OutputHandler
    ) -> None:
        """Initialize the stereo track writer.

        Args:
            sample_rate: Audio sample rate in Hz
            converter: Bit depth converter for output
            output_dir: Directory for output files
            output_handler: Handler for output messages
        """
        self.sample_rate = sample_rate
        self.converter = converter
        self.output_dir = output_dir
        self.output_handler = output_handler

    def write_tracks(self, buses: list[BusConfig], segments: SegmentMap) -> None:
        """Write stereo bus tracks.

        Args:
            buses: List of bus configurations to process
            segments: Dictionary mapping channel numbers to segment file lists
        """
        for bus in tqdm(buses, desc="Building bus tracks", unit="bus"):
            self._write_track(bus, segments)

    def _write_track(self, bus: BusConfig, segments: SegmentMap) -> None:
        """Write a single stereo bus track.

        Args:
            bus: Bus configuration
            segments: Dictionary mapping channel numbers to segment file lists
        """
        left_ch, right_ch, left_segments, right_segments = self._validate_bus_segments(bus, segments)

        output_path = build_bus_output_path(self.output_dir, bus.file_name)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sf.SoundFile(
            str(output_path), "w",
            samplerate=self.sample_rate,
            channels=2,
            subtype=self.converter.soundfile_subtype
        ) as dest:
            for left_path, right_path in zip(left_segments, right_segments):
                self._write_stereo_segments(dest, left_path, right_path, bus)

    def _validate_bus_segments(self, bus: BusConfig, segments: SegmentMap) -> tuple[int, int, list[Path], list[Path]]:
        """Validate bus configuration and return segment information.

        Args:
            bus: Bus configuration to validate
            segments: Dictionary mapping channel numbers to segment file lists

        Returns:
            Tuple of (left_channel, right_channel, left_segments, right_segments)

        Raises:
            AudioProcessingError: If bus configuration is invalid or segments are missing
        """
        left_ch = bus.slots.get(BusSlot.LEFT)
        right_ch = bus.slots.get(BusSlot.RIGHT)
        if left_ch is None or right_ch is None:
            raise AudioProcessingError(f"Bus {bus.file_name} is missing LEFT or RIGHT channel assignments.")

        left_segments = segments.get(left_ch, [])
        right_segments = segments.get(right_ch, [])
        if len(left_segments) != len(right_segments):
            raise AudioProcessingError(
                f"Bus {bus.file_name} segment mismatch: {len(left_segments)} left vs {len(right_segments)} right files."
            )
        return left_ch, right_ch, left_segments, right_segments

    def _write_stereo_segments(self, dest: sf.SoundFile, left_path: Path, right_path: Path, bus: BusConfig) -> None:
        """Write stereo segments from left and right files to destination.

        Args:
            dest: Output SoundFile for stereo data
            left_path: Path to left channel segment file
            right_path: Path to right channel segment file
            bus: Bus configuration for error reporting

        Raises:
            AudioProcessingError: If segment lengths don't match
        """
        with sf.SoundFile(str(left_path)) as left_file, sf.SoundFile(str(right_path)) as right_file:
            while True:
                left_data = left_file.read(AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
                right_data = right_file.read(AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
                if len(left_data) == 0 and len(right_data) == 0:
                    break
                if len(left_data) == 0 or len(right_data) == 0:
                    raise AudioProcessingError(
                        f"Bus {bus.file_name} segment length mismatch: one channel ended prematurely"
                    )
                if len(left_data) != len(right_data):
                    raise AudioProcessingError(
                        f"Bus {bus.file_name} audio chunk mismatch: left chunk has {len(left_data)} samples, right chunk has {len(right_data)} samples."
                    )
                stereo = np.column_stack((left_data[:, 0], right_data[:, 0]))
                converted_stereo = self.converter.convert(stereo)
                dest.write(converted_stereo.astype(self.converter.numpy_dtype, copy=False))