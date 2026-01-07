"""Section splitting logic for click-based audio segmentation."""

import time
from pathlib import Path

import numpy as np
import soundfile as sf
from rich.console import Console

from src.audio.click.analyzer import ScipyClickAnalyzer
from src.audio.click.models import SectionInfo
from src.audio.click.section_processor import SectionProcessor
from src.config import ChannelConfig, SegmentMap
from src.config.models import SectionSplittingConfig
from src.config.enums import ChannelAction
from src.exceptions import AudioProcessingError


class SectionSplitter:
    """Splits audio segments into sections based on click track analysis.

    This class coordinates the section splitting process:
    1. Identifies the click channel from configuration
    2. Analyzes the click track to detect section boundaries
    3. Splits all audio segments at the detected boundaries
    4. Returns the split segments for track building
    """

    def __init__(
        self,
        sample_rate: int,
        temp_dir: Path,
        section_splitting: SectionSplittingConfig,
        console: Console | None = None,
    ) -> None:
        """Initialize the section splitter.

        Args:
            sample_rate: Audio sample rate in Hz
            temp_dir: Directory for temporary files
            section_splitting: Section splitting configuration
            console: Optional Rich console for output
        """
        self.sample_rate = sample_rate
        self.temp_dir = temp_dir
        self.section_splitting = section_splitting
        self.console = console or Console()

        # Create analyzer and processor
        self.analyzer = ScipyClickAnalyzer(section_splitting)
        self.processor = SectionProcessor()

    def split_segments_if_enabled(
        self,
        segments: SegmentMap,
        channels: list[ChannelConfig],
    ) -> tuple[SegmentMap, list[SectionInfo]]:
        """Split segments into sections if section splitting is enabled.

        Args:
            segments: Original segments from AudioExtractor
            channels: Channel configurations

        Returns:
            Tuple of (split_segments, section_info) where split_segments
            contains the section-split segments and section_info contains
            metadata about each section.

        Raises:
            AudioProcessingError: If section splitting fails
        """
        if not self.section_splitting.enabled:
            # Return original segments with empty section info
            return segments, []

        self.console.print("[dim]Section splitting enabled, analyzing click track...[/dim]")

        # Find the click channel
        click_channel = self._find_click_channel(channels)
        if click_channel is None:
            raise AudioProcessingError("No click channel found for section splitting")

        # Analyze click track to get section boundaries
        sections = self._analyze_click_track(segments[click_channel.ch])

        if not sections:
            self.console.print("[yellow]Warning: No sections detected in click track[/yellow]")
            return segments, []

        # Split all segments at the detected boundaries
        split_segments = self._split_all_segments(segments, sections)

        self.console.print(f"[dim]Split into {len(sections)} sections[/dim]")
        return split_segments, sections

    def _find_click_channel(self, channels: list[ChannelConfig]) -> ChannelConfig | None:
        """Find the channel configured as the click track.

        Args:
            channels: List of channel configurations

        Returns:
            The click channel configuration, or None if not found
        """
        for channel in channels:
            if channel.action == ChannelAction.CLICK:
                return channel
        return None

    def _analyze_click_track(self, click_segments: list[Path]) -> list[SectionInfo]:
        """Analyze the click track segments to detect section boundaries.

        Args:
            click_segments: List of click channel segment files

        Returns:
            List of detected sections with metadata

        Raises:
            AudioProcessingError: If analysis fails
        """
        # Concatenate all click segments into a temporary file for analysis
        click_concat_path = self.temp_dir / "click_concat.wav"
        try:
            self._concatenate_segments(click_segments, click_concat_path)

            # Analyze the concatenated click track
            boundaries = self.analyzer.analyze(click_concat_path, self.sample_rate)

            # Process sections (merge short ones, etc.)
            sections = SectionProcessor.process_sections(
                boundaries.sections,
                self.sample_rate,
                self.section_splitting.min_section_length_seconds,
            )

            return sections

        finally:
            # Clean up temporary file
            if click_concat_path.exists():
                click_concat_path.unlink()

    def _concatenate_segments(self, segments: list[Path], output_path: Path) -> None:
        """Concatenate multiple audio segments into a single file.

        Args:
            segments: List of segment files to concatenate
            output_path: Path for the concatenated output file

        Raises:
            AudioProcessingError: If concatenation fails
        """
        if not segments:
            raise AudioProcessingError("No segments to concatenate")

        try:
            # Read all segments and concatenate
            audio_data = []
            for segment_path in segments:
                # Retry reading the file in case of temporary issues
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        data, _ = sf.read(segment_path)
                        break
                    except Exception as read_e:
                        if attempt == max_retries - 1:
                            raise read_e
                        time.sleep(0.1)  # Wait 100ms before retry
                
                if data.ndim == 1:
                    # Mono audio
                    audio_data.append(data)
                else:
                    # Multi-channel, take first channel (should be mono anyway)
                    audio_data.append(data[:, 0])

            concatenated = np.concatenate(audio_data)

            # Write concatenated audio
            sf.write(output_path, concatenated, self.sample_rate)

        except Exception as e:
            raise AudioProcessingError(f"Failed to concatenate click segments: {e}") from e

    def _split_all_segments(
        self,
        segments: SegmentMap,
        sections: list[SectionInfo]
    ) -> SegmentMap:
        """Split all audio segments at the detected section boundaries.

        Args:
            segments: Original segments keyed by channel number
            sections: Detected section boundaries

        Returns:
            Split segments organized by channel and section

        Raises:
            AudioProcessingError: If splitting fails
        """
        split_segments: SegmentMap = {}

        # Get total length of original concatenated audio
        total_samples = self._get_total_samples(segments)

        for channel_num, channel_segments in segments.items():
            split_segments[channel_num] = []

            # Concatenate this channel's segments for splitting
            channel_concat_path = self.temp_dir / f"ch{channel_num:02d}_concat.wav"
            try:
                self._concatenate_segments(channel_segments, channel_concat_path)

                # Split the concatenated channel audio at section boundaries
                section_files = self._split_channel_audio(
                    channel_concat_path, sections, channel_num, total_samples
                )

                split_segments[channel_num] = section_files

            finally:
                # Clean up temporary file
                if channel_concat_path.exists():
                    channel_concat_path.unlink()

        return split_segments

    def _get_total_samples(self, segments: SegmentMap) -> int:
        """Get the total number of samples across all segments for a channel.

        Args:
            segments: Segments for all channels

        Returns:
            Total sample count (assumes all channels have same length)
        """
        # Use the first channel to determine total length
        first_channel_segments = next(iter(segments.values()))
        total_samples = 0
        for segment_path in first_channel_segments:
            with sf.SoundFile(segment_path) as f:
                total_samples += len(f)
        return total_samples

    def _split_channel_audio(
        self,
        channel_concat_path: Path,
        sections: list[SectionInfo],
        channel_num: int,
        total_samples: int
    ) -> list[Path]:
        """Split a single channel's concatenated audio into section files.

        Args:
            channel_concat_path: Path to concatenated channel audio
            sections: Section boundaries
            channel_num: Channel number for naming
            total_samples: Total samples in the concatenated audio

        Returns:
            List of section audio files

        Raises:
            AudioProcessingError: If splitting fails
        """
        section_files = []

        try:
            # Read the entire concatenated audio
            audio_data, _ = sf.read(channel_concat_path)

            for section_idx, section in enumerate(sections, start=1):
                # Extract section audio
                start_sample = section.start_sample
                end_sample = min(section.end_sample, len(audio_data))

                if start_sample >= len(audio_data):
                    # Section starts beyond the end of audio
                    continue

                section_audio = audio_data[start_sample:end_sample]

                # Create section file path
                section_filename = f"ch{channel_num:02d}_section{section_idx:04d}.wav"
                section_path = self.temp_dir / section_filename

                # Write section audio
                sf.write(section_path, section_audio, self.sample_rate)
                section_files.append(section_path)

        except Exception as e:
            raise AudioProcessingError(f"Failed to split channel {channel_num}: {e}") from e

        return section_files