"""
Sensor monitoring using LibreHardwareMonitor.
"""

import sys
import os
import subprocess
import json
import threading
import time

# Persistent sensor helper script - runs continuously and responds to commands
SENSOR_HELPER_SCRIPT = '''
import sys
import json
import os
import time

computer = None

def init_lhm():
    global computer
    try:
        import clr
        from System.Reflection import Assembly
        from System import Activator

        app_dir = os.getcwd()
        dll_path = os.path.join(app_dir, "LibreHardwareMonitorLib.dll")

        if os.path.exists(dll_path):
            hidsharp = os.path.join(app_dir, "HidSharp.dll")
            if os.path.exists(hidsharp):
                try:
                    clr.AddReference(hidsharp)
                except:
                    pass

            clr.AddReference(dll_path)
            asm = Assembly.LoadFrom(dll_path)
            computer_type = asm.GetType("LibreHardwareMonitor.Hardware.Computer")

            computer = Activator.CreateInstance(computer_type)
            computer.IsCpuEnabled = True
            computer.IsGpuEnabled = True
            computer.Open()
            return True
    except Exception as e:
        print(json.dumps({"error": f"Init failed: {e}"}), flush=True)
        return False
    return False

def get_sensors():
    result = {
        "cpu_temp": 0,
        "cpu_clock": 0,
        "cpu_power": 0,
        "gpu_temp": 0,
        "gpu_percent": 0,
        "gpu_clock": 0,
        "gpu_memory_clock": 0,
        "gpu_memory_percent": 0,
        "gpu_power": 0,
    }
    gpu_edge_temp = 0  # Fallback if no hotspot/junction
    cpu_clocks = []  # Collect all core clocks to average

    if computer is None:
        return result

    try:
        for hardware in computer.Hardware:
            hardware.Update()
            hw_type = str(hardware.HardwareType)

            for sensor in hardware.Sensors:
                name = str(sensor.Name)
                stype = str(sensor.SensorType)
                val = sensor.Value

                if val is None:
                    continue

                # CPU sensors
                if "Cpu" in hw_type:
                    if stype == "Temperature":
                        if ("Tctl" in name or "Tdie" in name or "Package" in name) and result["cpu_temp"] == 0:
                            result["cpu_temp"] = float(val)
                        elif "Core" in name and result["cpu_temp"] == 0:
                            result["cpu_temp"] = float(val)
                    elif stype == "Clock":
                        if "Core" in name:
                            cpu_clocks.append(float(val))
                    elif stype == "Power":
                        if "Package" in name or "CPU" in name:
                            result["cpu_power"] = float(val)

                # GPU sensors
                elif "Gpu" in hw_type:
                    if stype == "Temperature":
                        if "Hot Spot" in name or "Junction" in name:
                            result["gpu_temp"] = float(val)
                        elif gpu_edge_temp == 0:
                            gpu_edge_temp = float(val)
                    elif stype == "Load":
                        if "Core" in name and result["gpu_percent"] == 0:
                            result["gpu_percent"] = float(val)
                        elif "Memory" in name and result["gpu_memory_percent"] == 0:
                            result["gpu_memory_percent"] = float(val)
                    elif stype == "Clock":
                        if "Core" in name and result["gpu_clock"] == 0:
                            result["gpu_clock"] = float(val)
                        elif "Memory" in name and result["gpu_memory_clock"] == 0:
                            result["gpu_memory_clock"] = float(val)
                    elif stype == "Power":
                        if result["gpu_power"] == 0:
                            result["gpu_power"] = float(val)

            for subhw in hardware.SubHardware:
                subhw.Update()
                for sensor in subhw.Sensors:
                    name = str(sensor.Name)
                    stype = str(sensor.SensorType)
                    val = sensor.Value
                    if val is None:
                        continue
                    if stype == "Temperature" and result["cpu_temp"] == 0:
                        if "Tctl" in name or "Tdie" in name or "Core" in name:
                            result["cpu_temp"] = float(val)
                    elif stype == "Clock" and "Core" in name:
                        cpu_clocks.append(float(val))

    except Exception as e:
        result["error"] = str(e)

    # Use edge temp as fallback if no hotspot found
    if result["gpu_temp"] == 0 and gpu_edge_temp > 0:
        result["gpu_temp"] = gpu_edge_temp

    # Average CPU clock
    if cpu_clocks:
        result["cpu_clock"] = sum(cpu_clocks) / len(cpu_clocks)

    return result

if __name__ == "__main__":
    if not init_lhm():
        sys.exit(1)

    print(json.dumps({"status": "ready"}), flush=True)

    # Main loop - respond to read commands
    while True:
        try:
            line = sys.stdin.readline().strip()
            if line == "read":
                print(json.dumps(get_sensors()), flush=True)
            elif line == "quit":
                break
        except:
            break

    if computer:
        try:
            computer.Close()
        except:
            pass
'''


class SensorProcess:
    """Manages a persistent subprocess for sensor reading."""

    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.last_data = {
            "cpu_temp": 0,
            "cpu_clock": 0,
            "cpu_power": 0,
            "gpu_temp": 0,
            "gpu_percent": 0,
            "gpu_clock": 0,
            "gpu_memory_clock": 0,
            "gpu_memory_percent": 0,
            "gpu_power": 0,
        }
        self.ready = False
        self.error = None

    def start(self, app_dir=None):
        if app_dir is None:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-c", SENSOR_HELPER_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=app_dir,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            # Wait for ready signal
            line = self.process.stdout.readline().strip()
            if line:
                data = json.loads(line)
                if data.get("status") == "ready":
                    self.ready = True
                    return True
                elif "error" in data:
                    self.error = data["error"]
        except Exception as e:
            self.error = str(e)
        return False

    def read(self):
        if not self.ready or not self.process:
            return self.last_data

        with self.lock:
            try:
                self.process.stdin.write("read\n")
                self.process.stdin.flush()
                line = self.process.stdout.readline().strip()
                if line:
                    data = json.loads(line)
                    if "error" not in data:
                        self.last_data = data
                    return data
            except Exception:
                pass
        return self.last_data

    def stop(self):
        if self.process:
            try:
                self.process.stdin.write("quit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None


# Global sensor process and cache
_sensor_process = SensorProcess()
_sensor_cache = {"data": None, "time": 0}
_SENSOR_UPDATE_INTERVAL = 0.5  # Update sensors every 500ms

# Track initialization state
HAS_LHM = False
LHM_ERROR = None

# Background sensor thread
_sensor_thread = None
_sensor_thread_running = False
_sensor_data_lock = threading.Lock()
_latest_sensor_data = {
    "cpu_temp": 0,
    "cpu_clock": 0,
    "cpu_power": 0,
    "gpu_temp": 0,
    "gpu_percent": 0,
    "gpu_clock": 0,
    "gpu_memory_clock": 0,
    "gpu_memory_percent": 0,
    "gpu_power": 0,
}


def _sensor_polling_thread():
    """Background thread that continuously polls sensors."""
    global _latest_sensor_data, _sensor_thread_running

    while _sensor_thread_running:
        try:
            data = _sensor_process.read()
            if data:
                with _sensor_data_lock:
                    _latest_sensor_data = data.copy()
        except Exception as e:
            print(f"[Sensors] Background poll error: {e}")

        # Sleep for update interval
        time.sleep(_SENSOR_UPDATE_INTERVAL)


def init_sensors(app_dir=None):
    """Initialize the sensor process and start background polling. Call this at app startup."""
    global HAS_LHM, LHM_ERROR, _sensor_cache, _sensor_thread, _sensor_thread_running, _latest_sensor_data

    HAS_LHM = _sensor_process.start(app_dir)
    LHM_ERROR = _sensor_process.error

    if HAS_LHM:
        print(f"[Sensors] LibreHardwareMonitor persistent process started")
        # Do initial read to populate cache
        initial_data = _sensor_process.read()
        _sensor_cache = {"data": initial_data, "time": time.time()}
        with _sensor_data_lock:
            _latest_sensor_data = initial_data.copy() if initial_data else _latest_sensor_data

        # Start background polling thread
        _sensor_thread_running = True
        _sensor_thread = threading.Thread(target=_sensor_polling_thread, daemon=True)
        _sensor_thread.start()
        print(f"[Sensors] Background polling thread started")
    elif LHM_ERROR:
        print(f"[Sensor Warning] {LHM_ERROR}")
    else:
        print(f"[Sensor Warning] LibreHardwareMonitor not available")

    return HAS_LHM


def get_lhm_sensors():
    """Get sensor data from background thread cache (non-blocking)."""
    global _latest_sensor_data

    with _sensor_data_lock:
        return _latest_sensor_data.copy()


def get_lhm_sensors_sync():
    """Get sensor data synchronously (for diagnostic use only)."""
    global _sensor_cache

    current_time = time.time()
    if _sensor_cache["data"] is not None and (current_time - _sensor_cache["time"]) < _SENSOR_UPDATE_INTERVAL:
        return _sensor_cache["data"]

    data = _sensor_process.read()
    _sensor_cache = {"data": data, "time": current_time}
    return data


def stop_sensors():
    """Stop the sensor process and background thread. Call this at app shutdown."""
    global _sensor_thread_running, _sensor_thread

    _sensor_thread_running = False
    if _sensor_thread and _sensor_thread.is_alive():
        _sensor_thread.join(timeout=1.0)
    _sensor_thread = None

    _sensor_process.stop()
