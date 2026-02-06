"""
DummyDevice - Virtual device for testing the full pipeline without USB hardware.

VID: 0xFFFF  PID: 0x0001 (fake — never matches real hardware)

Accepts frames and optionally saves the last one to disk for visual verification.
Tracks frame count and timing for performance testing.
"""

import io
import time
from pathlib import Path

from devices.base import BaseDevice, FrameFormat


class DummyDevice(BaseDevice):
    """Virtual device that accepts frames without USB hardware.

    Useful for testing the full render pipeline: manager -> driver -> frame output.
    Saves the last received frame to `output_dir/last_frame.jpg` if output_dir is set.
    """

    def __init__(self, width=480, height=480, output_dir=None):
        self._width = width
        self._height = height
        self._output_dir = Path(output_dir) if output_dir else None
        self._open = False
        self._frame_count = 0
        self._last_frame_time = None
        self._fps_window = []  # timestamps for rolling FPS

    @property
    def device_name(self) -> str:
        return "Dummy (Test)"

    @property
    def vendor_id(self) -> int:
        return 0xFFFF

    @property
    def product_id(self) -> int:
        return 0x0001

    @property
    def display_width(self) -> int:
        return self._width

    @property
    def display_height(self) -> int:
        return self._height

    @property
    def frame_format(self) -> FrameFormat:
        return FrameFormat.JPEG

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def fps(self) -> float:
        """Rolling FPS over the last 60 frames."""
        if len(self._fps_window) < 2:
            return 0.0
        elapsed = self._fps_window[-1] - self._fps_window[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._fps_window) - 1) / elapsed

    def open(self):
        self._open = True
        self._frame_count = 0
        self._fps_window.clear()
        print(f"[DummyDevice] Opened ({self._width}x{self._height})")

    def close(self):
        if self._open:
            print(f"[DummyDevice] Closed after {self._frame_count} frames")
        self._open = False

    def send_init(self):
        if not self._open:
            raise IOError("Device not open")
        print("[DummyDevice] Init OK")

    def send_frame(self, image):
        if not self._open:
            raise IOError("Device not open")

        now = time.perf_counter()
        self._frame_count += 1
        self._fps_window.append(now)
        # Keep rolling window to 60 samples
        if len(self._fps_window) > 60:
            self._fps_window.pop(0)
        self._last_frame_time = now

        # Save last frame to disk if output_dir is set
        if self._output_dir:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            out_path = self._output_dir / "last_frame.jpg"
            image.save(out_path, format="JPEG", quality=85)

        pass
