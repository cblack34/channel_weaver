"""FFmpeg command builders for Channel Weaver."""

from pathlib import Path
from typing import List

from src.config import BitDepth


class FFmpegCommandBuilder:
    """Build FFmpeg commands for audio processing operations."""

    @staticmethod
    def build_channel_split_command(
        input_path: Path,
        output_dir: Path,
        file_index: int,
        channels: int,
        bit_depth: BitDepth
    ) -> List[str]:
        """Build FFmpeg command to split multichannel audio into mono files.

        Args:
            input_path: Input WAV file path
            output_dir: Directory for output mono files
            file_index: Sequential file index for naming
            channels: Number of channels in the input file
            bit_depth: Target bit depth for output files

        Returns:
            FFmpeg command as list of strings
        """
        codec = {
            BitDepth.INT16: 'pcm_s16le',
            BitDepth.INT24: 'pcm_s24le',
            BitDepth.FLOAT32: 'pcm_f32le',
            BitDepth.SOURCE: 'pcm_s32le',  # SOURCE should be resolved before calling this
        }.get(bit_depth, 'pcm_s32le')

        # Build filter_complex for multiple pan filters
        pan_filters = '; '.join(f'[0:a]pan=mono|c0=c{i}[c{i}]' for i in range(channels))
        af = pan_filters

        # Build the command with all maps
        cmd = ['ffmpeg', '-y', '-i', str(input_path), '-filter_complex', af]

        for ch in range(1, channels + 1):
            channel_index = ch - 1
            segment_path = output_dir / f"ch{ch:02d}_{file_index:04d}.wav"
            cmd.extend(['-map', f'[c{channel_index}]', '-c:a', codec, str(segment_path)])

        return cmd