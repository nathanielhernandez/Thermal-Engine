"""
Settings management for Thermal Engine.
Handles persistent settings and Windows autostart.
"""

import os
import sys
import json
import winreg

APP_NAME = "ThermalEngine"
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

# Default settings
DEFAULT_SETTINGS = {
    "launch_at_login": True,
    "launch_minimized": True,
    "minimize_to_tray": True,
    "close_to_tray": True,
    "target_fps": 10,
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
        return sys.executable
    else:
        # Running as script - use pythonw to avoid console window
        python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'main.py'))
        return f'"{python_exe}" "{script_path}"'


def set_autostart(enabled):
    """Enable or disable Windows autostart via registry."""
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
    """Check if autostart is currently enabled in registry."""
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
    """Apply the current autostart setting to the registry."""
    enabled = get_setting("launch_at_login", True)
    set_autostart(enabled)


# Initialize settings on module load
load_settings()

# Apply autostart setting (ensures registry matches setting file)
apply_autostart_setting()
