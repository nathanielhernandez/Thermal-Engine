"""
Sensor monitoring using LibreHardwareMonitor via SensorHelperApp.exe.
Includes automatic recovery after sleep/restart/power loss.
"""

import sys
import os
import subprocess
import json
import threading
import time
import queue


class SensorProcess:
    """Manages a persistent subprocess for sensor reading with auto-recovery."""

    def __init__(self):
        self.process = None
        self.lock = threading.RLock()  # Reentrant lock for nested calls
        self.restart_lock = threading.Lock()  # Separate lock for restart
        self.app_dir = None
        self.helper_exe = None
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
        self.consecutive_failures = 0
        self.max_failures = 3
        self.last_successful_read = 0
        self._restart_in_progress = False
        self._read_thread = None
        self._response_queue = queue.Queue()

    def _find_helper_exe(self, app_dir):
        """Find SensorHelperApp.exe in various locations."""
        candidates = [
            os.path.join(app_dir, "SensorHelperApp.exe"),
            os.path.join(app_dir, "lhm", "SensorHelperApp.exe"),
            os.path.join(app_dir, "SensorHelperApp", "bin", "Release", "net10.0-windows", "SensorHelperApp.exe"),
            os.path.join(app_dir, "SensorHelperApp", "bin", "Release", "net8.0-windows", "SensorHelperApp.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _is_process_alive(self):
        """Check if the subprocess is still running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    def _is_pipe_healthy(self):
        """Check if pipes are still usable."""
        if self.process is None:
            return False
        try:
            # Check if pipes are closed
            if self.process.stdin.closed or self.process.stdout.closed:
                return False
            return True
        except:
            return False

    def start(self, app_dir=None):
        """Start the sensor helper process."""
        if app_dir is None:
            from app_path import get_app_dir
            app_dir = get_app_dir()

        self.app_dir = app_dir
        self.helper_exe = self._find_helper_exe(app_dir)

        if not self.helper_exe:
            self.error = "SensorHelperApp.exe not found"
            return False

        return self._start_process()

    def _start_process(self):
        """Internal method to start/restart the process."""
        # Kill any existing process
        self._kill_process()

        self.ready = False
        self.error = None
        self.consecutive_failures = 0

        # Clear any old responses
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except:
                break

        try:
            self.process = subprocess.Popen(
                [self.helper_exe],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=os.path.dirname(self.helper_exe),
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            # Start background reader thread
            self._start_reader_thread()

            # Wait for ready signal with timeout
            try:
                line = self._response_queue.get(timeout=10)
                if line:
                    data = json.loads(line)
                    if data.get("status") == "ready":
                        self.ready = True
                        self.last_successful_read = time.time()
                        return True
                    elif "error" in data:
                        self.error = data["error"]
            except queue.Empty:
                self.error = "No response from sensor process (timeout)"
            except json.JSONDecodeError as e:
                self.error = f"Invalid response: {e}"

        except Exception as e:
            self.error = str(e)

        return False

    def _start_reader_thread(self):
        """Start a dedicated thread for reading stdout."""
        if self._read_thread and self._read_thread.is_alive():
            return  # Already running

        def reader():
            while self.process and self._is_process_alive():
                try:
                    if self.process.stdout.closed:
                        break
                    line = self.process.stdout.readline()
                    if line:
                        self._response_queue.put(line.strip())
                    elif not self._is_process_alive():
                        break
                except:
                    break

        self._read_thread = threading.Thread(target=reader, daemon=True)
        self._read_thread.start()

    def _kill_process(self):
        """Kill the subprocess if running."""
        if self.process:
            try:
                if not self.process.stdin.closed:
                    self.process.stdin.write("quit\n")
                    self.process.stdin.flush()
            except:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                pass
            try:
                self.process.kill()
            except:
                pass
            try:
                self.process.wait(timeout=1)
            except:
                pass
            self.process = None
        self.ready = False

    def restart(self):
        """Restart the sensor process (thread-safe)."""
        # Prevent concurrent restarts
        if not self.restart_lock.acquire(blocking=False):
            return False  # Another restart in progress

        try:
            if self._restart_in_progress:
                return False
            self._restart_in_progress = True

            print("[Sensors] Restarting sensor process...")
            if self._start_process():
                print("[Sensors] Sensor process restarted successfully")
                return True
            else:
                print(f"[Sensors] Failed to restart: {self.error}")
                return False
        finally:
            self._restart_in_progress = False
            self.restart_lock.release()

    def read(self):
        """Read sensor data, with automatic recovery on failure."""
        if not self.helper_exe:
            return self.last_data

        # Quick checks without lock
        if not self._is_process_alive() or not self._is_pipe_healthy():
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.max_failures:
                self.restart()
            return self.last_data

        if not self.ready:
            return self.last_data

        with self.lock:
            try:
                # Write command
                if self.process.stdin.closed:
                    raise BrokenPipeError("stdin closed")
                self.process.stdin.write("read\n")
                self.process.stdin.flush()

                # Wait for response with timeout
                try:
                    line = self._response_queue.get(timeout=5)
                    if line:
                        data = json.loads(line)
                        if "error" not in data:
                            self.last_data = data
                            self.consecutive_failures = 0
                            self.last_successful_read = time.time()
                            return data
                except queue.Empty:
                    pass  # Timeout
                except json.JSONDecodeError:
                    pass

                # Read failed
                self.consecutive_failures += 1

            except (BrokenPipeError, OSError) as e:
                # Pipe error - process likely dead or pipes broken
                self.consecutive_failures = self.max_failures  # Force restart
            except Exception as e:
                self.consecutive_failures += 1

        # Check if we should restart
        if self.consecutive_failures >= self.max_failures:
            self.restart()

        return self.last_data

    def stop(self):
        """Stop the sensor process."""
        self._kill_process()


# Global sensor process
_sensor_process = SensorProcess()
_SENSOR_UPDATE_INTERVAL = 0.5
_HEALTH_CHECK_INTERVAL = 10

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
    """Background thread that continuously polls sensors with health monitoring."""
    global _latest_sensor_data, _sensor_thread_running, HAS_LHM

    last_health_check = time.time()
    restart_backoff = 0  # Exponential backoff for restarts

    while _sensor_thread_running:
        try:
            current_time = time.time()

            # Periodic health check
            if current_time - last_health_check > _HEALTH_CHECK_INTERVAL:
                last_health_check = current_time

                # Check if process seems stuck (no successful read in 30 seconds)
                if _sensor_process.ready and _sensor_process.last_successful_read > 0:
                    time_since_success = current_time - _sensor_process.last_successful_read
                    if time_since_success > 30:
                        print(f"[Sensors] No successful read in {time_since_success:.0f}s, restarting...")
                        if _sensor_process.restart():
                            restart_backoff = 0
                        else:
                            restart_backoff = min(restart_backoff + 1, 6)  # Max ~60 sec backoff

                # Try to start if not running (with backoff)
                if not _sensor_process.ready:
                    if restart_backoff == 0 or current_time % (10 * (2 ** restart_backoff)) < _HEALTH_CHECK_INTERVAL:
                        if _sensor_process.restart():
                            HAS_LHM = True
                            restart_backoff = 0
                        else:
                            restart_backoff = min(restart_backoff + 1, 6)

            # Normal sensor read
            data = _sensor_process.read()
            if data:
                with _sensor_data_lock:
                    _latest_sensor_data = data.copy()

        except Exception as e:
            print(f"[Sensors] Background poll error: {e}")

        time.sleep(_SENSOR_UPDATE_INTERVAL)


def init_sensors(app_dir=None):
    """Initialize the sensor process and start background polling."""
    global HAS_LHM, LHM_ERROR, _sensor_thread, _sensor_thread_running, _latest_sensor_data

    # Stop any existing thread first
    if _sensor_thread_running:
        stop_sensors()

    HAS_LHM = _sensor_process.start(app_dir)
    LHM_ERROR = _sensor_process.error

    if HAS_LHM:
        print("[Sensors] SensorHelperApp process started")
        # Do initial read
        initial_data = _sensor_process.read()
        with _sensor_data_lock:
            if initial_data:
                _latest_sensor_data = initial_data.copy()

        # Start background polling thread
        _sensor_thread_running = True
        _sensor_thread = threading.Thread(target=_sensor_polling_thread, daemon=True)
        _sensor_thread.start()
        print("[Sensors] Background polling started (with auto-recovery)")
    else:
        # Start polling thread anyway - it will retry periodically
        _sensor_thread_running = True
        _sensor_thread = threading.Thread(target=_sensor_polling_thread, daemon=True)
        _sensor_thread.start()

        if LHM_ERROR:
            print(f"[Sensor Warning] {LHM_ERROR} (will retry)")
        else:
            print("[Sensor Warning] SensorHelperApp not available (will retry)")

    return HAS_LHM


def get_lhm_sensors():
    """Get sensor data from background thread cache (non-blocking)."""
    with _sensor_data_lock:
        return _latest_sensor_data.copy()


def get_lhm_sensors_sync():
    """Get sensor data synchronously."""
    return _sensor_process.read()


def stop_sensors():
    """Stop the sensor process and background thread."""
    global _sensor_thread_running, _sensor_thread

    print("[Sensors] Stopping sensor monitoring...")

    _sensor_thread_running = False
    if _sensor_thread and _sensor_thread.is_alive():
        _sensor_thread.join(timeout=3.0)
    _sensor_thread = None

    _sensor_process.stop()
    print("[Sensors] Sensor monitoring stopped")
