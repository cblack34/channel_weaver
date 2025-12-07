"""Configuration utilities for the Midas M32 processor CLI.

This module defines the user-facing channel/bus configuration schema and a
robust loader that validates, normalizes, and auto-fills channel definitions
based on a detected channel count.
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

from .validators import ChannelValidator, BusValidator
from .converters import get_converter, BitDepthConverter
from .protocols import OutputHandler, ConsoleOutputHandler

from src.exceptions import *
from src.models import *


logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and validate user-editable channel and bus definitions."""

    def __init__(
        self,
        channels_data: Iterable[dict[str, object]],
        buses_data: Iterable[dict[str, object]],
        *,
        detected_channel_count: int | None = None,
        channel_validator: ChannelValidator | None = None,
        bus_validator: BusValidator | None = None,
    ) -> None:
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
        """Return validated channel and bus configurations."""

        channels = self._load_channels()
        buses = self._load_buses()

        self._channel_validator.validate(channels)
        bus_channels = self._collect_bus_channels(buses)
        self._bus_validator.validate_channels(bus_channels)
        self._bus_validator.validate_no_conflicts(channels, bus_channels)

        completed_channels = self._complete_channel_list(channels, bus_channels)
        return completed_channels, buses

    def _load_channels(self) -> list[ChannelConfig]:
        try:
            return [ChannelConfig(**channel_dict) for channel_dict in self._channels_data]
        except ValidationError as exc:  # pragma: no cover - defensive
            raise ConfigValidationError("Invalid channel configuration.", errors=exc) from exc

    def _load_buses(self) -> list[BusConfig]:
        try:
            return [BusConfig(**bus_dict) for bus_dict in self._buses_data]
        except ValidationError as exc:  # pragma: no cover - defensive
            raise ConfigValidationError("Invalid bus configuration.", errors=exc) from exc

    def _collect_bus_channels(self, buses: list[BusConfig]) -> list[int]:
        channels: list[int] = []
        for bus in buses:
            channels.extend(bus.slots.values())
        return channels

    def _complete_channel_list(
        self, channels: list[ChannelConfig], bus_channels: list[int]
    ) -> list[ChannelConfig]:
        channels_by_number = {channel.ch: channel for channel in channels}

        for ch in bus_channels:
            if ch not in channels_by_number:
                logger.warning("Auto-creating channel %02d for bus assignment with action=BUS.", ch)
                channels_by_number[ch] = ChannelConfig(ch=ch, name=f"Ch {ch:02d}", action=ChannelAction.BUS)

        for ch in range(1, self._detected_channels + 1):
            if ch not in channels_by_number:
                logger.warning("Auto-creating missing channel %02d with action=PROCESS.", ch)
                channels_by_number[ch] = ChannelConfig(ch=ch, name=f"Ch {ch:02d}")

        return sorted(channels_by_number.values(), key=lambda config: config.ch)


class AudioProcessingError(ConfigError):
    """Raised when audio files cannot be processed safely."""


_AUDIO_CHUNK_SIZE = 131072  # frames processed per read operation


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
        self.input_dir = input_dir
        self.temp_dir = temp_dir
        self.keep_temp = keep_temp
        # Use injected output handler or create default
        self._output_handler = output_handler or ConsoleOutputHandler(console)
        self.console = self._output_handler  # Backward compatibility

        self.sample_rate: int | None = None
        self.bit_depth: BitDepth | None = None
        self.channels: int | None = None
        self._files: list[Path] = []

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
        wav_files = [path for path in self.input_dir.iterdir() if path.suffix.lower() == ".wav"]
        sorted_files = sorted(wav_files, key=self._sort_key)

        self.console.print(f"Discovered {len(sorted_files)} input files in [bold]{self.input_dir}[/bold].")
        return sorted_files

    def _sort_key(self, path: Path) -> tuple[int | float, str]:
        match = re.search(r"(\d+)", path.stem)
        if match:
            return int(match.group(1)), path.name
        return float('inf'), path.name

    def _validate_audio_consistency(self, files: list[Path]) -> None:
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
        self.console.print(
            f"Input audio: [bold]{self.channels}[/bold] channels @ [bold]{self.sample_rate} Hz[/bold], bit depth [bold]{self.bit_depth.value}[/bold]."
        )

    def extract_segments(self, target_bit_depth: BitDepth | None = None) -> dict[int, list[Path]]:
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
        segments: dict[int, list[Path]] = {ch: [] for ch in range(1, self.channels + 1)}

        for index, path in enumerate(tqdm(self._files, desc="Extracting channels", unit="file"), start=1):
            with ExitStack() as stack:
                writers: dict[int, sf.SoundFile] = {}
                for ch in range(1, self.channels + 1):
                    segment_path = self.temp_dir / f"ch{ch:02d}_{index:04d}.wav"
                    writers[ch] = stack.enter_context(
                        sf.SoundFile(segment_path, "w", samplerate=self.sample_rate, channels=1, subtype=converter.soundfile_subtype)
                    )
                    segments[ch].append(segment_path)

                with sf.SoundFile(path) as source:
                    with tqdm(
                        total=len(source),
                        desc=f"{path.name}",
                        unit="frame",
                        leave=False,
                    ) as progress:
                        while True:
                            data = source.read(_AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
                            if data.size == 0:
                                break
                            for ch, writer in writers.items():
                                mono = converter.convert(data[:, ch - 1])
                                writer.write(mono)
                            progress.update(len(data))

        self.console.print(
            f"Wrote mono segments to [bold]{self.temp_dir}[/bold] using bit depth [bold]{effective_bit_depth.value}[/bold]."
        )
        return segments

    def cleanup(self) -> None:
        """
        Delete temporary files unless ``keep_temp`` was requested.

        Removes the entire temporary directory tree if it exists and ``keep_temp`` is
        False, printing whether cleanup was performed or skipped.
        """

        if self.keep_temp:
            self.console.print("Skipping temp cleanup (keep-temp enabled).")
            return
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.console.print(f"Removed temporary directory {self.temp_dir}.")


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
        segments: dict[int, list[Path]],
    ) -> None:
        self._write_mono_tracks(channels, segments)
        self._write_buses(buses, segments)

    def _write_mono_tracks(self, channels: list[ChannelConfig], segments: dict[int, list[Path]]) -> None:
        for channel in tqdm(channels, desc="Writing mono tracks"):
            if channel.action is not ChannelAction.PROCESS:
                continue

            ch_segments = segments.get(channel.ch, [])
            if not ch_segments:
                raise AudioProcessingError(f"No segments available for channel {channel.ch} ({channel.name}).")

            filename = f"{channel.ch:02d}_{_sanitize_filename(channel.name)}.wav"
            output_path = self.output_dir / filename

            with sf.SoundFile(output_path, "w", samplerate=self.sample_rate, channels=1, subtype=self.converter.soundfile_subtype) as dest:
                for segment in ch_segments:
                    with sf.SoundFile(segment) as source:
                        while True:
                            data = source.read(_AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
                            if data.size == 0:
                                break
                            converted_data = self.converter.convert(data[:, 0])
                            dest.write(converted_data.astype(self.converter.numpy_dtype, copy=False))

            self.console.print(f"Created mono track [green]{output_path.name}[/green].")

    def _write_buses(self, buses: list[BusConfig], segments: dict[int, list[Path]]) -> None:
        if not buses:
            return

        for bus in tqdm(buses, desc="Writing stereo buses"):
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

            output_path = self.output_dir / f"{_sanitize_filename(bus.file_name)}.wav"
            with sf.SoundFile(output_path, "w", samplerate=self.sample_rate, channels=2, subtype=self.converter.soundfile_subtype) as dest:
                for left_path, right_path in zip(left_segments, right_segments):
                    with sf.SoundFile(left_path) as left_file, sf.SoundFile(right_path) as right_file:
                        while True:
                            left_data = left_file.read(_AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
                            right_data = right_file.read(_AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
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

            self.console.print(f"Created stereo bus [cyan]{output_path.name}[/cyan].")
