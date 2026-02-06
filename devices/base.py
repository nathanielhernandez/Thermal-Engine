"""
BaseDevice - Abstract base class for all LCD device drivers.
"""

from abc import ABC, abstractmethod
from enum import Enum
import time


class FrameFormat(Enum):
    """Supported frame encoding formats."""
    JPEG = "jpeg"
    RGB565 = "rgb565"


class BaseDevice(ABC):
    """Abstract base class for HID LCD device drivers.

    Each device driver handles its own encoding and protocol.
    The caller provides a PIL Image; the driver converts and sends it.
    """

    @property
    @abstractmethod
    def device_name(self) -> str:
        """Human-readable device name (e.g. 'Trofeo Vision')."""

    @property
    @abstractmethod
    def vendor_id(self) -> int:
        """USB Vendor ID."""

    @property
    @abstractmethod
    def product_id(self) -> int:
        """USB Product ID."""

    @property
    @abstractmethod
    def display_width(self) -> int:
        """Native display width in pixels."""

    @property
    @abstractmethod
    def display_height(self) -> int:
        """Native display height in pixels."""

    @property
    @abstractmethod
    def frame_format(self) -> FrameFormat:
        """Frame encoding format used by this device."""

    @abstractmethod
    def open(self):
        """Open the HID device connection."""

    @abstractmethod
    def close(self):
        """Close the HID device connection."""

    @abstractmethod
    def send_init(self):
        """Send the initialization packet after opening."""

    @abstractmethod
    def send_frame(self, image):
        """Encode and send a frame to the device.

        Args:
            image: PIL.Image in RGB mode, sized to display_width x display_height.
        """

    def diagnose(self):
        """Run diagnostic probe and print results to console.
        Override in stub drivers to add device-specific init probes.
        """
        self._print_hid_info()

    def _print_hid_info(self):
        """Print all HID enumeration info for this device's VID:PID."""
        try:
            import hid
        except ImportError:
            print("  [!] hidapi not available — cannot enumerate HID devices")
            return

        print("--- HID Device Info ---")
        devices = hid.enumerate(self.vendor_id, self.product_id)
        if not devices:
            print("  No HID interfaces found for "
                  f"{self.vendor_id:#06x}:{self.product_id:#06x}")
            return

        for i, dev in enumerate(devices):
            if len(devices) > 1:
                print(f"  Interface #{i}:")
            prefix = "    " if len(devices) > 1 else "  "
            print(f"{prefix}Manufacturer: {dev.get('manufacturer_string', 'N/A')}")
            print(f"{prefix}Product:      {dev.get('product_string', 'N/A')}")
            print(f"{prefix}Serial:       {dev.get('serial_number', 'N/A')}")
            print(f"{prefix}Release:      {dev.get('release_number', 'N/A')}")
            print(f"{prefix}Interface:    {dev.get('interface_number', 'N/A')}")
            usage_page = dev.get('usage_page', 0)
            usage = dev.get('usage', 0)
            print(f"{prefix}Usage:        page={usage_page:#06x} usage={usage:#06x}")
            path = dev.get('path', b'')
            if isinstance(path, bytes):
                path = path.decode('utf-8', errors='replace')
            print(f"{prefix}Path:         {path}")

    def _open_hid_device(self):
        """Open the first HID interface for this VID:PID. Returns (hid.device, path) or (None, None)."""
        try:
            import hid
        except ImportError:
            print("  [!] hidapi not available")
            return None, None

        devices = hid.enumerate(self.vendor_id, self.product_id)
        if not devices:
            print("  [!] No HID interfaces found — cannot probe")
            return None, None

        path = devices[0].get('path', b'')
        try:
            h = hid.device()
            h.open_path(path)
            h.set_nonblocking(1)
            return h, path
        except Exception as e:
            print(f"  [!] Failed to open HID device: {e}")
            return None, None

    @staticmethod
    def _hex_dump(data, max_bytes=32):
        """Return a hex string of data, truncated to max_bytes."""
        shown = data[:max_bytes]
        hex_str = ' '.join(f'{b:02X}' for b in shown)
        if len(data) > max_bytes:
            hex_str += f' ... ({len(data)} bytes total)'
        return hex_str

    @staticmethod
    def _read_with_timeout(h, size, timeout_sec=2.0):
        """Non-blocking read loop with timeout. Returns bytes or None."""
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            data = h.read(size)
            if data:
                return bytes(data)
            time.sleep(0.05)
        return None

    def on_sleep(self):
        """Called when the system is going to sleep. Override if needed."""
        pass

    def on_wake(self):
        """Called when the system wakes from sleep. Override if needed."""
        pass

    def __repr__(self):
        return f"{self.device_name} ({self.display_width}x{self.display_height})"
