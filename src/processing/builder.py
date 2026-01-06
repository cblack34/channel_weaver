"""Track building orchestration for Channel Weaver."""

from pathlib import Path

from rich.console import Console

from typing import Protocol

from src.config import ChannelConfig, BusConfig, BitDepth
from src.processing.converters.factory import get_converter, resolve_bit_depth
from src.processing.mono import MonoTrackWriter
from src.processing.stereo import StereoTrackWriter
from src.output import OutputHandler, ConsoleOutputHandler
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
        """
        resolved_bit_depth = resolve_bit_depth(bit_depth, source_bit_depth)
        converter = get_converter(resolved_bit_depth)

        self.sample_rate = sample_rate
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        self.keep_temp = keep_temp
        self.sections = sections

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
        self._output_handler.info(f"Tracks written to {self.output_dir}")