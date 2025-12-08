"""Core processing components for Channel Weaver.

This module provides the main processing pipeline for the Midas M32 multitrack processor.
It includes three main components:

1. ConfigLoader: Loads and validates user-editable channel and bus configuration data
2. AudioExtractor: Discovers WAV files and extracts mono channel segments
3. TrackBuilder: Concatenates segments into final mono and stereo output tracks

The processing pipeline follows this flow:
    Raw config dicts → ConfigLoader → validated ChannelConfig/BusConfig objects
    Input WAV files → AudioExtractor → mono channel segments
    Segments + config → TrackBuilder → final output tracks
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import re
import shutil
from typing import Iterable, Optional

import numpy as np
import soundfile as sf
from rich.console import Console
from tqdm import tqdm
import logging

from src.validators import ChannelValidator, BusValidator
from src.converters import get_converter, BitDepthConverter
from src.protocols import OutputHandler, ConsoleOutputHandler
from src.types import SegmentMap, ChannelData, BusData
from src.constants import AUDIO_CHUNK_SIZE
from src.exceptions import (
    ConfigError,
    ConfigValidationError,
    AudioProcessingError,
)
from src.models import (
    ChannelConfig,
    BusConfig,
    ChannelAction,
    BusSlot,
    BitDepth,
)


logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and validate user-editable channel and bus definitions.

    This class processes raw configuration dictionaries into validated Pydantic models,
    performs cross-validation between channels and buses, and auto-fills missing channels
    based on detected audio channel count.

    Attributes:
        _channels_data: Raw channel configuration dictionaries
        _buses_data: Raw bus configuration dictionaries
        _detected_channels: Number of channels detected in input audio (optional)
        _channel_validator: Validator for channel configurations
        _bus_validator: Validator for bus configurations
    """

    def __init__(
        self,
        channels_data: Iterable[ChannelData],
        buses_data: Iterable[BusData],
        *,
        detected_channel_count: int | None = None,
        channel_validator: ChannelValidator | None = None,
        bus_validator: BusValidator | None = None,
    ) -> None:
        """Initialize the configuration loader.

        Args:
            channels_data: Iterable of raw channel configuration dictionaries
            buses_data: Iterable of raw bus configuration dictionaries
            detected_channel_count: Number of channels detected in input audio files
            channel_validator: Custom channel validator (uses default if None)
            bus_validator: Custom bus validator (uses default if None)
        """
        self._channels_data = list(channels_data)
        self._buses_data = list(buses_data)
        self._detected_channels = detected_channel_count
        # Use injected validators or create defaults
        self._channel_validator = channel_validator or (
            ChannelValidator(detected_channel_count) if detected_channel_count is not None else None
        )
        self._bus_validator = bus_validator or (
            BusValidator(detected_channel_count) if detected_channel_count is not None else None
        )

    def load(self) -> tuple[list[ChannelConfig], list[BusConfig]]:
        """Return validated channel and bus configurations.

        Processes raw configuration data through validation and normalization,
        ensuring all channels are accounted for and bus assignments are valid.

        Returns:
            Tuple of (channels, buses) where channels includes auto-created entries
            for any missing channels detected in the audio.

        Raises:
            ConfigValidationError: If channel or bus configuration is invalid
        """

        channels = self._load_channels()
        buses = self._load_buses()

        self._channel_validator.validate(channels)
        bus_channels = self._collect_bus_channels(buses)
        self._bus_validator.validate_channels(bus_channels)
        self._bus_validator.validate_no_conflicts(channels, bus_channels)

        completed_channels = self._complete_channel_list(channels, bus_channels)
        return completed_channels, buses

    def _load_channels(self) -> list[ChannelConfig]:
        """Load channel configurations from raw data.

        Returns:
            List of ChannelConfig objects parsed from raw dictionaries.

        Raises:
            ConfigValidationError: If channel data cannot be parsed
        """

    def _load_buses(self) -> list[BusConfig]:
        """Load bus configurations from raw data.

        Returns:
            List of BusConfig objects parsed from raw dictionaries.

        Raises:
            ConfigValidationError: If bus data cannot be parsed
        """

    def _collect_bus_channels(self, buses: list[BusConfig]) -> list[int]:
        """Extract all channel numbers used in bus configurations.

        Args:
            buses: List of bus configurations to analyze

        Returns:
            Sorted list of unique channel numbers used in bus slots
        """

    def _complete_channel_list(
        self, channels: list[ChannelConfig], bus_channels: list[int]
    ) -> list[ChannelConfig]:
        """Complete channel list with auto-created entries for missing channels.

        Args:
            channels: Existing channel configurations
            bus_channels: Channel numbers referenced in bus configurations

        Returns:
            Complete list including auto-created channels for bus assignments
            and any missing channels up to detected_channel_count
        """


class AudioProcessingError(ConfigError):
    """Raised when audio files cannot be processed safely."""


def _sanitize_filename(name: str) -> str:
    """Return a filesystem-safe version of ``name``.

    Leading/trailing whitespace is trimmed, internal whitespace is collapsed, and any
    character outside of ``[A-Za-z0-9 _.-]`` is replaced with an underscore. Returns
    ``"track"`` if the sanitized result would otherwise be empty.
    """

    trimmed = re.sub(r"\s+", " ", name).strip()
    safe = re.sub(r"[^A-Za-z0-9 _.-]", "_", trimmed)
    return safe or "track"


def _resolve_bit_depth(requested: BitDepth, source: BitDepth | None) -> BitDepth:
    """Return an actionable bit depth, replacing ``SOURCE`` with ``source``."""

    if requested is BitDepth.SOURCE:
        if source is None:
            raise AudioProcessingError("Cannot resolve source bit depth before validating input files.")
        return source
    return requested


def _bit_depth_from_subtype(subtype: str) -> BitDepth:
    """Return a :class:`BitDepth` from a SoundFile subtype string."""

    normalized = subtype.upper()
    mapping = {
        "PCM_16": BitDepth.INT16,
        "PCM_24": BitDepth.INT24,
        "PCM_32": BitDepth.FLOAT32,
        "FLOAT": BitDepth.FLOAT32,
        "DOUBLE": BitDepth.FLOAT32,
    }
    try:
        return mapping[normalized]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise AudioProcessingError(f"Unsupported audio subtype: {subtype}") from exc


class AudioExtractor:
    """Discover WAV files and split multichannel content into mono segments.

    This class handles the discovery of sequential WAV files in an input directory,
    validates consistent audio parameters (sample rate, channel count, bit depth),
    and splits multichannel audio into individual mono channel segments stored in a
    temporary directory for later processing.
    """

    def __init__(
        self,
        input_dir: Path,
        temp_dir: Path,
        *,
        keep_temp: bool = False,
        console: Optional[Console] = None,
        output_handler: OutputHandler | None = None,
    ) -> None:
        """Initialize the audio extractor.

        Args:
            input_dir: Directory containing input WAV files
            temp_dir: Directory for temporary mono channel segments
            keep_temp: Whether to preserve temporary files after processing
            console: Rich console for output (optional, uses default if None)
            output_handler: Custom output handler (optional, uses console if None)
        """
        self.input_dir = input_dir
        self.temp_dir = temp_dir
        self.keep_temp = keep_temp
        self.console = console or Console()
        self._output_handler = output_handler or ConsoleOutputHandler(self.console)
        self._files: list[Path] | None = None
        self.sample_rate: int | None = None
        self.channels: int | None = None
        self.bit_depth: BitDepth | None = None

    def discover_and_validate(self) -> list[Path]:
        """Find sequential WAV files and validate shared audio parameters.

        Returns:
            list[Path]: A list of validated WAV file paths, sorted sequentially.
        """

        self._files = self._discover_files()
        if not self._files:
            raise AudioProcessingError(f"No WAV files found in {self.input_dir}")

        self._validate_audio_consistency(self._files)
        return self._files

    def _discover_files(self) -> list[Path]:
        """Discover and sort WAV files in the input directory.

        Returns:
            Sorted list of WAV file paths, ordered by numeric sequence in filename
        """
        wav_files = list(self.input_dir.glob("*.wav"))
        wav_files.sort(key=self._sort_key)
        return wav_files

    def _sort_key(self, path: Path) -> tuple[int | float, str]:
        """Generate sort key for WAV files based on numeric sequence.

        Args:
            path: File path to generate sort key for

        Returns:
            Tuple of (numeric_value, filename) for sorting WAV files in sequence
        """
        filename = path.stem
        # Find the first sequence of digits
        match = re.search(r'\d+', filename)
        if match:
            num = int(match.group())
        else:
            num = float('inf')  # Put files without numbers at the end
        return (num, filename)

    def _validate_audio_consistency(self, files: list[Path]) -> None:
        """Validate that all WAV files have consistent audio parameters.

        Args:
            files: List of WAV file paths to validate

        Raises:
            AudioProcessingError: If files have inconsistent sample rate, channels, or bit depth
        """
        expected_rate: int | None = None
        expected_channels: int | None = None
        expected_subtype: str | None = None

        for path in tqdm(files, desc="Validating audio files", unit="file"):
            info = sf.info(path)
            expected_rate = expected_rate or info.samplerate
            expected_channels = expected_channels or info.channels
            expected_subtype = expected_subtype or info.subtype

            if info.samplerate != expected_rate:
                raise AudioProcessingError(
                    f"Sample rate mismatch: {path.name} has {info.samplerate} Hz (expected {expected_rate})."
                )
            if info.channels != expected_channels:
                raise AudioProcessingError(
                    f"Channel count mismatch: {path.name} has {info.channels} channels (expected {expected_channels})."
                )
            if info.subtype != expected_subtype:
                raise AudioProcessingError(
                    f"Bit depth mismatch: {path.name} uses {info.subtype} (expected {expected_subtype})."
                )

        self.sample_rate = expected_rate
        self.channels = expected_channels
        self.bit_depth = _bit_depth_from_subtype(expected_subtype or "")
        logger.info(
            f"Input audio: {self.channels} channels @ {self.sample_rate} Hz, bit depth {self.bit_depth.value}."
        )

    def extract_segments(self, target_bit_depth: BitDepth | None = None) -> SegmentMap:
        """
        Split each input file into per-channel mono files in ``temp_dir``.

        Args:
            target_bit_depth (BitDepth | None): The desired bit depth for output files.
                If None, uses the source bit depth.
        Returns:
            dict[int, list[Path]]: Temporary segment paths keyed by channel number.
        """

        if not self._files:
            self.discover_and_validate()

        assert self.sample_rate is not None
        assert self.channels is not None
        requested_bit_depth = target_bit_depth or self.bit_depth or BitDepth.FLOAT32
        effective_bit_depth = _resolve_bit_depth(requested_bit_depth, self.bit_depth)
        converter = get_converter(effective_bit_depth)

        self.temp_dir.mkdir(parents=True, exist_ok=True)
        segments: SegmentMap = {ch: [] for ch in range(1, self.channels + 1)}

        for index, path in enumerate(tqdm(self._files, desc="Extracting channels", unit="file"), start=1):
            self._process_file_segments(path, index, segments, converter)

        self._output_handler.info(
            f"Wrote mono segments to {self.temp_dir} using bit depth {effective_bit_depth.value}."
        )
        return segments

    def _process_file_segments(
        self,
        path: Path,
        index: int,
        segments: SegmentMap,
        converter: BitDepthConverter,
    ) -> None:
        """Process a single file into per-channel segments.

        Args:
            path: Input WAV file path
            index: Sequential file index for naming segments
            segments: Dictionary to store segment paths by channel
            converter: Bit depth converter for output format
        """
        with ExitStack() as stack:
            writers = self._create_segment_writers(path, index, segments, converter, stack)
            self._process_file_chunks(path, writers, converter)

    def _create_segment_writers(
        self,
        path: Path,
        index: int,
        segments: SegmentMap,
        converter: BitDepthConverter,
        stack: ExitStack,
    ) -> dict[int, sf.SoundFile]:
        """Create SoundFile writers for each channel segment.

        Args:
            path: Input file path (used for naming context)
            index: Sequential file index
            segments: Dictionary to store segment paths by channel
            converter: Bit depth converter with SoundFile subtype
            stack: ExitStack for managing file handles

        Returns:
            Dictionary mapping channel numbers to SoundFile writers
        """
        writers: dict[int, sf.SoundFile] = {}
        for ch in range(1, self.channels + 1):
            segment_path = self.temp_dir / f"ch{ch:02d}_{index:04d}.wav"
            writers[ch] = stack.enter_context(
                sf.SoundFile(segment_path, "w", samplerate=self.sample_rate, channels=1, subtype=converter.soundfile_subtype)
            )
            segments[ch].append(segment_path)
        return writers

    def _process_file_chunks(
        self,
        path: Path,
        writers: dict[int, sf.SoundFile],
        converter: BitDepthConverter,
    ) -> None:
        """Process audio file in chunks, writing to segment files.

        Args:
            path: Input WAV file path to read from
            writers: Dictionary of channel writers for output segments
            converter: Bit depth converter for data transformation
        """
        with sf.SoundFile(path) as source:
            with tqdm(
                total=len(source),
                desc=f"{path.name}",
                unit="frame",
                leave=False,
            ) as progress:
                while True:
                    data = source.read(AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
                    if data.size == 0:
                        break
                    for ch, writer in writers.items():
                        mono = converter.convert(data[:, ch - 1])
                        writer.write(mono)
                    progress.update(len(data))

    def cleanup(self) -> None:
        """
        Delete temporary files unless ``keep_temp`` was requested.

        Removes the entire temporary directory tree if it exists and ``keep_temp`` is
        False, printing whether cleanup was performed or skipped.
        """

        if self.keep_temp:
            logger.info("Skipping temp cleanup (keep-temp enabled).")
            return
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Removed temporary directory {self.temp_dir}.")


class TrackBuilder:
    """Concatenate channel segments and construct mono or stereo bus tracks.

    This class concatenates the mono channel segments produced by :class:`AudioExtractor`
    into final output tracks. It supports individual mono channel tracks and stereo bus
    tracks that combine left/right channels, applying filename sanitization and optional
    bit-depth conversion for the outputs.
    """

    def __init__(
        self,
        sample_rate: int,
        *,
        bit_depth: BitDepth,
        source_bit_depth: BitDepth | None = None,
        temp_dir: Path,
        output_dir: Path,
        keep_temp: bool = False,
        console: Optional[Console] = None,
        output_handler: OutputHandler | None = None,
    ) -> None:
        """Initialize the track builder.

        Args:
            sample_rate: Audio sample rate in Hz.
            bit_depth: Target bit depth for output files.
            source_bit_depth: Original bit depth of the source audio (used to resolve
                :data:`BitDepth.SOURCE`).
            temp_dir: Directory containing temporary segment files.
            output_dir: Directory for final output track files.
            keep_temp: If True, preserves temporary files after processing.
            console: Optional Rich console for formatted output. Creates a new console
                if None is provided.
            output_handler: Optional output handler for dependency injection.
        """
        resolved_bit_depth = _resolve_bit_depth(bit_depth, source_bit_depth)
        self.converter = get_converter(resolved_bit_depth)
        self.sample_rate = sample_rate
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        self.keep_temp = keep_temp
        # Use injected output handler or create default
        self._output_handler = output_handler or ConsoleOutputHandler(console)
        self.console = self._output_handler  # Backward compatibility

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_tracks(
        self,
        channels: list[ChannelConfig],
        buses: list[BusConfig],
        segments: SegmentMap,
    ) -> None:
        """Build final output tracks from channel segments.

        Creates mono tracks for channels with PROCESS action and stereo bus tracks
        for configured buses by concatenating the appropriate channel segments.

        Args:
            channels: List of channel configurations
            buses: List of bus configurations
            segments: Dictionary mapping channel numbers to segment file lists
        """

    def _write_mono_tracks(self, channels: list[ChannelConfig], segments: SegmentMap) -> None:
        """Write individual mono tracks for channels with PROCESS action.

        Args:
            channels: List of channel configurations to process
            segments: Dictionary mapping channel numbers to segment file lists
        """

    def _write_buses(self, buses: list[BusConfig], segments: SegmentMap) -> None:
        """Write stereo bus tracks by combining left and right channel segments.

        Args:
            buses: List of bus configurations to process
            segments: Dictionary mapping channel numbers to segment file lists
        """

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

    def _write_stereo_file(self, bus: BusConfig, segments: SegmentMap, output_path: Path) -> None:
        """Write stereo bus file by interleaving left and right channels.

        Args:
            bus: Bus configuration with LEFT/RIGHT channel assignments
            segments: Dictionary mapping channel numbers to segment file lists
            output_path: Path for the output stereo WAV file
        """
        left_ch, right_ch, left_segments, right_segments = self._validate_bus_segments(bus, segments)
        
        with sf.SoundFile(output_path, "w", samplerate=self.sample_rate, channels=2, subtype=self.converter.soundfile_subtype) as dest:
            for left_path, right_path in zip(left_segments, right_segments):
                self._write_stereo_segments(dest, left_path, right_path, bus)

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
        with sf.SoundFile(left_path) as left_file, sf.SoundFile(right_path) as right_file:
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
