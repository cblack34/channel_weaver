"""24-bit integer converter for Channel Weaver."""

import numpy as np


class Int24Converter:
    """Converter for 24-bit integer output."""

    @property
    def soundfile_subtype(self) -> str:
        return "PCM_24"

    @property
    def numpy_dtype(self) -> np.dtype:
        return np.int32

    def convert(self, data: np.ndarray) -> np.ndarray:
        """Convert to 24-bit integer range."""
        float_data = data.astype(np.float32, copy=False)
        # Scale to 24-bit signed integer range: [-2^23, 2^23-1] = [-8388608, 8388607]
        scaled = np.clip(np.rint(float_data * 8388608.0), -8388608, 8388607)
        return scaled.astype(np.int32)