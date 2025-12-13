"""Audio information retrieval for Channel Weaver."""

import json
import subprocess
from pathlib import Path
from typing import NamedTuple

import soundfile as sf


class AudioInfo(NamedTuple):
    """Audio file information."""
    samplerate: int
    channels: int
    subtype: str


class AudioInfoRetriever:
    """Retrieve audio file information using soundfile with ffmpeg fallback.

    Attempts to get audio information using the soundfile library first,
    falling back to ffmpeg/ffprobe if soundfile fails.
    """

    def get_info(self, path: Path) -> AudioInfo:
        """Get audio information for a file.

        Args:
            path: Path to the audio file

        Returns:
            AudioInfo containing sample rate, channel count, and subtype

        Raises:
            AudioProcessingError: If both soundfile and ffmpeg fail
        """
        try:
            info = sf.info(path)
            return AudioInfo(
                samplerate=info.samplerate,
                channels=info.channels,
                subtype=info.subtype
            )
        except Exception as e:
            # Try ffmpeg as fallback
            try:
                return self._get_info_ffmpeg(path)
            except Exception as ffmpeg_e:
                from src.exceptions import AudioProcessingError
                raise AudioProcessingError(
                    f"Failed to read audio file {path} with both soundfile and ffmpeg: "
                    f"soundfile: {e}, ffmpeg: {ffmpeg_e}"
                ) from e

    def _get_info_ffmpeg(self, path: Path) -> AudioInfo:
        """Get audio info using ffprobe when soundfile fails."""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        stream = data['streams'][0]

        # Map ffmpeg codec names to soundfile subtypes
        subtype = stream.get('codec_name', 'pcm_s32le')
        if subtype == 'pcm_s32le':
            subtype = 'PCM_32'
        elif subtype == 'pcm_s24le':
            subtype = 'PCM_24'
        elif subtype == 'pcm_s16le':
            subtype = 'PCM_16'
        else:
            subtype = 'PCM_32'  # default

        return AudioInfo(
            samplerate=int(stream['sample_rate']),
            channels=int(stream['channels']),
            subtype=subtype
        )