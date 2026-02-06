"""
Device Registry - Maps (vendor_id, product_id) pairs to device driver classes.
"""

from devices.trofeo_vision import TrofeoVisionDevice
from devices.ali_lcd import AliLcdDevice
from devices.lianyun import LianYunDevice
from devices.lianyun_v2 import LianYunV2Device
from devices.xsail import XsailDevice
from devices.dummy import DummyDevice

# Registry of known devices: (vid, pid) -> driver class
DEVICE_REGISTRY = {
    (0x0416, 0x5302): TrofeoVisionDevice,   # Thermalright Trofeo Vision (1280x480)
    (0x0416, 0x5406): AliLcdDevice,          # ALi chipset LCD (stub)
    (0x0416, 0x5408): LianYunDevice,         # LianYun LY chipset LCD (stub)
    (0x0416, 0x5409): LianYunV2Device,       # LianYun V2 LY1 chipset LCD (stub)
    (0x87AD, 0x70DB): XsailDevice,           # Older Xsail-based LCD (stub)
    (0xFFFF, 0x0001): DummyDevice,           # Virtual test device (no USB)
}


def get_driver_for_device(vendor_id, product_id):
    """Look up and instantiate a driver for the given VID/PID.

    Returns:
        A BaseDevice instance, or None if no driver is registered.
    """
    driver_class = DEVICE_REGISTRY.get((vendor_id, product_id))
    if driver_class:
        return driver_class()
    return None
