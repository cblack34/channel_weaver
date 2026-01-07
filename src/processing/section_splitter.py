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
from src.output.protocols import MetadataWriterProtocol


class SectionSplitter:
    """Splits audio tracks into sections based on click track analysis.

    This class coordinates the section splitting process:
    1. Analyzes the click track to detect section boundaries
    2. Splits final output tracks at the detected boundaries
    3. Applies BPM metadata to section files
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

    def analyze_final_click_track(
        self,
        output_dir: Path,
        channels: list[ChannelConfig],
    ) -> list[SectionInfo]:
        """Analyze the final concatenated click track to get section boundaries.

        This method should be called AFTER TrackBuilder has created all tracks,
        so the click track is already concatenated into a single file.

        Args:
            output_dir: Directory containing the final output tracks
            channels: Channel configurations

        Returns:
            List of section information, or empty list if disabled or no sections found

        Raises:
            AudioProcessingError: If section splitting is enabled but fails
        """
        if not self.section_splitting.enabled:
            return []

        self.console.print("[dim]Section splitting enabled, analyzing click track...[/dim]")

        # Find the click channel
        click_channel = self._find_click_channel(channels)
        if click_channel is None:
            raise AudioProcessingError("No click channel found for section splitting")

        # Find the click track file in output directory
        click_track_path = self._find_click_track_file(output_dir, click_channel)
        if click_track_path is None:
            raise AudioProcessingError(
                f"Click track file not found in output directory for channel {click_channel.ch}"
            )

        self.console.print(f"[dim]Analyzing click track: {click_track_path.name}[/dim]")

        # Analyze the final concatenated click track
        sections = self._analyze_final_track(click_track_path)

        if not sections:
            self.console.print("[yellow]Warning: No sections detected in click track[/yellow]")
            return []

        self.console.print(f"[dim]Detected {len(sections)} sections[/dim]")
        return sections

    def _find_click_track_file(self, output_dir: Path, click_channel: ChannelConfig) -> Path | None:
        """Find the click track file in the output directory.

        Args:
            output_dir: Directory containing final output tracks
            click_channel: Click channel configuration

        Returns:
            Path to the click track file, or None if not found
        """
        from src.output.naming import sanitize_filename

        # Build the expected filename pattern
        output_ch = click_channel.output_ch or click_channel.ch
        sanitized_name = sanitize_filename(click_channel.name)
        expected_filename = f"{output_ch:02d}_{sanitized_name}.wav"

        click_track_path = output_dir / expected_filename
        if click_track_path.exists():
            return click_track_path

        # Try to find by channel number prefix as fallback
        for wav_file in output_dir.glob(f"{output_ch:02d}_*.wav"):
            return wav_file

        return None

    def _analyze_final_track(self, click_track_path: Path) -> list[SectionInfo]:
        """Analyze a single concatenated click track file.

        Args:
            click_track_path: Path to the final concatenated click track

        Returns:
            List of detected sections with metadata

        Raises:
            AudioProcessingError: If analysis fails
        """
        try:
            # Analyze the concatenated click track directly
            boundaries = self.analyzer.analyze(click_track_path, self.sample_rate)

            # Process sections (merge short ones, etc.)
            sections = SectionProcessor.process_sections(
                boundaries.sections,
                self.sample_rate,
                self.section_splitting.min_section_length_seconds,
            )

            return sections

        except Exception as e:
            raise AudioProcessingError(f"Failed to analyze click track: {e}") from e

    def analyze_click_track_if_enabled(
        self,
        segments: SegmentMap,
        channels: list[ChannelConfig],
    ) -> list[SectionInfo]:
        """Analyze click track to get section boundaries if section splitting is enabled.

        Args:
            segments: Original segments from AudioExtractor
            channels: Channel configurations

        Returns:
            List of section information, or empty list if disabled or no sections found

        Raises:
            AudioProcessingError: If section splitting is enabled but fails
        """
        if not self.section_splitting.enabled:
            return []

        self.console.print("[dim]Section splitting enabled, analyzing click track...[/dim]")

        # Find the click channel
        click_channel = self._find_click_channel(channels)
        if click_channel is None:
            raise AudioProcessingError("No click channel found for section splitting")

        # Analyze click track to get section boundaries
        sections = self._analyze_click_track(segments[click_channel.ch])

        if not sections:
            self.console.print("[yellow]Warning: No sections detected in click track[/yellow]")
            return []

        self.console.print(f"[dim]Detected {len(sections)} sections[/dim]")
        return sections

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

    def split_output_tracks_if_enabled(
        self,
        output_dir: Path,
        sections: list[SectionInfo],
    ) -> None:
        """Split final output tracks into sections if section splitting is enabled.

        Args:
            output_dir: Directory containing final output tracks
            sections: Section boundaries to split at

        Raises:
            AudioProcessingError: If splitting fails
        """
        if not sections:
            return

        self.console.print(f"[dim]Splitting {len(sections)} sections into subdirectories...[/dim]")

        # Find all WAV files in output directory (non-recursive, only top level)
        wav_files = list(output_dir.glob("*.wav"))

        for wav_file in wav_files:
            try:
                self._split_single_track(wav_file, sections, output_dir)
            except Exception as e:
                raise AudioProcessingError(f"Failed to split track {wav_file.name}: {e}") from e

        # Remove original files after successful splitting
        for wav_file in wav_files:
            wav_file.unlink()

        self.console.print(f"[dim]Split {len(wav_files)} tracks into {len(sections)} sections[/dim]")

    def _split_single_track(
        self,
        track_path: Path,
        sections: list[SectionInfo],
        output_base: Path,
    ) -> None:
        """Split a single audio track into section files.

        Args:
            track_path: Path to the track to split
            sections: Section boundaries
            output_base: Base output directory

        Raises:
            AudioProcessingError: If splitting fails
        """
        try:
            # Read the entire track (soundfile requires string paths)
            audio_data, sr = sf.read(str(track_path))

            if sr != self.sample_rate:
                raise AudioProcessingError(
                    f"Sample rate mismatch: {sr} vs {self.sample_rate}"
                )

            for section in sections:
                # Extract section audio
                start_sample = section.start_sample
                end_sample = min(section.end_sample, len(audio_data))

                if start_sample >= len(audio_data):
                    # Section starts beyond the end of audio
                    continue

                section_audio = audio_data[start_sample:end_sample]

                # Create section directory
                section_dir = output_base / f"section_{section.section_number:02d}"
                section_dir.mkdir(parents=True, exist_ok=True)

                # Create output path with same filename
                output_path = section_dir / track_path.name

                # Write section audio (soundfile requires string paths)
                sf.write(str(output_path), section_audio, sr)

        except Exception as e:
            raise AudioProcessingError(f"Failed to split {track_path.name}: {e}") from e

    def apply_metadata(
        self,
        output_dir: Path,
        sections: list[SectionInfo],
        metadata_writer: MetadataWriterProtocol,
    ) -> None:
        """Apply BPM metadata to all section files.

        Args:
            output_dir: Base output directory containing section folders
            sections: Section information with BPM data
            metadata_writer: Writer for embedding metadata
        """
        if not metadata_writer or not sections:
            return

        # Find all WAV files in section subdirectories
        wav_files = list(output_dir.rglob("*.wav"))

        for wav_file in wav_files:
            # Determine which section this file belongs to
            bpm = self._get_bpm_for_file(wav_file, sections)
            if bpm is not None:
                try:
                    metadata_writer.write_bpm(wav_file, bpm)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to write BPM to {wav_file.name}: {e}[/yellow]")

    def _get_bpm_for_file(self, wav_file: Path, sections: list[SectionInfo]) -> int | None:
        """Determine the BPM for a section file based on its path.

        Args:
            wav_file: Path to the WAV file
            sections: Section information

        Returns:
            BPM value for this file's section, or None
        """
        # Extract section number from path (e.g., section_01/file.wav -> section 1)
        parent_name = wav_file.parent.name
        if not parent_name.startswith("section_"):
            return None

        try:
            section_num = int(parent_name.split("_")[1])
            # Find matching section (sections are 1-indexed)
            for section in sections:
                if section.section_number == section_num:
                    return section.bpm
        except (ValueError, IndexError):
            pass

        return None

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
                self.console.print(f"[dim]Reading segment: {segment_path}[/dim]")
                # Retry reading the file in case of temporary issues
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        data, _ = sf.read(str(segment_path))  # Convert to string explicitly
                        self.console.print(f"[dim]Successfully read {len(data)} samples from {segment_path.name}[/dim]")
                        break
                    except Exception as read_e:
                        if attempt == max_retries - 1:
                            raise read_e
                        self.console.print(f"[dim]Retry {attempt + 1} reading {segment_path.name}[/dim]")
                        time.sleep(0.1)  # Wait 100ms before retry
                
                if data.ndim == 1:
                    # Mono audio
                    audio_data.append(data)
                else:
                    # Multi-channel, take first channel (should be mono anyway)
                    audio_data.append(data[:, 0])

            concatenated = np.concatenate(audio_data)
            self.console.print(f"[dim]Concatenated {len(audio_data)} segments into {len(concatenated)} samples[/dim]")

            # Write concatenated audio (soundfile requires string paths)
            sf.write(str(output_path), concatenated, self.sample_rate)
            self.console.print(f"[dim]Wrote concatenated audio to {output_path}[/dim]")

        except Exception as e:
            raise AudioProcessingError(f"Failed to concatenate click segments: {e}") from e