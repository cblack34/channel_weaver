"""Basic integration tests for the audio processing pipeline."""

from __future__ import annotations

from pathlib import Path

import soundfile as sf

from src.audio.extractor import AudioExtractor
from src.config.loader import ConfigLoader
from src.processing.builder import TrackBuilder


class TestBasicPipeline:
    """Basic integration tests for the complete pipeline."""

    def test_multichannel_extraction(
        self,
        multichannel_wav_file: Path,
        temp_processing_dir: Path,
    ) -> None:
        """Test extraction from a multichannel WAV file."""
        input_dir = multichannel_wav_file.parent

        # Extract and validate
        extractor = AudioExtractor(
            input_dir=input_dir,
            temp_dir=temp_processing_dir,
            keep_temp=True,
            console=None,
        )

        extractor.discover_and_validate()

        # Verify detection
        assert extractor.channels == 8
        assert extractor.sample_rate == 44100
        assert extractor.bit_depth is not None
        # Note: bit depth may be SOURCE or FLOAT32 depending on how soundfile detects it
        assert extractor.bit_depth.name in ["FLOAT32", "SOURCE"]

        # Extract segments
        segments = extractor.extract_segments(target_bit_depth=None)

        # Verify segments
        assert len(segments) == 8
        for ch_num, segment_list in segments.items():
            assert len(segment_list) == 1  # One file
            assert segment_list[0].exists()
            assert segment_list[0].stat().st_size > 0

    def test_full_pipeline_with_config(
        self,
        multichannel_wav_file: Path,
        config_file: Path,
        output_dir: Path,
        temp_processing_dir: Path,
    ) -> None:
        """Test complete pipeline from extraction to output."""
        input_dir = multichannel_wav_file.parent

        # Step 1: Extract audio
        extractor = AudioExtractor(
            input_dir=input_dir,
            temp_dir=temp_processing_dir,
            keep_temp=True,
            console=None,
        )

        extractor.discover_and_validate()
        segments = extractor.extract_segments(target_bit_depth=None)

        # Step 2: Load configuration
        import sys
        sys.path.insert(0, str(config_file.parent))

        try:
            config_module = __import__(config_file.stem)
            raw_channels, raw_buses = config_module.CHANNELS, config_module.BUSES
        finally:
            sys.path.remove(str(config_file.parent))

        config_loader = ConfigLoader(
            raw_channels,
            raw_buses,
            detected_channel_count=extractor.channels
        )
        channels, buses, section_splitting = config_loader.load()

        # Step 3: Build tracks
        builder = TrackBuilder(
            sample_rate=extractor.sample_rate,  # type: ignore[arg-type]
            bit_depth=extractor.bit_depth,  # type: ignore[arg-type]
            source_bit_depth=extractor.bit_depth,
            temp_dir=temp_processing_dir,
            output_dir=output_dir,
            keep_temp=True,
            console=None,
        )

        builder.build_tracks(channels, buses, segments)

        # Step 4: Verify output
        output_files = list(output_dir.glob("*.wav"))
        assert len(output_files) > 0

        # Verify each output file
        for output_file in output_files:
            assert output_file.stat().st_size > 0
            info = sf.info(str(output_file))
            assert info.samplerate == 44100
            # Subtype can vary based on bit depth conversion
            assert info.subtype in ["FLOAT", "PCM_32", "PCM_24", "PCM_16"]
