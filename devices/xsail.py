"""
XsailDevice - Stub driver for older Xsail-based Thermalright LCD displays.

VID: 0x87AD  PID: 0x70DB
Protocol: JPEG frames over USB bulk transfers (LibUsbDotNet EP1 Read, EP1 Write).

Protocol details (from TRCC USBLCDNEW.dll decompilation):
  - Init packet: 64 bytes
    Header: {0x12, 0x34, 0x56, 0x78, ...}, byte[56] = 1
  - Init response: 1024 bytes
    Device info at bytes [20..40]
  - Frame data: JPEG size read from bytes [60-63] (big-endian shifted), 64-byte offset
  - Sends frame in single async transfer
  - If transfer size is a multiple of 512, sends a zero-length packet (ZLP)
  - Shared memory slot size: 691200 bytes
  - NOTE: Uses EP1 for both read AND write (not separate endpoints)

SSCRM command types (defined but appear unused/legacy):
  DEV_INFO=1, PICTURE=2, LOGO=3, OTA=4, UPG_STATE=5,
  ROTATE=6, SCR_SET=7, BKL_SET=8, LOGO_STATE=9

STATUS: STUB - Not yet implemented. Needs a physical device to test and verify.
OEM manufacturer: SOMORE TECH CO., LTD. (New Taipei City, Taiwan).
"""

from devices.base import BaseDevice, FrameFormat


class XsailDevice(BaseDevice):
    """Stub driver for older Xsail-based Thermalright LCD.

    This appears to be an older/legacy device using a Xsail SoC.
    """

    # Protocol constants from TRCC decompilation
    INIT_HEADER = bytes([0x12, 0x34, 0x56, 0x78])
    INIT_PACKET_SIZE = 64
    RESPONSE_SIZE = 1024
    FRAME_OFFSET = 64
    WRITE_ENDPOINT = 1  # EP1 for both read and write

    def __init__(self):
        self._device = None

    @property
    def device_name(self) -> str:
        return "Xsail LCD"

    @property
    def vendor_id(self) -> int:
        return 0x87AD

    @property
    def product_id(self) -> int:
        return 0x70DB

    @property
    def display_width(self) -> int:
        return 480  # placeholder — actual resolution unknown without device

    @property
    def display_height(self) -> int:
        return 480  # placeholder

    @property
    def frame_format(self) -> FrameFormat:
        return FrameFormat.JPEG

    def open(self):
        raise NotImplementedError(
            "Xsail LCD driver is a stub. A physical device (0x87AD:0x70DB) is needed to implement and test."
        )

    def close(self):
        pass

    def send_init(self):
        raise NotImplementedError("Xsail LCD driver is a stub.")

    def send_frame(self, image):
        raise NotImplementedError("Xsail LCD driver is a stub.")

    def diagnose(self):
        """Probe Xsail LCD: send 64-byte init, capture 1024-byte response."""
        self._print_hid_info()

        print("\n--- Init Probe ---")
        h, path = self._open_hid_device()
        if not h:
            return

        try:
            # Build 64-byte init packet: 4-byte header, byte[56] = 1, rest zeros
            init_packet = bytearray(self.INIT_PACKET_SIZE)
            init_packet[:len(self.INIT_HEADER)] = self.INIT_HEADER
            init_packet[56] = 1

            print(f"  Sending {self.INIT_PACKET_SIZE}-byte init packet...")
            print(f"  TX (first 32 bytes): {self._hex_dump(init_packet, 32)}")

            h.write(bytes(init_packet))

            rx = self._read_with_timeout(h, self.RESPONSE_SIZE)
            if rx:
                print(f"  RX ({len(rx)} bytes):       {self._hex_dump(rx, 32)}")
                # Device info expected at bytes [20..40]
                if len(rx) > 40:
                    info_slice = rx[20:41]
                    print(f"  Device info [20:40]: {self._hex_dump(info_slice, 21)}")
                    # Try to decode as ASCII string
                    ascii_str = info_slice.decode('ascii', errors='replace').rstrip('\x00')
                    if ascii_str.strip():
                        print(f"  Device info (ASCII): {ascii_str}")
            else:
                print("  RX: no response within 2s timeout")
        except Exception as e:
            print(f"  [!] Probe error: {e}")
        finally:
            try:
                h.close()
            except Exception:
                pass
