"""
Devices package - Multi-device support for ThermalEngine.

Provides device abstraction, discovery, and protocol drivers for
Thermalright LCD displays connected via HID.
"""

from devices.base import BaseDevice, FrameFormat
from devices.registry import DEVICE_REGISTRY, get_driver_for_device
from devices.manager import DeviceManager

__all__ = [
    "BaseDevice",
    "FrameFormat",
    "DEVICE_REGISTRY",
    "get_driver_for_device",
    "DeviceManager",
]
