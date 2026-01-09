"""Section-based output handling for Channel Weaver."""

from pathlib import Path

from src.config import ChannelConfig, BusConfig
from src.config import SegmentMap
from src.audio.click.models import SectionInfo
from src.output.protocols import OutputHandler
from src.processing.mono import MonoTrackWriter
from src.processing.stereo import StereoTrackWriter


class SectionMonoTrackWriter(MonoTrackWriter):
    """Mono track writer that organizes output by sections."""

    def __init__(
        self,
        sections: list[SectionInfo],
        sample_rate: int,
        converter,
        output_dir: Path,
        output_handler: OutputHandler,
    ) -> None:
        """Initialize the section-aware mono track writer.

        Args:
            sections: List of section information
            sample_rate: Audio sample rate in Hz
            converter: Bit depth converter for output
            output_dir: Base output directory
            output_handler: Handler for output messages
        """
        # Initialize parent without sections parameter
        super().__init__(sample_rate, converter, output_dir, output_handler)
        self.sections = sections

    def write_tracks(self, channels: list[ChannelConfig], segments: SegmentMap) -> None:
        """Write individual mono tracks organized by sections.

        Args:
            channels: List of channel configurations to process
            segments: Dictionary mapping channel numbers to segment file lists
        """
        for section_idx, section in enumerate(self.sections):
            section_dir = self.output_dir / f"section_{section.section_number:02d}"
            section_dir.mkdir(parents=True, exist_ok=True)

            # Write tracks for this section
            self._write_section_tracks(channels, segments, section_idx, section_dir)

    def _write_section_tracks(
        self,
        channels: list[ChannelConfig],
        segments: SegmentMap,
        section_idx: int,
        section_dir: Path,
    ) -> None:
        """Write mono tracks for a specific section.

        Args:
            channels: List of channel configurations
            segments: Dictionary mapping channel numbers to segment file lists
            section_idx: Index of the section to write
            section_dir: Section directory to write to
        """
        from src.config import ChannelAction

        process_channels = [c for c in channels if c.action == ChannelAction.PROCESS]

        for ch_config in process_channels:
            ch = ch_config.ch
            ch_segments = segments.get(ch, [])

            # Get the segment for this section
            if section_idx < len(ch_segments):
                self._write_track_to_section(ch_config, ch_segments[section_idx], section_dir)

    def _write_track_to_section(
        self, ch_config: ChannelConfig, segment_path: Path, section_dir: Path
    ) -> None:
        """Write a single mono track segment to a section directory.

        Args:
            ch_config: Channel configuration
            segment_path: Path to the segment file for this section
            section_dir: Section directory to write to
        """
        from src.output.naming import build_output_path
        import soundfile as sf

        output_ch = ch_config.output_ch
        output_path = build_output_path(section_dir, output_ch, ch_config.name)  # type: ignore[arg-type]

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sf.SoundFile(
            str(output_path), "w",
            samplerate=self.sample_rate,
            channels=1,
            subtype=self.converter.soundfile_subtype
        ) as dest:
            self._concatenate_segment(dest, segment_path)


class SectionStereoTrackWriter(StereoTrackWriter):
    """Stereo track writer that organizes output by sections."""

    def __init__(
        self,
        sections: list[SectionInfo],
        sample_rate: int,
        converter,
        output_dir: Path,
        output_handler: OutputHandler,
    ) -> None:
        """Initialize the section-aware stereo track writer.

        Args:
            sections: List of section information
            sample_rate: Audio sample rate in Hz
            converter: Bit depth converter for output
            output_dir: Base output directory
            output_handler: Handler for output messages
        """
        # Initialize parent without sections parameter
        super().__init__(sample_rate, converter, output_dir, output_handler)
        self.sections = sections

    def write_tracks(self, buses: list[BusConfig], segments: SegmentMap) -> None:
        """Write stereo bus tracks organized by sections.

        Args:
            buses: List of bus configurations to process
            segments: Dictionary mapping channel numbers to segment file lists
        """
        for section_idx, section in enumerate(self.sections):
            section_dir = self.output_dir / f"section_{section.section_number:02d}"
            section_dir.mkdir(parents=True, exist_ok=True)

            # Write tracks for this section
            self._write_section_tracks(buses, segments, section_idx, section_dir)

    def _write_section_tracks(
        self,
        buses: list[BusConfig],
        segments: SegmentMap,
        section_idx: int,
        section_dir: Path,
    ) -> None:
        """Write stereo tracks for a specific section.

        Args:
            buses: List of bus configurations
            segments: Dictionary mapping channel numbers to segment file lists
            section_idx: Index of the section to write
            section_dir: Section directory to write to
        """
        for bus in buses:
            self._write_track_to_section(bus, segments, section_idx, section_dir)

    def _write_track_to_section(
        self, bus: BusConfig, segments: SegmentMap, section_idx: int, section_dir: Path
    ) -> None:
        """Write a single stereo bus track to a section directory.

        Args:
            bus: Bus configuration
            segments: Dictionary mapping channel numbers to segment file lists
            section_idx: Index of the section to write
            section_dir: Section directory to write to
        """
        from src.output.naming import build_bus_output_path
        import soundfile as sf

        left_ch, right_ch, left_segments, right_segments = self._validate_bus_segments(bus, segments)

        # Get the segments for this section
        if section_idx >= len(left_segments) or section_idx >= len(right_segments):
            self.output_handler.warning(f"No segments for section {section_idx + 1} in bus {bus.file_name}")
            return

        left_segment = left_segments[section_idx]
        right_segment = right_segments[section_idx]

        output_path = build_bus_output_path(section_dir, bus.file_name)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sf.SoundFile(
            str(output_path), "w",
            samplerate=self.sample_rate,
            channels=2,
            subtype=self.converter.soundfile_subtype
        ) as dest:
            self._write_stereo_segments(dest, left_segment, right_segment, bus)