"""32-bit float converter for Channel Weaver."""

import numpy as np


class Float32Converter:
    """Converter for 32-bit float output."""

    @property
    def soundfile_subtype(self) -> str:
        return "FLOAT"

    @property
    def numpy_dtype(self) -> np.dtype:
        return np.float32

    def convert(self, data: np.ndarray) -> np.ndarray:
        """Convert to 32-bit float (no-op for already normalized float data)."""
        return data.astype(np.float32, copy=False)