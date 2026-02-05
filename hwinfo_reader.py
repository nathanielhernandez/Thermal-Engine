"""
HWiNFO Shared Memory Reader

Reads sensor data from HWiNFO64's shared memory interface.
Requires HWiNFO to be running with "Shared Memory Support" enabled in settings.

Reference: https://www.hwinfo.com/forum/threads/shared-memory-layout.5149/
"""

import ctypes
from ctypes import Structure, c_uint, c_double, c_char, c_uint32, c_uint64, wintypes

# Windows API for shared memory access
kernel32 = ctypes.windll.kernel32

FILE_MAP_READ = 0x0004
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenFileMappingW.restype = wintypes.HANDLE

kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
kernel32.MapViewOfFile.restype = ctypes.c_void_p

kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
kernel32.UnmapViewOfFile.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

# HWiNFO Shared Memory Constants
HWINFO_SHARED_MEM_NAME = "Global\\HWiNFO_SENS_SM2"
HWINFO_SENSORS_STRING_LEN = 128
HWINFO_UNIT_STRING_LEN = 16


class HWiNFO_SENSORS_READING_ELEMENT(Structure):
    """Individual sensor reading structure."""
    _pack_ = 1
    _fields_ = [
        ("tReading", c_uint),           # Sensor type (temp, voltage, fan, etc.)
        ("dwSensorIndex", c_uint),      # Index of the sensor
        ("dwReadingID", c_uint),        # Unique ID of the reading
        ("szLabelOrig", c_char * HWINFO_SENSORS_STRING_LEN),  # Original label
        ("szLabelUser", c_char * HWINFO_SENSORS_STRING_LEN),  # User-defined label
        ("szUnit", c_char * HWINFO_UNIT_STRING_LEN),          # Unit string
        ("Value", c_double),            # Current value
        ("ValueMin", c_double),         # Minimum value
        ("ValueMax", c_double),         # Maximum value
        ("ValueAvg", c_double),         # Average value
    ]


class HWiNFO_SENSORS_SENSOR_ELEMENT(Structure):
    """Sensor element (hardware component) structure."""
    _pack_ = 1
    _fields_ = [
        ("dwSensorID", c_uint),         # Sensor ID
        ("dwSensorInst", c_uint),       # Sensor instance
        ("szSensorNameOrig", c_char * HWINFO_SENSORS_STRING_LEN),  # Original name
        ("szSensorNameUser", c_char * HWINFO_SENSORS_STRING_LEN),  # User-defined name
    ]


class HWiNFO_SENSORS_SHARED_MEM_HEADER(Structure):
    """Shared memory header structure."""
    _pack_ = 1
    _fields_ = [
        ("dwSignature", c_uint32),      # "HWiS" signature
        ("dwVersion", c_uint32),        # Structure version
        ("dwRevision", c_uint32),       # Revision
        ("pollTime", c_uint64),         # Poll time in ms
        ("dwOffsetOfSensorSection", c_uint32),  # Offset to sensor section
        ("dwSizeOfSensorElement", c_uint32),    # Size of sensor element
        ("dwNumSensorElements", c_uint32),      # Number of sensors
        ("dwOffsetOfReadingSection", c_uint32), # Offset to reading section
        ("dwSizeOfReadingElement", c_uint32),   # Size of reading element
        ("dwNumReadingElements", c_uint32),     # Number of readings
    ]


# Sensor type constants
SENSOR_TYPE_NONE = 0
SENSOR_TYPE_TEMP = 1
SENSOR_TYPE_VOLT = 2
SENSOR_TYPE_FAN = 3
SENSOR_TYPE_CURRENT = 4
SENSOR_TYPE_POWER = 5
SENSOR_TYPE_CLOCK = 6
SENSOR_TYPE_USAGE = 7
SENSOR_TYPE_OTHER = 8


class HWiNFOReader:
    """Reads sensor data from HWiNFO shared memory."""

    def __init__(self):
        self.handle = None
        self.view = None
        self.connected = False
        self.last_error = None
        self._sensor_cache = {}  # Cache sensor name -> index mapping
        self._view_size = 0

    def connect(self):
        """Connect to HWiNFO shared memory."""
        try:
            # Open the existing shared memory mapping
            self.handle = kernel32.OpenFileMappingW(FILE_MAP_READ, False, HWINFO_SHARED_MEM_NAME)
            if not self.handle:
                error = ctypes.get_last_error()
                self.last_error = f"OpenFileMappingW failed (error {error}). Is HWiNFO running with Shared Memory enabled?"
                return False

            # Map view of the file - map entire region (size=0)
            self.view = kernel32.MapViewOfFile(self.handle, FILE_MAP_READ, 0, 0, 0)
            if not self.view:
                error = ctypes.get_last_error()
                kernel32.CloseHandle(self.handle)
                self.handle = None
                self.last_error = f"MapViewOfFile failed (error {error})"
                return False

            self.connected = True
            self.last_error = None
            self._build_sensor_cache()
            return True
        except Exception as e:
            self.last_error = str(e)
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from shared memory."""
        if self.view:
            try:
                kernel32.UnmapViewOfFile(self.view)
            except:
                pass
            self.view = None
        if self.handle:
            try:
                kernel32.CloseHandle(self.handle)
            except:
                pass
            self.handle = None
        self.connected = False
        self._sensor_cache = {}

    def is_available(self):
        """Check if HWiNFO shared memory is available."""
        if self.connected:
            return True
        return self.connect()

    def _read_from_view(self, offset, size):
        """Read bytes from the memory view at given offset."""
        return (ctypes.c_char * size).from_address(self.view + offset).raw

    def _read_header(self):
        """Read the shared memory header."""
        if not self.view:
            return None
        header_size = ctypes.sizeof(HWiNFO_SENSORS_SHARED_MEM_HEADER)
        header_data = self._read_from_view(0, header_size)
        return HWiNFO_SENSORS_SHARED_MEM_HEADER.from_buffer_copy(header_data)

    def _read_sensors(self, header):
        """Read all sensor elements."""
        sensors = []
        offset = header.dwOffsetOfSensorSection
        for i in range(header.dwNumSensorElements):
            data = self._read_from_view(offset, header.dwSizeOfSensorElement)
            if len(data) >= ctypes.sizeof(HWiNFO_SENSORS_SENSOR_ELEMENT):
                sensor = HWiNFO_SENSORS_SENSOR_ELEMENT.from_buffer_copy(data)
                sensors.append(sensor)
            offset += header.dwSizeOfSensorElement
        return sensors

    def _read_readings(self, header):
        """Read all sensor readings."""
        readings = []
        offset = header.dwOffsetOfReadingSection
        for i in range(header.dwNumReadingElements):
            data = self._read_from_view(offset, header.dwSizeOfReadingElement)
            if len(data) >= ctypes.sizeof(HWiNFO_SENSORS_READING_ELEMENT):
                reading = HWiNFO_SENSORS_READING_ELEMENT.from_buffer_copy(data)
                readings.append(reading)
            offset += header.dwSizeOfReadingElement
        return readings

    def _build_sensor_cache(self):
        """Build a cache of sensor names to reading indices for fast lookup."""
        self._sensor_cache = {}
        try:
            header = self._read_header()
            if not header:
                return

            sensors = self._read_sensors(header)
            readings = self._read_readings(header)

            for i, reading in enumerate(readings):
                sensor_idx = reading.dwSensorIndex
                if sensor_idx < len(sensors):
                    sensor_name = sensors[sensor_idx].szSensorNameOrig.decode('utf-8', errors='ignore').strip()
                else:
                    sensor_name = "Unknown"

                label = reading.szLabelUser.decode('utf-8', errors='ignore').strip()
                if not label:
                    label = reading.szLabelOrig.decode('utf-8', errors='ignore').strip()

                # Create lookup key: "SensorName/ReadingLabel"
                key = f"{sensor_name}/{label}"
                self._sensor_cache[key] = i

                # Also store by just the label for common lookups
                self._sensor_cache[label] = i

        except Exception as e:
            self.last_error = str(e)

    def get_all_readings(self):
        """Get all sensor readings as a list of dicts."""
        if not self.is_available():
            return []

        try:
            header = self._read_header()
            if not header:
                return []

            sensors = self._read_sensors(header)
            readings = self._read_readings(header)

            results = []
            for reading in readings:
                sensor_idx = reading.dwSensorIndex
                if sensor_idx < len(sensors):
                    sensor_name = sensors[sensor_idx].szSensorNameOrig.decode('utf-8', errors='ignore').strip()
                else:
                    sensor_name = "Unknown"

                label = reading.szLabelUser.decode('utf-8', errors='ignore').strip()
                if not label:
                    label = reading.szLabelOrig.decode('utf-8', errors='ignore').strip()

                unit = reading.szUnit.decode('utf-8', errors='ignore').strip()

                results.append({
                    'sensor': sensor_name,
                    'label': label,
                    'unit': unit,
                    'value': reading.Value,
                    'min': reading.ValueMin,
                    'max': reading.ValueMax,
                    'avg': reading.ValueAvg,
                    'type': reading.tReading,
                })

            return results
        except Exception as e:
            self.last_error = str(e)
            return []

    def find_reading(self, patterns, sensor_type=None):
        """
        Find a reading matching any of the given patterns.

        Args:
            patterns: List of strings to search for in sensor/label names
            sensor_type: Optional sensor type filter (SENSOR_TYPE_*)

        Returns:
            Reading dict or None
        """
        readings = self.get_all_readings()

        for pattern in patterns:
            pattern_lower = pattern.lower()
            for reading in readings:
                if sensor_type is not None and reading['type'] != sensor_type:
                    continue

                # Check if pattern matches sensor name or label
                sensor_lower = reading['sensor'].lower()
                label_lower = reading['label'].lower()

                if pattern_lower in sensor_lower or pattern_lower in label_lower:
                    return reading

        return None

    def get_cpu_temp(self):
        """Get CPU temperature."""
        # Try common CPU temperature labels
        patterns = [
            'CPU Package',
            'CPU (Tctl/Tdie)',
            'CPU Tctl/Tdie',
            'Tctl/Tdie',
            'CPU Die',
            'CPU',
            'Core 0',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_TEMP)
        return reading['value'] if reading else 0.0

    def get_cpu_clock(self):
        """Get CPU clock speed."""
        patterns = [
            'Core 0 Clock',
            'CPU Core 0',
            'Core Clock',
            'CPU Clock',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_CLOCK)
        return reading['value'] if reading else 0

    def get_cpu_power(self):
        """Get CPU power consumption."""
        patterns = [
            'CPU Package Power',
            'CPU Power',
            'Package Power',
            'CPU PPT',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_POWER)
        return reading['value'] if reading else 0.0

    def get_gpu_temp(self):
        """Get GPU temperature."""
        patterns = [
            'GPU Temperature',
            'GPU Hot Spot',
            'GPU Core',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_TEMP)
        return reading['value'] if reading else 0.0

    def get_gpu_clock(self):
        """Get GPU core clock."""
        patterns = [
            'GPU Clock',
            'GPU Core Clock',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_CLOCK)
        return reading['value'] if reading else 0

    def get_gpu_memory_clock(self):
        """Get GPU memory clock."""
        patterns = [
            'GPU Memory Clock',
            'Memory Clock',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_CLOCK)
        return reading['value'] if reading else 0

    def get_gpu_usage(self):
        """Get GPU usage percentage."""
        patterns = [
            'GPU Core Load',
            'GPU Usage',
            'GPU Load',
            'GPU Utilization',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_USAGE)
        return reading['value'] if reading else 0.0

    def get_gpu_memory_usage(self):
        """Get GPU memory usage percentage."""
        patterns = [
            'GPU Memory Usage',
            'GPU Memory Load',
            'GPU Memory Allocated',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_USAGE)
        return reading['value'] if reading else 0.0

    def get_gpu_power(self):
        """Get GPU power consumption."""
        patterns = [
            'GPU Power',
            'GPU Total Power',
            'GPU Board Power',
            'GPU Chip Power',
        ]
        reading = self.find_reading(patterns, SENSOR_TYPE_POWER)
        return reading['value'] if reading else 0.0

    def get_thermal_sensors(self):
        """
        Get all thermal-related sensors in the format expected by ThermalEngine.

        Returns:
            dict with keys matching sensors.py format
        """
        return {
            'cpu_temp': self.get_cpu_temp(),
            'cpu_clock': int(self.get_cpu_clock()),
            'cpu_power': self.get_cpu_power(),
            'gpu_temp': self.get_gpu_temp(),
            'gpu_percent': self.get_gpu_usage(),
            'gpu_clock': int(self.get_gpu_clock()),
            'gpu_memory_clock': int(self.get_gpu_memory_clock()),
            'gpu_memory_percent': self.get_gpu_memory_usage(),
            'gpu_power': self.get_gpu_power(),
        }


# Global instance for easy access
_reader = None


def get_hwinfo_reader():
    """Get the global HWiNFO reader instance."""
    global _reader
    if _reader is None:
        _reader = HWiNFOReader()
    return _reader


def is_hwinfo_available():
    """Check if HWiNFO shared memory is available."""
    return get_hwinfo_reader().is_available()


def get_hwinfo_sensors():
    """Get sensor data from HWiNFO in ThermalEngine format."""
    reader = get_hwinfo_reader()
    if reader.is_available():
        return reader.get_thermal_sensors()
    return None


# Test function
if __name__ == "__main__":
    print("HWiNFO Shared Memory Reader Test")
    print("=" * 50)

    reader = HWiNFOReader()

    if reader.connect():
        print("Connected to HWiNFO shared memory!")
        print()

        # Get thermal sensors in ThermalEngine format
        sensors = reader.get_thermal_sensors()
        print("Thermal Sensors:")
        for key, value in sensors.items():
            print(f"  {key}: {value}")

        print()
        print("All available readings:")
        print("-" * 50)

        readings = reader.get_all_readings()
        for r in readings:
            print(f"[{r['sensor']}] {r['label']}: {r['value']:.1f} {r['unit']}")

        reader.disconnect()
    else:
        print(f"Failed to connect: {reader.last_error}")
        print()
        print("Make sure HWiNFO is running with 'Shared Memory Support' enabled:")
        print("  1. Open HWiNFO")
        print("  2. Go to Settings (gear icon)")
        print("  3. Check 'Shared Memory Support'")
        print("  4. Click OK and restart sensors")
