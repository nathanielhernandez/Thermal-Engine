"""
Settings management for Thermal Engine.
Handles persistent settings and Windows autostart.
"""

import os
import sys
import json

# Windows-only imports
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import winreg

from app_path import get_app_dir, get_resource_path
from security import escape_registry_path

APP_NAME = "ThermalEngine"
SETTINGS_FILE = get_resource_path("settings.json")

# Default settings
DEFAULT_SETTINGS = {
    "launch_at_login": True,
    "launch_minimized": True,
    "minimize_to_tray": True,
    "close_to_tray": True,
    "target_fps": 30,  # 30 FPS is smooth for most PCs
    "default_preset": None,  # Name of preset to load on startup (legacy fallback)
    "default_presets": {},  # Per-resolution defaults: {"WxH": "preset_name"}
    "overdrive_mode": False,
    "suppress_60fps_warning": False,  # Show warning when selecting 60 FPS
    "preferred_device": None,  # VID:PID of preferred device (e.g. "0416:5302")
}

_settings = None


def load_settings():
    """Load settings from file, creating defaults if needed."""
    global _settings

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                _settings = json.load(f)
            # Ensure all default keys exist
            for key, value in DEFAULT_SETTINGS.items():
                if key not in _settings:
                    _settings[key] = value
        except Exception as e:
            print(f"[Settings] Error loading settings: {e}")
            _settings = DEFAULT_SETTINGS.copy()
    else:
        _settings = DEFAULT_SETTINGS.copy()
        save_settings()  # Create the file with defaults

    return _settings


def save_settings():
    """Save current settings to file."""
    global _settings
    if _settings is None:
        _settings = DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(_settings, f, indent=2)
    except Exception as e:
        print(f"[Settings] Error saving settings: {e}")


def get_setting(key, default=None):
    """Get a setting value."""
    global _settings
    if _settings is None:
        load_settings()
    return _settings.get(key, default)


def set_setting(key, value):
    """Set a setting value and save."""
    global _settings
    if _settings is None:
        load_settings()
    _settings[key] = value
    save_settings()


def get_executable_path():
    """Get the path to use for autostart."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return escape_registry_path(sys.executable)
    else:
        # Running as script - use pythonw on Windows to avoid console window
        if IS_WINDOWS:
            python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
        else:
            python_exe = sys.executable
        script_path = get_resource_path('main.py')
        return f'{escape_registry_path(python_exe)} {escape_registry_path(script_path)}'


def set_autostart(enabled):
    """Enable or disable autostart. Windows-only via registry."""
    if not IS_WINDOWS:
        print("[Settings] Autostart is only supported on Windows")
        return False

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

        if enabled:
            exe_path = get_executable_path()
            # Add --minimized flag if launch_minimized is enabled
            if get_setting("launch_minimized", True):
                exe_path += " --minimized"
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass  # Already doesn't exist

        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Settings] Error setting autostart: {e}")
        return False


def is_autostart_enabled():
    """Check if autostart is currently enabled. Windows-only via registry."""
    if not IS_WINDOWS:
        return False

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def apply_autostart_setting():
    """Apply the current autostart setting to the registry. Windows-only."""
    if not IS_WINDOWS:
        return
    enabled = get_setting("launch_at_login", True)
    set_autostart(enabled)


# Initialize settings on module load
load_settings()

# Apply autostart setting (ensures registry matches setting file)
apply_autostart_setting()
