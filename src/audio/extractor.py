"""Audio extraction orchestration for Channel Weaver."""

from pathlib import Path
from typing import Optional

from rich.console import Console
from tqdm import tqdm

from src.audio.discovery import AudioFileDiscovery
from src.audio.ffmpeg.commands import FFmpegCommandBuilder
from src.audio.ffmpeg.executor import FFmpegExecutor
from src.audio.validation import AudioValidator
from src.config import BitDepth
from src.processing.converters import get_converter
from src.exceptions import AudioProcessingError
from src.output import OutputHandler, ConsoleOutputHandler
from src.config import SegmentMap


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

        # Initialize components
        self.discovery = AudioFileDiscovery(input_dir)
        self.validator = AudioValidator()
        self.command_builder = FFmpegCommandBuilder()
        self.executor = FFmpegExecutor(self._output_handler)

        # State
        self._files: list[Path] | None = None
        self.sample_rate: int | None = None
        self.channels: int | None = None
        self.bit_depth: BitDepth | None = None

    def discover_and_validate(self) -> list[Path]:
        """Find sequential WAV files and validate shared audio parameters.

        Returns:
            list[Path]: A list of validated WAV file paths, sorted sequentially.

        Raises:
            AudioProcessingError: If no files found or validation fails
        """
        self._files = self.discovery.discover_files()
        if not self._files:
            raise AudioProcessingError(f"No WAV files found in {self.input_dir}")

        self.sample_rate, self.channels, self.bit_depth = self.validator.validate_files(self._files)
        self._output_handler.info(
            f"Input audio: {self.channels} channels @ {self.sample_rate} Hz, "
            f"bit depth {self.bit_depth.value}."
        )
        return self._files

    def extract_segments(self, target_bit_depth: BitDepth | None = None) -> SegmentMap:
        """Split each input file into per-channel mono files in temp_dir.

        Args:
            target_bit_depth: The desired bit depth for output files.
                If None, uses the source bit depth.

        Returns:
            dict[int, list[Path]]: Temporary segment paths keyed by channel number.

        Raises:
            AudioProcessingError: If extraction fails
        """
        if not self._files:
            self.discover_and_validate()

        assert self.sample_rate is not None
        assert self.channels is not None
        assert self.bit_depth is not None

        requested_bit_depth = target_bit_depth or self.bit_depth
        effective_bit_depth = self._resolve_bit_depth(requested_bit_depth, self.bit_depth)
        converter = get_converter(effective_bit_depth)

        self.temp_dir.mkdir(parents=True, exist_ok=True)
        segments: SegmentMap = {ch: [] for ch in range(1, self.channels + 1)}

        for index, path in enumerate(tqdm(self._files, desc="Extracting channels", unit="file"), start=1):
            self._process_file_segments(path, index, segments, effective_bit_depth)

        self._output_handler.info(
            f"Wrote mono segments to {self.temp_dir} using bit depth {effective_bit_depth.value}."
        )
        return segments

    def _process_file_segments(
        self,
        path: Path,
        index: int,
        segments: SegmentMap,
        bit_depth: BitDepth,
    ) -> None:
        """Process a single file into per-channel segments using ffmpeg.

        Args:
            path: Input WAV file path
            index: Sequential file index for naming segments
            segments: Dictionary to store segment paths by channel
            bit_depth: Target bit depth for output files
        """
        command = self.command_builder.build_channel_split_command(
            input_path=path,
            output_dir=self.temp_dir,
            file_index=index,
            channels=self.channels,
            bit_depth=bit_depth
        )

        self.executor.execute(command, path)

        # Add segment paths to segments dict
        for ch in range(1, self.channels + 1):
            segment_path = self.temp_dir / f"ch{ch:02d}_{index:04d}.wav"
            segments[ch].append(segment_path)

    def _resolve_bit_depth(self, requested: BitDepth, source: BitDepth) -> BitDepth:
        """Resolve the effective bit depth to use.

        Args:
            requested: Requested bit depth
            source: Source bit depth

        Returns:
            Effective bit depth to use
        """
        if requested == BitDepth.SOURCE:
            return source
        return requested

    def cleanup(self) -> None:
        """Delete temporary files unless keep_temp was requested."""
        if self.keep_temp:
            self._output_handler.info("Skipping temp cleanup (keep-temp enabled).")
            return
        if self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
            self._output_handler.info(f"Removed temporary directory {self.temp_dir}.")