import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

# The OS-provided libcamera pybind11 module only exists on the Raspi image
sys.modules.setdefault('libcamera', MagicMock())

# tests/base.py (imported by most other test modules) replaces
# seedsigner.hardware.camera_stream in sys.modules with a MagicMock for the
# app-level tests. Load the real module directly from its file -- under a
# private name, so the mock is left undisturbed -- to test its pure-python
# helpers regardless of pytest collection order.
spec = importlib.util.spec_from_file_location(
    "camera_stream_under_test",
    Path(__file__).resolve().parent.parent / "src" / "seedsigner" / "hardware" / "camera_stream.py",
)
camera_stream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera_stream)

strip_stride = camera_stream.strip_stride
rgba_buffer_to_image = camera_stream.rgba_buffer_to_image



class TestStripStride:
    def test_passthrough_when_no_padding(self):
        """When stride == width the input bytes must be returned unchanged (no copy)."""
        data = bytes(range(8)) * 4  # 8-wide, 4 rows
        assert strip_stride(data, stride=8, width_bytes=8, height=4) is data


    def test_strips_row_padding(self):
        """
        The RPi ISP pads YUV420 rows out to an aligned stride (e.g. 480px wide
        reports a 512-byte stride); the padding must be removed.
        """
        width, height, stride = 8, 4, 12
        rows = [bytes([row_num] * width) + b"\xff" * (stride - width) for row_num in range(height)]
        result = strip_stride(b"".join(rows), stride=stride, width_bytes=width, height=height)

        assert len(result) == width * height
        assert result == b"".join(bytes([row_num] * width) for row_num in range(height))


class TestRgbaBufferToImage:
    def test_converts_xbgr8888_frame(self):
        """XBGR8888 memory order (R,G,B,X) must map straight onto PIL RGBA pixels."""
        width, height = 2, 2
        pixels = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (9, 8, 7, 255)]
        data = b"".join(bytes(p) for p in pixels)

        img = rgba_buffer_to_image(data, stride=width * 4, width=width, height=height)

        assert img.mode == "RGBA"
        assert img.size == (width, height)
        assert list(img.getdata()) == pixels


    def test_handles_padded_stride(self):
        """Rows longer than width*4 (alignment padding) must not shear the image."""
        width, height, stride = 2, 2, 12  # 4 padding bytes per row
        pixel = (1, 2, 3, 255)
        row = bytes(pixel) * width + b"\x00" * (stride - width * 4)

        img = rgba_buffer_to_image(row * height, stride=stride, width=width, height=height)

        assert img.size == (width, height)
        assert list(img.getdata()) == [pixel] * (width * height)
