"""Metadata writing for audio files using mutagen for ID3 tags."""

from pathlib import Path
import logging

from mutagen import File
from mutagen.id3 import TBPM

logger = logging.getLogger(__name__)


class MutagenMetadataWriter:
    """Write metadata to audio files using mutagen's ID3 tag support."""

    def write_bpm(self, file_path: Path, bpm: int | None) -> bool:
        """Embed BPM metadata into an audio file using ID3 TBPM tag.

        Args:
            file_path: Path to the audio file to modify
            bpm: BPM value to embed, or None to remove BPM metadata

        Returns:
            True if metadata was successfully written, False otherwise
        """
        try:
            # Load the file with mutagen
            audio = File(str(file_path), easy=False)

            if audio is None:
                logger.warning(f"Could not load audio file: {file_path}")
                return False

            # Ensure we have ID3 tags
            if not hasattr(audio, 'tags') or audio.tags is None:
                audio.add_tags()

            if bpm is not None:
                # Set the TBPM (BPM) frame
                audio.tags.add(TBPM(encoding=3, text=str(bpm)))
                logger.debug(f"Successfully wrote BPM={bpm} to {file_path}")
            else:
                # Remove BPM tag if it exists
                if 'TBPM' in audio.tags:
                    del audio.tags['TBPM']
                logger.debug(f"Removed BPM metadata from {file_path}")

            # Save the changes
            audio.save()
            return True

        except Exception as e:
            logger.warning(f"Failed to write BPM metadata to {file_path}: {e}")
            return False

    def read_bpm(self, file_path: Path) -> int | None:
        """Read BPM metadata from an audio file's ID3 TBPM tag.

        Args:
            file_path: Path to the audio file to read

        Returns:
            BPM value if found, None if not present or unreadable
        """
        try:
            audio = File(str(file_path), easy=False)

            if audio is None or not hasattr(audio, 'tags') or audio.tags is None:
                return None

            # Look for TBPM frame
            if 'TBPM' in audio.tags:
                tbpm_frame = audio.tags['TBPM']
                if tbpm_frame.text:
                    bpm_str = str(tbpm_frame.text[0]).strip()
                    try:
                        return int(bpm_str)
                    except ValueError:
                        logger.warning(f"Invalid BPM value in {file_path}: {bpm_str}")
                        return None

            return None

        except Exception as e:
            logger.warning(f"Failed to read BPM metadata from {file_path}: {e}")
            return None


# Alternative implementation using ffmpeg as fallback (if needed)
class FfmpegMetadataWriter:
    """Alternative metadata writer using ffmpeg as fallback."""

    def write_bpm(self, file_path: Path, bpm: int | None) -> bool:
        """Embed BPM metadata using ffmpeg.

        This is a fallback implementation that could be used if soundfile
        metadata writing proves insufficient for some use cases.
        """
        # Implementation would use subprocess to call ffmpeg
        # For now, just log that it's not implemented
        logger.warning("FfmpegMetadataWriter not implemented - use SoundfileMetadataWriter")
        return False

    def read_bpm(self, file_path: Path) -> int | None:
        """Read BPM metadata using ffmpeg."""
        logger.warning("FfmpegMetadataWriter not implemented - use SoundfileMetadataWriter")
        return None