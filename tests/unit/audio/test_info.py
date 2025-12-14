"""Unit tests for audio information retrieval."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.audio.info import AudioInfo, AudioInfoRetriever
from src.exceptions import AudioProcessingError


class TestAudioInfoRetriever:
    """Tests for AudioInfoRetriever class."""

    @pytest.fixture
    def retriever(self) -> AudioInfoRetriever:
        """Create AudioInfoRetriever instance."""
        return AudioInfoRetriever()

    def test_get_info_soundfile_success(
        self,
        retriever: AudioInfoRetriever,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test successful audio info retrieval using soundfile."""
        file_path = tmp_path / "test.wav"
        file_path.write_bytes(b"\x00" * 100)

        # Mock soundfile.info to return info object
        mock_sf_info = mocker.MagicMock()
        mock_sf_info.samplerate = 44100
        mock_sf_info.channels = 2
        mock_sf_info.subtype = "PCM_16"
        mock_sf = mocker.patch("src.audio.info.sf.info", return_value=mock_sf_info)

        result = retriever.get_info(file_path)

        assert result == AudioInfo(samplerate=44100, channels=2, subtype="PCM_16")
        # Verify soundfile was called, not ffmpeg
        mock_sf.assert_called_once_with(file_path)

    def test_get_info_soundfile_fails_ffmpeg_success(
        self,
        retriever: AudioInfoRetriever,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test fallback to ffmpeg when soundfile fails."""
        file_path = tmp_path / "test.wav"
        file_path.write_bytes(b"\x00" * 100)

        # Mock soundfile to raise exception
        mocker.patch("src.audio.info.sf.info", side_effect=Exception("Soundfile failed"))

        # Mock subprocess.run for ffmpeg
        mock_process = mocker.MagicMock()
        mock_process.stdout = '''{
            "streams": [{
                "sample_rate": "48000",
                "channels": 8,
                "codec_name": "pcm_s24le"
            }]
        }'''
        mocker.patch("src.audio.info.subprocess.run", return_value=mock_process)

        # Mock json.loads
        mock_json_data = {
            "streams": [{
                "sample_rate": "48000",
                "channels": 8,
                "codec_name": "pcm_s24le"
            }]
        }
        mocker.patch("src.audio.info.json.loads", return_value=mock_json_data)

        result = retriever.get_info(file_path)

        assert result == AudioInfo(samplerate=48000, channels=8, subtype="PCM_24")

    def test_get_info_both_soundfile_and_ffmpeg_fail(
        self,
        retriever: AudioInfoRetriever,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test AudioProcessingError when both soundfile and ffmpeg fail."""
        file_path = tmp_path / "test.wav"
        file_path.write_bytes(b"\x00" * 100)

        # Mock soundfile to raise exception
        mocker.patch("src.audio.info.sf.info", side_effect=Exception("Soundfile error"))

        # Mock subprocess.run to raise exception
        mocker.patch("src.audio.info.subprocess.run", side_effect=Exception("FFmpeg error"))

        with pytest.raises(AudioProcessingError) as exc_info:
            retriever.get_info(file_path)

        assert "Failed to read audio file" in str(exc_info.value)
        assert "Soundfile error" in str(exc_info.value)
        assert "FFmpeg error" in str(exc_info.value)

    @pytest.mark.parametrize("codec_name,expected_subtype", [
        ("pcm_s16le", "PCM_16"),
        ("pcm_s24le", "PCM_24"),
        ("pcm_s32le", "PCM_32"),
        ("flac", "PCM_32"),  # default case
        ("aac", "PCM_32"),   # default case
    ])
    def test_get_info_ffmpeg_codec_mapping(
        self,
        retriever: AudioInfoRetriever,
        mocker: MockerFixture,
        tmp_path: Path,
        codec_name: str,
        expected_subtype: str,
    ) -> None:
        """Test ffmpeg codec name to soundfile subtype mapping."""
        file_path = tmp_path / "test.wav"
        file_path.write_bytes(b"\x00" * 100)

        # Mock soundfile to fail
        mocker.patch("src.audio.info.sf.info", side_effect=Exception("Soundfile failed"))

        # Mock subprocess.run for ffmpeg
        mock_process = mocker.MagicMock()
        mock_process.stdout = f'''{{
            "streams": [{{
                "sample_rate": "44100",
                "channels": 2,
                "codec_name": "{codec_name}"
            }}]
        }}'''
        mocker.patch("src.audio.info.subprocess.run", return_value=mock_process)

        # Mock json.loads
        mock_json_data = {
            "streams": [{
                "sample_rate": "44100",
                "channels": 2,
                "codec_name": codec_name
            }]
        }
        mocker.patch("src.audio.info.json.loads", return_value=mock_json_data)

        result = retriever.get_info(file_path)

        assert result == AudioInfo(samplerate=44100, channels=2, subtype=expected_subtype)

    def test_get_info_ffmpeg_missing_fields(
        self,
        retriever: AudioInfoRetriever,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test ffmpeg fallback with missing codec_name field."""
        file_path = tmp_path / "test.wav"
        file_path.write_bytes(b"\x00" * 100)

        # Mock soundfile to fail
        mocker.patch("src.audio.info.sf.info", side_effect=Exception("Soundfile failed"))

        # Mock subprocess.run for ffmpeg
        mock_process = mocker.MagicMock()
        mock_process.stdout = '''{
            "streams": [{
                "sample_rate": "22050",
                "channels": 1
            }]
        }'''
        mocker.patch("src.audio.info.subprocess.run", return_value=mock_process)

        # Mock json.loads
        mock_json_data = {
            "streams": [{
                "sample_rate": "22050",
                "channels": 1
            }]
        }
        mocker.patch("src.audio.info.json.loads", return_value=mock_json_data)

        result = retriever.get_info(file_path)

        # Should default to PCM_32 when codec_name is missing
        assert result == AudioInfo(samplerate=22050, channels=1, subtype="PCM_32")

    def test_get_info_ffmpeg_subprocess_error(
        self,
        retriever: AudioInfoRetriever,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test ffmpeg subprocess failure."""
        file_path = tmp_path / "test.wav"
        file_path.write_bytes(b"\x00" * 100)

        # Mock soundfile to fail
        mocker.patch("src.audio.info.sf.info", side_effect=Exception("Soundfile error"))

        # Mock subprocess.run to raise CalledProcessError
        from subprocess import CalledProcessError
        mocker.patch("src.audio.info.subprocess.run", side_effect=CalledProcessError(1, 'ffprobe'))

        with pytest.raises(AudioProcessingError) as exc_info:
            retriever.get_info(file_path)

        assert "Failed to read audio file" in str(exc_info.value)
        assert "Soundfile error" in str(exc_info.value)
        assert "returned non-zero exit status 1" in str(exc_info.value)

    def test_get_info_ffmpeg_json_parse_error(
        self,
        retriever: AudioInfoRetriever,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test ffmpeg output JSON parsing failure."""
        file_path = tmp_path / "test.wav"
        file_path.write_bytes(b"\x00" * 100)

        # Mock soundfile to fail
        mocker.patch("src.audio.info.sf.info", side_effect=Exception("Soundfile error"))

        # Mock subprocess.run for ffmpeg
        mock_process = mocker.MagicMock()
        mock_process.stdout = "invalid json"
        mocker.patch("src.audio.info.subprocess.run", return_value=mock_process)

        # Mock json.loads to raise exception
        mocker.patch("src.audio.info.json.loads", side_effect=ValueError("Invalid JSON"))

        with pytest.raises(AudioProcessingError) as exc_info:
            retriever.get_info(file_path)

        assert "Failed to read audio file" in str(exc_info.value)
        assert "Soundfile error" in str(exc_info.value)
        assert "Invalid JSON" in str(exc_info.value)