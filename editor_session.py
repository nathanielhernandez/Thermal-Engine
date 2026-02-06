"""
EditorSession - Per-device editing state.

Each connected device (or the offline fallback) gets its own session
holding elements, undo/redo stacks, video background, and frame buffer.
"""

import threading
from video_background import VideoBackground


class EditorSession:
    """Holds all editor state for a single device session."""

    def __init__(self, device=None, resolution=(1280, 480)):
        # Device reference (None for offline session)
        self.device = device

        # Session identity
        if device is not None:
            self.device_key = f"{device.vendor_id:04x}:{device.product_id:04x}"
        else:
            self.device_key = "offline"

        self.resolution = resolution

        # Theme state
        self.theme_name = "Untitled Theme"
        self.background_color = "#0f0f19"
        self.elements = []

        # Undo / Redo
        self.undo_stack = []
        self.redo_stack = []

        # Video background (each session owns its own instance)
        self.video_bg = VideoBackground()

        # Frame buffer for overdrive mode
        self.frame_buffer = None
        self.frame_buffer_lock = threading.Lock()
