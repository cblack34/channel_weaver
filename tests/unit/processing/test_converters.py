"""Unit tests for bit depth converter factory and converters."""

from __future__ import annotations

import numpy as np
import pytest

from src.config.enums import BitDepth
from src.processing.converters.factory import get_converter, resolve_bit_depth
from src.processing.converters.float32 import Float32Converter
from src.processing.converters.int16 import Int16Converter
from src.processing.converters.int24 import Int24Converter
from src.processing.converters.source import SourceConverter


class TestConverterFactory:
    """Tests for converter factory functions."""

    @pytest.mark.parametrize("bit_depth,expected_converter_class", [
        (BitDepth.FLOAT32, Float32Converter),
        (BitDepth.INT24, Int24Converter),
        (BitDepth.INT16, Int16Converter),
        (BitDepth.SOURCE, SourceConverter),
    ])
    def test_get_converter_returns_correct_type(
        self,
        bit_depth: BitDepth,
        expected_converter_class: type,
    ) -> None:
        """Test that get_converter returns the correct converter type."""
        converter = get_converter(bit_depth)
        assert isinstance(converter, expected_converter_class)

    def test_resolve_bit_depth_passthrough(self) -> None:
        """Test resolve_bit_depth returns requested bit depth when not SOURCE."""
        assert resolve_bit_depth(BitDepth.INT16, BitDepth.INT24) == BitDepth.INT16
        assert resolve_bit_depth(BitDepth.FLOAT32, None) == BitDepth.FLOAT32

    def test_resolve_bit_depth_source_with_valid_source(self) -> None:
        """Test resolve_bit_depth resolves SOURCE to source bit depth."""
        assert resolve_bit_depth(BitDepth.SOURCE, BitDepth.INT24) == BitDepth.INT24
        assert resolve_bit_depth(BitDepth.SOURCE, BitDepth.FLOAT32) == BitDepth.FLOAT32

    def test_resolve_bit_depth_source_without_source_raises_error(self) -> None:
        """Test resolve_bit_depth raises ValueError when SOURCE requested but source is None."""
        with pytest.raises(ValueError, match="Cannot resolve source bit depth"):
            resolve_bit_depth(BitDepth.SOURCE, None)


class TestFloat32Converter:
    """Tests for Float32Converter."""

    @pytest.fixture
    def converter(self) -> Float32Converter:
        """Create Float32Converter instance."""
        return Float32Converter()

    def test_soundfile_subtype(self, converter: Float32Converter) -> None:
        """Test soundfile subtype property."""
        assert converter.soundfile_subtype == "FLOAT"

    def test_numpy_dtype(self, converter: Float32Converter) -> None:
        """Test numpy dtype property."""
        assert converter.numpy_dtype == np.dtype('float32')

    def test_convert_passthrough(self, converter: Float32Converter) -> None:
        """Test convert method passes through float32 data unchanged."""
        data = np.array([[0.5, -0.3], [0.8, -0.1]], dtype=np.float32)
        result = converter.convert(data)
        np.testing.assert_array_equal(result, data)
        assert result.dtype == np.float32

    def test_convert_from_other_dtype(self, converter: Float32Converter) -> None:
        """Test convert method handles different input dtypes."""
        data = np.array([[0.5, -0.3]], dtype=np.float64)
        result = converter.convert(data)
        assert result.dtype == np.float32
        np.testing.assert_array_almost_equal(result, data.astype(np.float32))


class TestInt16Converter:
    """Tests for Int16Converter."""

    @pytest.fixture
    def converter(self) -> Int16Converter:
        """Create Int16Converter instance."""
        return Int16Converter()

    def test_soundfile_subtype(self, converter: Int16Converter) -> None:
        """Test soundfile subtype property."""
        assert converter.soundfile_subtype == "PCM_16"

    def test_numpy_dtype(self, converter: Int16Converter) -> None:
        """Test numpy dtype property."""
        assert converter.numpy_dtype == np.dtype('int16')

    def test_convert_clips_and_converts(self, converter: Int16Converter) -> None:
        """Test convert method clips and converts to int16."""
        # Test normal range
        data = np.array([[0.5, -0.3], [-0.8, 0.1]], dtype=np.float32)
        result = converter.convert(data)

        assert result.dtype == np.int16
        # Values should be scaled and converted
        expected = np.array([[16384, -9830], [-26214, 3277]], dtype=np.int16)
        np.testing.assert_array_equal(result, expected)

    def test_convert_clips_out_of_range(self, converter: Int16Converter) -> None:
        """Test convert method clips values outside [-1, 1] range."""
        data = np.array([[2.0, -1.5]], dtype=np.float32)  # Outside [-1, 1]
        result = converter.convert(data)

        assert result.dtype == np.int16
        # Should be clipped to int16 range
        expected = np.array([[32767, -32768]], dtype=np.int16)
        np.testing.assert_array_equal(result, expected)


class TestInt24Converter:
    """Tests for Int24Converter."""

    @pytest.fixture
    def converter(self) -> Int24Converter:
        """Create Int24Converter instance."""
        return Int24Converter()

    def test_soundfile_subtype(self, converter: Int24Converter) -> None:
        """Test soundfile subtype property."""
        assert converter.soundfile_subtype == "PCM_24"

    def test_numpy_dtype(self, converter: Int24Converter) -> None:
        """Test numpy dtype property."""
        assert converter.numpy_dtype == np.dtype('int32')  # SoundFile uses int32 for 24-bit

    def test_convert_clips_and_converts(self, converter: Int24Converter) -> None:
        """Test convert method clips and converts to int32 (24-bit)."""
        data = np.array([[0.5, -0.3]], dtype=np.float32)
        result = converter.convert(data)

        assert result.dtype == np.int32
        # Values should be scaled to 24-bit range
        expected = np.array([[4194304, -2516582]], dtype=np.int32)
        np.testing.assert_array_equal(result, expected)

    def test_convert_clips_out_of_range(self, converter: Int24Converter) -> None:
        """Test convert method clips values outside [-1, 1] range."""
        data = np.array([[1.5, -2.0]], dtype=np.float32)
        result = converter.convert(data)

        assert result.dtype == np.int32
        # Should be clipped to 24-bit range
        expected = np.array([[8388607, -8388608]], dtype=np.int32)
        np.testing.assert_array_equal(result, expected)


class TestSourceConverter:
    """Tests for SourceConverter."""

    @pytest.fixture
    def converter(self) -> SourceConverter:
        """Create SourceConverter instance."""
        return SourceConverter()

    def test_soundfile_subtype(self, converter: SourceConverter) -> None:
        """Test soundfile subtype property."""
        assert converter.soundfile_subtype == "PCM_32"

    def test_numpy_dtype(self, converter: SourceConverter) -> None:
        """Test numpy dtype property."""
        assert converter.numpy_dtype == np.dtype('int32')

    def test_convert_converts_to_int32(self, converter: SourceConverter) -> None:
        """Test convert method converts to int32."""
        data = np.array([[0.5, -0.3]], dtype=np.float32)
        result = converter.convert(data)

        assert result.dtype == np.int32
        # Values should be scaled to 32-bit range
        expected = np.array([[1073741824, -644245120]], dtype=np.int32)
        np.testing.assert_array_equal(result, expected)

    def test_convert_clips_out_of_range(self, converter: SourceConverter) -> None:
        """Test convert method clips values outside [-1, 1] range."""
        data = np.array([[1.5, -2.0]], dtype=np.float32)
        result = converter.convert(data)

        assert result.dtype == np.int32
        # Should be clipped to 32-bit range
        expected = np.array([[2147483647, -2147483648]], dtype=np.int32)
        np.testing.assert_array_equal(result, expected)