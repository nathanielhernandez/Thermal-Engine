"""
Application path utilities.
Handles path resolution for both script and frozen executable.
"""

import sys
import os

def get_app_dir():
    """Get the application directory (works for both script and frozen exe)."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """Get absolute path to resource (works for both script and frozen exe)."""
    return os.path.join(get_app_dir(), relative_path)


# Commonly used paths
APP_DIR = get_app_dir()
