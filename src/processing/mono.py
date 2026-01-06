"""Mono track writing for Channel Weaver."""

from pathlib import Path

import soundfile as sf
from tqdm import tqdm

from src.config import ChannelConfig, ChannelAction
from src.constants import AUDIO_CHUNK_SIZE
from src.output.naming import build_output_path
from src.processing.converters.protocols import BitDepthConverter
from src.output.protocols import OutputHandler
from src.config import SegmentMap


class MonoTrackWriter:
    """Write individual mono tracks from channel segments."""

    def __init__(
        self,
        sample_rate: int,
        converter: BitDepthConverter,
        output_dir: Path,
        output_handler: OutputHandler,
    ) -> None:
        """Initialize the mono track writer.

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

    def write_tracks(self, channels: list[ChannelConfig], segments: SegmentMap) -> None:
        """Write individual mono tracks for channels with PROCESS action.

        Args:
            channels: List of channel configurations to process
            segments: Dictionary mapping channel numbers to segment file lists
        """
        process_channels = [c for c in channels if c.action == ChannelAction.PROCESS]
        
        for ch_config in tqdm(process_channels, desc="Building mono tracks", unit="track"):
            self._write_track(ch_config, segments)

    def _write_track(self, ch_config: ChannelConfig, segments: SegmentMap) -> None:
        """Write a single mono track.

        Args:
            ch_config: Channel configuration
            segments: Dictionary mapping channel numbers to segment file lists
        """
        ch = ch_config.ch
        output_ch = ch_config.output_ch
        ch_segments = segments.get(ch, [])

        if not ch_segments:
            self.output_handler.warning(f"No segments for channel {ch}")
            return

        output_path = build_output_path(self.output_dir, output_ch, ch_config.name)  # type: ignore[arg-type]

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sf.SoundFile(
            str(output_path), "w",
            samplerate=self.sample_rate,
            channels=1,
            subtype=self.converter.soundfile_subtype
        ) as dest:
            for seg_path in ch_segments:
                self._concatenate_segment(dest, seg_path)

    def _concatenate_segment(self, dest: sf.SoundFile, seg_path: Path) -> None:
        """Concatenate a single segment to the destination file.

        Args:
            dest: Destination SoundFile to write to
            seg_path: Path to the segment file to read
        """
        with sf.SoundFile(str(seg_path)) as src:
            while True:
                data = src.read(AUDIO_CHUNK_SIZE, dtype="float32", always_2d=True)
                if len(data) == 0:
                    break
                converted = self.converter.convert(data)
                dest.write(converted.astype(self.converter.numpy_dtype, copy=False))