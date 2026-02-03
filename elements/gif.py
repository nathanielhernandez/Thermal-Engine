"""
GIF Element

Displays animated GIF images with proper frame timing.
"""

import os
import time
import sys
from PIL import Image as PILImage

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QPen, QColor

# Add parent directory to path for security import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import is_safe_path

ELEMENT_TYPE = "gif"
ELEMENT_NAME = "GIF Image"

DEFAULT_PROPS = {
    "x": 100,
    "y": 100,
    "width": 200,
    "height": 200,
    "gif_path": "",
    "scale_mode": "fit",  # "fit", "fill", "stretch"
}

# Cache for loaded GIFs - stores frames and timing info per path
_gif_cache = {}

# Playback state per element
_playback_state = {}


def reset_all_playback():
    """Reset all GIF playback timing after system wake or other disruption."""
    global _playback_state
    current_time = time.time()
    # Reset all start times to now to prevent frame jumps
    for key in _playback_state:
        _playback_state[key]['start_time'] = current_time


class GifData:
    """Stores extracted GIF data."""
    def __init__(self, path):
        self.path = path
        self.frames = []  # List of PIL Image frames
        self.durations = []  # Duration for each frame in seconds
        self.total_duration = 0
        self.width = 0
        self.height = 0
        self.loaded = False
        self.error = None

    def load(self):
        """Load and extract all frames from the GIF."""
        try:
            if not os.path.exists(self.path):
                self.error = "File not found"
                return False

            gif = PILImage.open(self.path)
            self.width = gif.width
            self.height = gif.height

            # Extract all frames
            self.frames = []
            self.durations = []

            try:
                while True:
                    # Convert frame to RGBA
                    frame = gif.convert('RGBA')
                    self.frames.append(frame.copy())

                    # Get frame duration (in milliseconds, default to 100ms)
                    duration = gif.info.get('duration', 100) / 1000.0
                    if duration <= 0:
                        duration = 0.1
                    self.durations.append(duration)
                    self.total_duration += duration

                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass  # End of frames

            if len(self.frames) == 0:
                self.error = "No frames found"
                return False

            self.loaded = True
            return True

        except Exception as e:
            self.error = str(e)
            return False


def get_gif_data(path):
    """Get or load GIF data from cache."""
    if not path:
        return None

    if path not in _gif_cache:
        gif_data = GifData(path)
        gif_data.load()
        _gif_cache[path] = gif_data

    return _gif_cache[path]


def get_current_frame_index(element, gif_data):
    """Get the current frame index based on elapsed time."""
    if not gif_data or not gif_data.loaded or len(gif_data.frames) <= 1:
        return 0

    key = getattr(element, 'name', id(element))
    current_time = time.time()

    if key not in _playback_state:
        _playback_state[key] = {'start_time': current_time}

    elapsed = current_time - _playback_state[key]['start_time']

    # Loop the animation
    elapsed = elapsed % gif_data.total_duration

    # Find the current frame
    accumulated = 0
    for i, duration in enumerate(gif_data.durations):
        accumulated += duration
        if elapsed < accumulated:
            return i

    return len(gif_data.frames) - 1


def get_scaled_frame(frame, element_width, element_height, scale_mode):
    """Scale a frame according to the scale mode."""
    frame_width, frame_height = frame.size

    if scale_mode == "stretch":
        # Stretch to fill exactly
        return frame.resize((element_width, element_height), PILImage.Resampling.LANCZOS)

    elif scale_mode == "fill":
        # Scale to fill, crop excess
        scale = max(element_width / frame_width, element_height / frame_height)
        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)
        scaled = frame.resize((new_width, new_height), PILImage.Resampling.LANCZOS)

        # Crop to center
        left = (new_width - element_width) // 2
        top = (new_height - element_height) // 2
        return scaled.crop((left, top, left + element_width, top + element_height))

    else:  # "fit" - default
        # Scale to fit within bounds, maintain aspect ratio
        scale = min(element_width / frame_width, element_height / frame_height)
        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)
        scaled = frame.resize((new_width, new_height), PILImage.Resampling.LANCZOS)

        # Center on transparent background
        result = PILImage.new('RGBA', (element_width, element_height), (0, 0, 0, 0))
        x_offset = (element_width - new_width) // 2
        y_offset = (element_height - new_height) // 2
        result.paste(scaled, (x_offset, y_offset), scaled)
        return result


def draw_preview(painter, element, x, y, scale):
    """Draw the GIF in the Qt preview canvas."""
    width = int(element.width * scale)
    height = int(element.height * scale)

    gif_path = getattr(element, 'gif_path', '')
    scale_mode = getattr(element, 'scale_mode', 'fit')

    # Validate path is safe before loading
    if gif_path:
        safe, _, err = is_safe_path(gif_path, allow_absolute=True)
        if not safe:
            painter.fillRect(x, y, width, height, QColor(60, 40, 40))
            painter.setPen(QPen(QColor(150, 100, 100)))
            painter.drawRect(x, y, width, height)
            painter.drawText(x + 5, y + height // 2, "Unsafe path")
            return

    if not gif_path or not os.path.exists(gif_path):
        # Draw placeholder
        painter.fillRect(x, y, width, height, QColor(40, 40, 60))
        painter.setPen(QPen(QColor(100, 100, 120)))
        painter.drawRect(x, y, width, height)
        painter.drawText(x + 5, y + height // 2, "No GIF")
        return

    gif_data = get_gif_data(gif_path)

    if not gif_data or not gif_data.loaded:
        # Draw error placeholder
        painter.fillRect(x, y, width, height, QColor(60, 40, 40))
        painter.setPen(QPen(QColor(150, 100, 100)))
        painter.drawRect(x, y, width, height)
        error = gif_data.error if gif_data else "Load error"
        painter.drawText(x + 5, y + height // 2, error[:20])
        return

    # Get current frame
    frame_idx = get_current_frame_index(element, gif_data)
    frame = gif_data.frames[frame_idx]

    # Scale frame to element size
    scaled_frame = get_scaled_frame(frame, element.width, element.height, scale_mode)

    # Scale for preview
    if scale != 1.0:
        preview_width = int(element.width * scale)
        preview_height = int(element.height * scale)
        scaled_frame = scaled_frame.resize((preview_width, preview_height), PILImage.Resampling.BILINEAR)

    # Convert PIL to QPixmap
    data = scaled_frame.tobytes("raw", "RGBA")
    qimage = QImage(data, scaled_frame.width, scaled_frame.height,
                    scaled_frame.width * 4, QImage.Format.Format_RGBA8888)
    pixmap = QPixmap.fromImage(qimage)

    painter.drawPixmap(x, y, pixmap)


def render_image(draw, img, element):
    """Render the GIF using PIL for the actual display."""
    x, y = element.x, element.y
    width, height = element.width, element.height

    gif_path = getattr(element, 'gif_path', '')
    scale_mode = getattr(element, 'scale_mode', 'fit')
    opacity = getattr(element, 'color_opacity', 100)

    # Validate path is safe before loading
    if gif_path:
        safe, _, err = is_safe_path(gif_path, allow_absolute=True)
        if not safe:
            print(f"GIF unsafe path blocked: {gif_path} - {err}")
            return

    if not gif_path or not os.path.exists(gif_path):
        return

    gif_data = get_gif_data(gif_path)

    if not gif_data or not gif_data.loaded:
        return

    # Get current frame
    frame_idx = get_current_frame_index(element, gif_data)
    frame = gif_data.frames[frame_idx]

    # Scale frame to element size
    scaled_frame = get_scaled_frame(frame, width, height, scale_mode)

    # Apply opacity if needed
    if opacity < 100:
        alpha = scaled_frame.split()[3]
        alpha = alpha.point(lambda x: int(x * opacity / 100))
        scaled_frame.putalpha(alpha)

    # Composite onto main image
    if img.mode == 'RGBA':
        # Create a temporary image for compositing
        temp = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
        temp.paste(scaled_frame, (x, y), scaled_frame)
        img.alpha_composite(temp)
    else:
        # Convert to RGBA for compositing
        img_rgba = img.convert('RGBA')
        temp = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
        temp.paste(scaled_frame, (x, y), scaled_frame)
        result = PILImage.alpha_composite(img_rgba, temp)
        img.paste(result.convert('RGB'))


def clear_cache():
    """Clear the GIF cache to free memory."""
    global _gif_cache, _playback_state
    _gif_cache = {}
    _playback_state = {}
