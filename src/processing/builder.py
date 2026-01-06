"""Track building orchestration for Channel Weaver."""

from pathlib import Path

from rich.console import Console

from typing import Protocol

from src.config import ChannelConfig, BusConfig, BitDepth
from src.processing.converters.factory import get_converter, resolve_bit_depth
from src.processing.mono import MonoTrackWriter
from src.processing.stereo import StereoTrackWriter
from src.output.protocols import MetadataWriterProtocol, OutputHandler
from src.output import ConsoleOutputHandler
from src.config import SegmentMap
from src.audio.click.models import SectionInfo


class TrackWriterProtocol(Protocol):
    """Protocol for track writers."""

    def write_tracks(self, channels_or_buses, segments: SegmentMap) -> None:
        """Write tracks for the given configurations and segments."""
        ...


class TrackBuilder:
    """Concatenate channel segments and construct mono or stereo bus tracks.

    This class concatenates the mono channel segments produced by AudioExtractor
    into final output tracks. It supports individual mono channel tracks and stereo bus
    tracks that combine left/right channels, applying filename sanitization and optional
    bit-depth conversion for the outputs.
    """

    mono_writer: TrackWriterProtocol
    stereo_writer: TrackWriterProtocol

    def __init__(
        self,
        sample_rate: int,
        *,
        bit_depth: BitDepth,
        source_bit_depth: BitDepth | None = None,
        temp_dir: Path,
        output_dir: Path,
        keep_temp: bool = False,
        console: Console | None = None,
        output_handler: OutputHandler | None = None,
        sections: list[SectionInfo] | None = None,
        metadata_writer: MetadataWriterProtocol | None = None,
    ) -> None:
        """Initialize the track builder.

        Args:
            sample_rate: Audio sample rate in Hz.
            bit_depth: Target bit depth for output files.
            source_bit_depth: Original bit depth of the source audio (used to resolve
                BitDepth.SOURCE).
            temp_dir: Directory containing temporary segment files.
            output_dir: Directory for final output track files.
            keep_temp: If True, preserves temporary files after processing.
            console: Optional Rich console for formatted output. Creates a new console
                if None is provided.
            output_handler: Optional output handler for dependency injection.
            sections: Optional list of section information for section-based output.
            metadata_writer: Optional metadata writer for embedding BPM information.
        """
        resolved_bit_depth = resolve_bit_depth(bit_depth, source_bit_depth)
        converter = get_converter(resolved_bit_depth)

        self.sample_rate = sample_rate
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        self.keep_temp = keep_temp
        self.sections = sections
        self.metadata_writer = metadata_writer

        # Use injected output handler or create default
        self._output_handler = output_handler or ConsoleOutputHandler(console)

        # Initialize specialized writers based on whether sections are provided
        if sections:
            from src.output.section_handler import SectionMonoTrackWriter, SectionStereoTrackWriter
            self.mono_writer: TrackWriterProtocol = SectionMonoTrackWriter(
                sections=sections,
                sample_rate=sample_rate,
                converter=converter,
                output_dir=output_dir,
                output_handler=self._output_handler,
            )
            self.stereo_writer: TrackWriterProtocol = SectionStereoTrackWriter(
                sections=sections,
                sample_rate=sample_rate,
                converter=converter,
                output_dir=output_dir,
                output_handler=self._output_handler,
            )
        else:
            self.mono_writer: TrackWriterProtocol = MonoTrackWriter(
                sample_rate=sample_rate,
                converter=converter,
                output_dir=output_dir,
                output_handler=self._output_handler,
            )
            self.stereo_writer: TrackWriterProtocol = StereoTrackWriter(
                sample_rate=sample_rate,
                converter=converter,
                output_dir=output_dir,
                output_handler=self._output_handler,
            )

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
        self.mono_writer.write_tracks(channels, segments)
        self.stereo_writer.write_tracks(buses, segments)

        # Apply BPM metadata if writer is provided and sections exist
        if self.metadata_writer and self.sections:
            self._apply_bpm_metadata()

        self._output_handler.info(f"Tracks written to {self.output_dir}")

    def _apply_bpm_metadata(self) -> None:
        """Apply BPM metadata to all generated WAV files based on section information."""
        if not self.metadata_writer or not self.sections:
            return

        # Find all WAV files in output directory (including section subdirs)
        wav_files = list(self.output_dir.rglob("*.wav"))

        for wav_file in wav_files:
            # Determine which section this file belongs to
            bpm = self._get_bpm_for_file(wav_file)
            if bpm is not None:
                success = self.metadata_writer.write_bpm(wav_file, bpm)
                if success:
                    self._output_handler.info(f"Embedded BPM={bpm} in {wav_file.name}")
                else:
                    self._output_handler.warning(f"Failed to embed BPM metadata in {wav_file.name}")

    def _get_bpm_for_file(self, wav_file: Path) -> int | None:
        """Determine the BPM for a given WAV file based on its path and section info.

        Args:
            wav_file: Path to the WAV file

        Returns:
            BPM value for the section this file belongs to, or None
        """
        # Extract section number from path (e.g., "section_01/file.wav" -> 1)
        parts = wav_file.parts
        section_part = None

        for part in parts:
            if part.startswith("section_"):
                section_part = part
                break

        if section_part and self.sections is not None:
            try:
                section_num = int(section_part.split("_")[1])
                # Find the section with this number (sections are 1-indexed)
                for section in self.sections:
                    if section.section_number == section_num:
                        return section.bpm
            except (ValueError, IndexError):
                pass

        # If no section found or file is not in a section directory,
        # check if there's only one section and apply its BPM
        if self.sections is not None and len(self.sections) == 1:
            return self.sections[0].bpm

        return None