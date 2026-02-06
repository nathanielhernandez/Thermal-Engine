"""
DeviceManager - Handles device enumeration, connection lifecycle, and frame sending.

Supports multiple simultaneous device connections keyed by "vid:pid".
"""

try:
    import hid
    HAS_HID = True
except ImportError:
    HAS_HID = False

from devices.registry import DEVICE_REGISTRY, get_driver_for_device


class DeviceManager:
    """Manages multiple LCD device connections.

    Provides enumeration, connect/disconnect per device, and cleanup.
    Sessions own their device references and send frames directly.
    """

    def __init__(self):
        self._connected_devices = {}  # "vid:pid" -> BaseDevice

        # Callbacks (set by main_window)
        self.on_connected = None      # (device, device_key)
        self.on_disconnected = None   # (device_key,)
        self.on_error = None

    # -- Properties --

    @property
    def is_connected(self):
        """True if at least one device is currently connected."""
        return len(self._connected_devices) > 0

    @property
    def connected_keys(self):
        """Set of currently connected device keys."""
        return set(self._connected_devices.keys())

    def get_device(self, device_key):
        """Get a connected device by key, or None."""
        return self._connected_devices.get(device_key)

    # -- Enumeration --

    def enumerate_devices(self):
        """Scan HID bus for known devices.

        Returns:
            List of dicts: [{"vid": int, "pid": int, "name": str,
                             "width": int, "height": int, "path": bytes}, ...]
        """
        if not HAS_HID:
            return []

        found = []
        seen = set()

        try:
            for dev_info in hid.enumerate():
                vid = dev_info["vendor_id"]
                pid = dev_info["product_id"]
                key = (vid, pid)

                if key in DEVICE_REGISTRY and key not in seen:
                    seen.add(key)
                    driver_class = DEVICE_REGISTRY[key]
                    # Instantiate temporarily to read properties
                    tmp = driver_class()
                    found.append({
                        "vid": vid,
                        "pid": pid,
                        "name": tmp.device_name,
                        "width": tmp.display_width,
                        "height": tmp.display_height,
                        "path": dev_info.get("path", b""),
                    })
        except Exception as e:
            print(f"[DeviceManager] Enumeration error: {e}")

        return found

    # -- Connection --

    def connect(self, vid, pid):
        """Connect to a specific device by VID/PID (does not disconnect others).

        Returns:
            The BaseDevice on success, None on failure.
        """
        device_key = f"{vid:04x}:{pid:04x}"

        # Already connected?
        if device_key in self._connected_devices:
            return self._connected_devices[device_key]

        driver = get_driver_for_device(vid, pid)
        if not driver:
            print(f"[DeviceManager] No driver for {vid:#06x}:{pid:#06x}")
            return None

        try:
            print(f"[DeviceManager] Opening {driver.device_name} ({device_key})...")
            driver.open()
            print(f"[DeviceManager] Device opened, sending init...")
            driver.send_init()
            print(f"[DeviceManager] Init complete: {driver}")
            self._connected_devices[device_key] = driver
            print(f"[DeviceManager] Connected to {driver}")
            if self.on_connected:
                self.on_connected(driver, device_key)
            return driver
        except NotImplementedError:
            # Stub driver — run diagnostic probe instead
            print(f"\n{'=' * 55}")
            print(f"  Device Diagnostic: {driver.device_name} ({driver.vendor_id:#06x}:{driver.product_id:#06x})")
            print(f"{'=' * 55}")
            print("This device has a stub driver. Collecting diagnostic data...\n")
            try:
                driver.diagnose()
            except Exception as diag_err:
                print(f"  [!] Diagnostic failed: {diag_err}")
            print(f"\n{'=' * 55}")
            print("  Diagnostic Complete")
            print(f"{'=' * 55}")
            print("Please copy the output above and share it at:")
            print("  https://github.com/nathanielhernandez/ThermalEngine/issues")
            print("This data helps us implement support for your device.\n")
            return None
        except Exception as e:
            print(f"[DeviceManager] Connect failed: {e}")
            try:
                driver.close()
            except:
                pass
            if self.on_error:
                self.on_error(e)
            return None

    def disconnect(self, vid, pid):
        """Disconnect a specific device by VID/PID."""
        device_key = f"{vid:04x}:{pid:04x}"
        device = self._connected_devices.pop(device_key, None)
        if device:
            try:
                device.close()
            except Exception as e:
                print(f"[DeviceManager] Error during disconnect: {e}")
            print(f"[DeviceManager] Disconnected {device.device_name}")
            if self.on_disconnected:
                self.on_disconnected(device_key)

    def disconnect_all(self):
        """Disconnect all connected devices."""
        for device_key in list(self._connected_devices.keys()):
            device = self._connected_devices.pop(device_key)
            try:
                device.close()
            except Exception as e:
                print(f"[DeviceManager] Error disconnecting {device_key}: {e}")
            print(f"[DeviceManager] Disconnected {device.device_name}")
        if self.on_disconnected:
            self.on_disconnected(None)

    # -- Sleep/Wake --

    def notify_sleep(self):
        """Notify all connected devices of system sleep."""
        for device in self._connected_devices.values():
            device.on_sleep()

    def notify_wake(self):
        """Notify all connected devices of system wake."""
        for device in self._connected_devices.values():
            device.on_wake()

    # -- Cleanup --

    def cleanup(self):
        """Release all resources."""
        self.disconnect_all()
