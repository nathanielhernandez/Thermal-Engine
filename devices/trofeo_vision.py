"""
TrofeoVisionDevice - Driver for the Thermalright Trofeo Vision (1280x480 JPEG over HID).

VID: 0x0416  PID: 0x5302
Protocol: JPEG frames over 512-byte HID packets.
"""

import io

try:
    import hid
    HAS_HID = True
except ImportError:
    HAS_HID = False

from devices.base import BaseDevice, FrameFormat


class TrofeoVisionDevice(BaseDevice):
    """Driver for Thermalright Trofeo Vision 1280x480 LCD."""

    MAGIC = bytes([0xDA, 0xDB, 0xDC, 0xDD])
    PACKET_SIZE = 512

    def __init__(self):
        self._device = None

    # -- Abstract property implementations --

    @property
    def device_name(self) -> str:
        return "Trofeo Vision"

    @property
    def vendor_id(self) -> int:
        return 0x0416

    @property
    def product_id(self) -> int:
        return 0x5302

    @property
    def display_width(self) -> int:
        return 1280

    @property
    def display_height(self) -> int:
        return 480

    @property
    def frame_format(self) -> FrameFormat:
        return FrameFormat.JPEG

    # -- Connection lifecycle --

    def open(self):
        if not HAS_HID:
            raise RuntimeError("hidapi library not installed (pip install hidapi)")
        self._device = hid.device()
        self._device.open(self.vendor_id, self.product_id)

    def close(self):
        if self._device:
            try:
                self._device.close()
            except Exception as e:
                print(f"[{self.device_name}] Error closing device: {e}")
            finally:
                self._device = None

    def send_init(self):
        """Send the Trofeo Vision initialization packet and read device info."""
        if not self._device:
            raise IOError("Device not open")
        init = bytearray(self.PACKET_SIZE)
        init[0:4] = self.MAGIC
        init[4] = 0x00
        init[12] = 0x01
        self._device.write(bytes([0x00]) + bytes(init))

        # Read init response (non-blocking, up to 2s)
        import time
        self._device.set_nonblocking(1)
        deadline = time.monotonic() + 2.0
        response = None
        while time.monotonic() < deadline:
            data = self._device.read(self.PACKET_SIZE)
            if data:
                response = bytes(data)
                break
            time.sleep(0.05)
        self._device.set_nonblocking(0)

        if response:
            self._print_init_response(response)
        else:
            print(f"[{self.device_name}] No init response received")

    @staticmethod
    def _decode_init_response(response):
        """Decode fields from the H-protocol init response."""
        info = {}
        info['magic_ok'] = response[0:4] == bytes([0xDA, 0xDB, 0xDC, 0xDD])
        info['type_bytes'] = (response[4], response[5]) if len(response) > 5 else None
        info['byte_12'] = response[12] if len(response) > 12 else None
        info['byte_16'] = response[16] if len(response) > 16 else None
        if len(response) >= 36:
            info['board_id_hex'] = ''.join(f'{b:02X}' for b in response[20:36])
            info['board_id_ascii'] = bytes(response[20:36]).decode('ascii', errors='replace').rstrip('\x00')
        return info

    def _print_init_response(self, response):
        """Print decoded init response to console."""
        hex_str = ' '.join(f'{b:02X}' for b in response[:36])
        print(f"[{self.device_name}] Init response ({len(response)} bytes): {hex_str}")
        info = self._decode_init_response(response)
        print(f"[{self.device_name}]   Magic valid: {info['magic_ok']}")
        if info['type_bytes']:
            print(f"[{self.device_name}]   Device type bytes [4:6]: "
                  f"{info['type_bytes'][0]:#04x} {info['type_bytes'][1]:#04x}")
        if info['byte_12'] is not None:
            print(f"[{self.device_name}]   Byte [12]: {info['byte_12']:#04x}  "
                  f"Byte [16]: {info['byte_16']:#04x}")
        if info.get('board_id_hex'):
            print(f"[{self.device_name}]   Board ID [20:36]: {info['board_id_hex']}")
            print(f"[{self.device_name}]   Board ID (ASCII): {info['board_id_ascii']}")

    def diagnose(self):
        """Probe H-protocol device: send 512-byte init, decode response."""
        self._print_hid_info()

        print("\n--- Init Probe (H-protocol) ---")
        h, path = self._open_hid_device()
        if not h:
            return

        try:
            init = bytearray(self.PACKET_SIZE)
            init[0:4] = self.MAGIC
            init[12] = 0x01

            print(f"  Sending {self.PACKET_SIZE}-byte init packet...")
            print(f"  TX (first 32 bytes): {self._hex_dump(init, 32)}")

            h.write(bytes([0x00]) + bytes(init))

            rx = self._read_with_timeout(h, self.PACKET_SIZE)
            if rx:
                print(f"  RX ({len(rx)} bytes):       {self._hex_dump(rx, 36)}")
                info = self._decode_init_response(rx)
                print(f"  Magic valid:    {info['magic_ok']}")
                if info['type_bytes']:
                    print(f"  Type [4:6]:     {info['type_bytes'][0]:#04x} {info['type_bytes'][1]:#04x}")
                if info['byte_12'] is not None:
                    print(f"  Byte [12]:      {info['byte_12']:#04x}")
                    print(f"  Byte [16]:      {info['byte_16']:#04x}")
                if info.get('board_id_hex'):
                    print(f"  Board ID (hex): {info['board_id_hex']}")
                    print(f"  Board ID (ASCII): {info['board_id_ascii']}")
            else:
                print("  RX: no response within 2s timeout")
        except Exception as e:
            print(f"  [!] Probe error: {e}")
        finally:
            try:
                h.close()
            except Exception:
                pass

    def send_frame(self, image):
        """Encode image as JPEG and send to device.

        Args:
            image: PIL.Image in RGB mode, 1280x480.
        """
        jpeg_data = self._image_to_jpeg(image)
        self._send_jpeg_frame(jpeg_data)

    # -- Internal helpers --

    def _image_to_jpeg(self, img, quality=80):
        """Convert PIL Image to JPEG bytes."""
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=False, subsampling=2)
        return buffer.getvalue()

    def _send_jpeg_frame(self, jpeg_data):
        """Send JPEG data using the Trofeo Vision HID protocol."""
        if not self._device:
            raise IOError("Device not connected")

        header = bytearray(self.PACKET_SIZE)
        header[0:4] = self.MAGIC
        header[4] = 0x02
        header[8:12] = bytes([0x00, 0x05, 0xE0, 0x01])
        header[12] = 0x02

        jpeg_len = len(jpeg_data)
        header[16] = jpeg_len & 0xFF
        header[17] = (jpeg_len >> 8) & 0xFF
        header[18] = (jpeg_len >> 16) & 0xFF
        header[19] = (jpeg_len >> 24) & 0xFF

        first_chunk = min(len(jpeg_data), 492)
        header[20:20 + first_chunk] = jpeg_data[:first_chunk]

        try:
            self._device.write(bytes([0x00]) + bytes(header))

            offset = first_chunk
            while offset < len(jpeg_data):
                chunk = jpeg_data[offset:offset + self.PACKET_SIZE]
                if len(chunk) < self.PACKET_SIZE:
                    chunk = chunk + bytes(self.PACKET_SIZE - len(chunk))
                self._device.write(bytes([0x00]) + chunk)
                offset += self.PACKET_SIZE
        except Exception as e:
            raise IOError(f"HID write failed: {e}")

    def image_to_jpeg(self, img, quality=80):
        """Public access to JPEG encoding (used by overdrive mode)."""
        return self._image_to_jpeg(img, quality)

    def send_jpeg_data(self, jpeg_data):
        """Public access to send pre-encoded JPEG data (used by overdrive mode)."""
        self._send_jpeg_frame(jpeg_data)
