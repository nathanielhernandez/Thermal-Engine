"""
LianYunDevice - Stub driver for LianYun (LY) chipset Thermalright LCD displays.

VID: 0x0416  PID: 0x5408
Protocol: JPEG frames over USB bulk transfers (LibUsbDotNet EP1 Read, EP9 Write).

Protocol details (from TRCC USBLCDNEW.dll decompilation):
  - Init packet: 2048 bytes (16-byte header + 2032 zeros)
    Header: {0x02, 0xFF, 0x00, ...}, byte[8] = 1
  - Init response validation: bytes[0] == 3, bytes[1] == 0xFF, bytes[8] == 1
  - Frame chunking: 512-byte packets
    Each chunk: 16-byte header + 496 bytes payload
    Chunk header: {0x01, 0xFF, size[0-3], chunk_len[0-1], cmd_type=1,
                   total_chunks[0-1], chunk_idx[0-1], ...}
  - Frame data starts at byte offset 64
  - Writes in 4096-byte bursts (2048 for last chunk)
  - Reads 512-byte acknowledgment after all chunks sent
  - NOTE: Uses EP9 for writes (unusual), not EP2

STATUS: STUB - Not yet implemented. Needs a physical device to test and verify.
"""

from devices.base import BaseDevice, FrameFormat


class LianYunDevice(BaseDevice):
    """Stub driver for LianYun (LY) chipset Thermalright LCD.

    Known products using this chipset: unknown — needs identification
    from users with 0x0416:0x5408 devices.
    """

    # Protocol constants from TRCC decompilation
    INIT_HEADER = bytes([0x02, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                         0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    CHUNK_HEADER_PREFIX = bytes([0x01, 0xFF])
    INIT_PACKET_SIZE = 2048  # 16 header + 2032 zeros
    CHUNK_SIZE = 512         # 16-byte header + 496-byte payload
    BURST_SIZE = 4096
    FRAME_OFFSET = 64
    WRITE_ENDPOINT = 9       # EP9 — unusual
    CMD_TYPE = 1

    def __init__(self):
        self._device = None

    @property
    def device_name(self) -> str:
        return "LianYun LCD"

    @property
    def vendor_id(self) -> int:
        return 0x0416

    @property
    def product_id(self) -> int:
        return 0x5408

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
            "LianYun LCD driver is a stub. A physical device (0x0416:0x5408) is needed to implement and test."
        )

    def close(self):
        pass

    def send_init(self):
        raise NotImplementedError("LianYun LCD driver is a stub.")

    def send_frame(self, image):
        raise NotImplementedError("LianYun LCD driver is a stub.")

    def diagnose(self):
        """Probe LianYun LCD: send 2048-byte init, capture response."""
        self._print_hid_info()

        print("\n--- Init Probe ---")
        h, path = self._open_hid_device()
        if not h:
            return

        try:
            # Build 2048-byte init packet (16-byte header + 2032 zeros)
            init_packet = bytearray(self.INIT_PACKET_SIZE)
            init_packet[:len(self.INIT_HEADER)] = self.INIT_HEADER

            print(f"  Sending {self.INIT_PACKET_SIZE}-byte init packet...")
            print(f"  TX (first 32 bytes): {self._hex_dump(init_packet, 32)}")

            h.write(bytes(init_packet))

            rx = self._read_with_timeout(h, 512)
            if rx:
                print(f"  RX ({len(rx)} bytes):       {self._hex_dump(rx, 32)}")
                # Validate expected response pattern
                ok_0 = rx[0] == 3 if len(rx) > 0 else False
                ok_1 = rx[1] == 0xFF if len(rx) > 1 else False
                ok_8 = rx[8] == 1 if len(rx) > 8 else False
                print(f"  Validation: bytes[0]==3: {ok_0}, bytes[1]==0xFF: {ok_1}, bytes[8]==1: {ok_8}")
            else:
                print("  RX: no response within 2s timeout")
        except Exception as e:
            print(f"  [!] Probe error: {e}")
        finally:
            try:
                h.close()
            except Exception:
                pass
