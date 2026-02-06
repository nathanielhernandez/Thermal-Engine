"""
AliLcdDevice - Stub driver for ALi chipset Thermalright LCD displays.

VID: 0x0416  PID: 0x5406
Protocol: JPEG frames over USB bulk transfers (LibUsbDotNet EP1 Read, EP2 Write).

Protocol details (from TRCC USBLCDNEW.dll decompilation):
  - Init packet: 1040 bytes (16-byte header + 1024 zeros)
    Header: {0xF5, 0x00, 0x01, 0x00, 0xBC, 0xFF, 0xB6, 0xC8, ...}, byte[13] = 0x04
  - Init response: first byte identifies screen variant:
    0x36 (54):  buffer 153600 bytes (smaller screen)
    0x65 (101): buffer 204800 bytes (larger screen)
    0x66 (102): buffer 204800 bytes (larger screen variant)
  - Frame packet: 16-byte header + JPEG data
    Header: {0xF5, 0x01, 0x01, 0x00, 0xBC, 0xFF, 0xB6, 0xC8, ...}
    Image size at bytes [12-15]
  - Frame send: single Write() of header+JPEG, then 16-byte Read() acknowledgment

STATUS: STUB - Not yet implemented. Needs a physical device to test and verify.
"""

from devices.base import BaseDevice, FrameFormat


class AliLcdDevice(BaseDevice):
    """Stub driver for ALi chipset Thermalright LCD.

    Known products using this chipset: unknown — needs identification
    from users with 0x0416:0x5406 devices.
    """

    # Protocol constants from TRCC decompilation
    INIT_HEADER = bytes([0xF5, 0x00, 0x01, 0x00, 0xBC, 0xFF, 0xB6, 0xC8,
                         0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00])
    FRAME_HEADER = bytes([0xF5, 0x01, 0x01, 0x00, 0xBC, 0xFF, 0xB6, 0xC8,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    INIT_PACKET_SIZE = 1040  # 16 header + 1024 zeros

    # Screen variant response bytes -> buffer sizes
    VARIANT_SMALL = 0x36   # 153600 byte buffer
    VARIANT_LARGE = 0x65   # 204800 byte buffer
    VARIANT_LARGE2 = 0x66  # 204800 byte buffer

    def __init__(self):
        self._device = None

    @property
    def device_name(self) -> str:
        return "ALi LCD"

    @property
    def vendor_id(self) -> int:
        return 0x0416

    @property
    def product_id(self) -> int:
        return 0x5406

    @property
    def display_width(self) -> int:
        return 480  # placeholder — actual resolution determined from init response

    @property
    def display_height(self) -> int:
        return 480  # placeholder

    @property
    def frame_format(self) -> FrameFormat:
        return FrameFormat.JPEG

    def open(self):
        raise NotImplementedError(
            "ALi LCD driver is a stub. A physical device (0x0416:0x5406) is needed to implement and test."
        )

    def close(self):
        pass

    def send_init(self):
        raise NotImplementedError("ALi LCD driver is a stub.")

    def send_frame(self, image):
        raise NotImplementedError("ALi LCD driver is a stub.")

    def diagnose(self):
        """Probe ALi LCD: send 1040-byte init, capture response."""
        self._print_hid_info()

        print("\n--- Init Probe ---")
        h, path = self._open_hid_device()
        if not h:
            return

        try:
            # Build 1040-byte init packet (16-byte header + 1024 zeros)
            init_packet = bytearray(self.INIT_PACKET_SIZE)
            init_packet[:len(self.INIT_HEADER)] = self.INIT_HEADER

            print(f"  Sending {self.INIT_PACKET_SIZE}-byte init packet...")
            print(f"  TX (first 32 bytes): {self._hex_dump(init_packet, 32)}")

            h.write(bytes(init_packet))

            rx = self._read_with_timeout(h, 64)
            if rx:
                print(f"  RX ({len(rx)} bytes):       {self._hex_dump(rx, 32)}")
                # Decode variant byte
                variant = rx[0] if rx else None
                if variant == self.VARIANT_SMALL:
                    print(f"  Variant: 0x{variant:02X} -> small screen (153600-byte buffer)")
                elif variant in (self.VARIANT_LARGE, self.VARIANT_LARGE2):
                    print(f"  Variant: 0x{variant:02X} -> large screen (204800-byte buffer)")
                else:
                    print(f"  Variant: 0x{variant:02X} -> unknown (not in expected set: 0x36, 0x65, 0x66)")
            else:
                print("  RX: no response within 2s timeout")
        except Exception as e:
            print(f"  [!] Probe error: {e}")
        finally:
            try:
                h.close()
            except Exception:
                pass
