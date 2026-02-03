"""
Video Background Manager

Handles video playback for theme backgrounds using OpenCV.
Supports fit-to-height and fit-to-width scaling modes.
Pre-buffers all frames in memory for smooth playback.
"""

import os
import time
import threading
from PIL import Image

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None

from constants import DISPLAY_WIDTH, DISPLAY_HEIGHT


class VideoBackground:
    """Manages video background playback with frame buffering."""

    FIT_HEIGHT = "fit_height"
    FIT_WIDTH = "fit_width"

    def __init__(self):
        self.video_path = ""
        self.fit_mode = self.FIT_HEIGHT
        self.enabled = False

        # Video metadata
        self._frame_count = 0
        self._fps = 30
        self._video_width = 0
        self._video_height = 0

        # Frame buffer - stores pre-scaled numpy arrays (RGB)
        self._frame_buffer = []
        self._buffer_ready = False
        self._loading = False
        self._load_progress = 0
        self._load_error = None

        # Playback state
        self._current_frame_idx = 0
        self._last_frame_time = 0

        # Cached converted frames for current frame
        self._cached_pil = None
        self._cached_pixmap = None
        self._cached_frame_idx = -1

        # Threading
        self._lock = threading.Lock()
        self._load_thread = None
        self._stop_loading = False

    def load_video(self, path, callback=None):
        """
        Load a video file and buffer all frames.

        Args:
            path: Path to video file
            callback: Optional callback(progress, done, error) for progress updates

        Returns:
            True if loading started successfully
        """
        if not HAS_CV2:
            if callback:
                callback(0, True, "OpenCV not installed")
            return False

        if not path or not os.path.exists(path):
            if callback:
                callback(0, True, "File not found")
            return False

        # Stop any existing load
        self._stop_loading = True
        if self._load_thread and self._load_thread.is_alive():
            self._load_thread.join(timeout=1.0)

        # Reset state
        with self._lock:
            self._frame_buffer = []
            self._buffer_ready = False
            self._loading = True
            self._load_progress = 0
            self._load_error = None
            self._stop_loading = False
            self._current_frame_idx = 0
            self._cached_pil = None
            self._cached_pixmap = None
            self._cached_frame_idx = -1

        # Start loading in background thread
        self._load_thread = threading.Thread(
            target=self._load_video_thread,
            args=(path, callback),
            daemon=True
        )
        self._load_thread.start()

        self.video_path = path
        self.enabled = True
        return True

    def _load_video_thread(self, path, callback):
        """Background thread to load and buffer video frames."""
        try:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                with self._lock:
                    self._loading = False
                    self._load_error = "Failed to open video"
                if callback:
                    callback(0, True, "Failed to open video")
                return

            # Get video info
            self._frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._fps = cap.get(cv2.CAP_PROP_FPS) or 30
            self._video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Calculate target dimensions
            new_width, new_height, x_offset, y_offset = self._calculate_dimensions()

            frames = []
            frame_idx = 0

            while True:
                if self._stop_loading:
                    cap.release()
                    return

                ret, frame = cap.read()
                if not ret:
                    break

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Resize frame to target size
                frame_resized = cv2.resize(
                    frame_rgb,
                    (new_width, new_height),
                    interpolation=cv2.INTER_LINEAR
                )

                # Create output frame with black background
                output = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)

                # Calculate paste region (handle negative offsets for fit_width)
                y_start = max(0, y_offset)
                y_end = min(DISPLAY_HEIGHT, y_offset + new_height)
                x_start = max(0, x_offset)
                x_end = min(DISPLAY_WIDTH, x_offset + new_width)

                # Source region from resized frame
                src_y_start = max(0, -y_offset)
                src_y_end = src_y_start + (y_end - y_start)
                src_x_start = max(0, -x_offset)
                src_x_end = src_x_start + (x_end - x_start)

                output[y_start:y_end, x_start:x_end] = frame_resized[src_y_start:src_y_end, src_x_start:src_x_end]

                frames.append(output)
                frame_idx += 1

                # Update progress
                progress = frame_idx / max(1, self._frame_count)
                with self._lock:
                    self._load_progress = progress

                if callback:
                    callback(progress, False, None)

            cap.release()

            # Store buffered frames
            with self._lock:
                self._frame_buffer = frames
                self._frame_count = len(frames)
                self._buffer_ready = True
                self._loading = False
                self._load_progress = 1.0

            if callback:
                callback(1.0, True, None)

        except Exception as e:
            with self._lock:
                self._loading = False
                self._load_error = str(e)
            if callback:
                callback(0, True, str(e))

    def _calculate_dimensions(self):
        """Calculate the scaled dimensions based on fit mode."""
        if self._video_width == 0 or self._video_height == 0:
            return DISPLAY_WIDTH, DISPLAY_HEIGHT, 0, 0

        aspect_ratio = self._video_width / self._video_height

        if self.fit_mode == self.FIT_HEIGHT:
            # Scale so video height matches display height
            new_height = DISPLAY_HEIGHT
            new_width = int(new_height * aspect_ratio)
            # Center horizontally
            x_offset = (DISPLAY_WIDTH - new_width) // 2
            y_offset = 0
        else:  # FIT_WIDTH
            # Scale so video width matches display width
            new_width = DISPLAY_WIDTH
            new_height = int(new_width / aspect_ratio)
            # Center vertically
            x_offset = 0
            y_offset = (DISPLAY_HEIGHT - new_height) // 2

        return new_width, new_height, x_offset, y_offset

    def clear_video(self):
        """Clear the current video and free memory."""
        self._stop_loading = True
        if self._load_thread and self._load_thread.is_alive():
            self._load_thread.join(timeout=1.0)

        with self._lock:
            self._frame_buffer = []
            self._buffer_ready = False
            self._loading = False
            self._current_frame_idx = 0
            self._cached_pil = None
            self._cached_pixmap = None
            self._cached_frame_idx = -1

        self.video_path = ""
        self.enabled = False

    def set_fit_mode(self, mode):
        """Set the fit mode and reload if needed."""
        if mode in [self.FIT_HEIGHT, self.FIT_WIDTH] and mode != self.fit_mode:
            old_mode = self.fit_mode
            self.fit_mode = mode

            # Reload video with new fit mode if we have a video loaded
            if self.video_path and self._buffer_ready:
                self.load_video(self.video_path)

    def reset_timing(self):
        """Reset playback timing after system wake or other timing disruption."""
        with self._lock:
            self._last_frame_time = time.time()
            # Don't reset frame index - continue from where we were
            # Invalidate caches
            self._cached_pil = None
            self._cached_pixmap = None
            self._cached_frame_idx = -1

    def _advance_frame(self):
        """Advance to next frame based on elapsed time."""
        if not self._buffer_ready or self._frame_count == 0:
            return

        current_time = time.time()
        frame_duration = 1.0 / self._fps

        if current_time - self._last_frame_time >= frame_duration:
            self._current_frame_idx = (self._current_frame_idx + 1) % self._frame_count
            self._last_frame_time = current_time

    def get_frame_pil(self):
        """Get the current frame as a PIL Image."""
        if not self.enabled:
            return None

        with self._lock:
            if not self._buffer_ready or not self._frame_buffer:
                return None

            self._advance_frame()

            # Return cached if same frame
            if self._cached_frame_idx == self._current_frame_idx and self._cached_pil is not None:
                return self._cached_pil

            # Convert numpy array to PIL
            frame = self._frame_buffer[self._current_frame_idx]
            pil_image = Image.fromarray(frame)

            self._cached_pil = pil_image
            self._cached_frame_idx = self._current_frame_idx
            self._cached_pixmap = None  # Invalidate pixmap cache

            return pil_image

    def get_frame_qpixmap(self, scale=1.0):
        """Get the current frame as a QPixmap for Qt rendering."""
        from PySide6.QtGui import QPixmap, QImage

        if not self.enabled:
            return None

        with self._lock:
            if not self._buffer_ready or not self._frame_buffer:
                # Show loading indicator
                if self._loading:
                    return self._create_loading_pixmap(scale)
                return None

            self._advance_frame()

            # Return cached if same frame and same scale
            if (self._cached_frame_idx == self._current_frame_idx and
                self._cached_pixmap is not None):
                return self._cached_pixmap

            # Get frame data
            frame = self._frame_buffer[self._current_frame_idx]

            # Scale if needed
            if scale != 1.0:
                scaled_width = int(DISPLAY_WIDTH * scale)
                scaled_height = int(DISPLAY_HEIGHT * scale)
                frame = cv2.resize(frame, (scaled_width, scaled_height), interpolation=cv2.INTER_LINEAR)

            height, width, channels = frame.shape
            bytes_per_line = channels * width

            # Convert to QImage then QPixmap
            qimage = QImage(
                frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qimage)

            self._cached_pixmap = pixmap
            self._cached_frame_idx = self._current_frame_idx
            self._cached_pil = None  # Invalidate PIL cache

            return pixmap

    def _create_loading_pixmap(self, scale):
        """Create a loading indicator pixmap."""
        from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
        from PySide6.QtCore import Qt

        width = int(DISPLAY_WIDTH * scale)
        height = int(DISPLAY_HEIGHT * scale)

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(15, 15, 25))

        painter = QPainter(pixmap)
        painter.setPen(QColor(100, 100, 120))

        font = QFont("Arial", 12)
        painter.setFont(font)

        progress_pct = int(self._load_progress * 100)
        text = f"Loading video... {progress_pct}%"

        rect = pixmap.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        # Draw progress bar
        bar_width = int(width * 0.6)
        bar_height = 8
        bar_x = (width - bar_width) // 2
        bar_y = height // 2 + 20

        painter.drawRect(bar_x, bar_y, bar_width, bar_height)
        painter.fillRect(bar_x + 1, bar_y + 1, int((bar_width - 2) * self._load_progress), bar_height - 2, QColor(0, 150, 255))

        painter.end()
        return pixmap

    @property
    def is_loading(self):
        """Check if video is currently loading."""
        return self._loading

    @property
    def load_progress(self):
        """Get loading progress (0.0 to 1.0)."""
        return self._load_progress

    @property
    def frame_count(self):
        """Get total frame count."""
        return self._frame_count

    @property
    def fps(self):
        """Get video FPS."""
        return self._fps

    @property
    def memory_usage_mb(self):
        """Estimate memory usage in MB."""
        if not self._frame_buffer:
            return 0
        # Each frame is DISPLAY_WIDTH x DISPLAY_HEIGHT x 3 bytes
        frame_size = DISPLAY_WIDTH * DISPLAY_HEIGHT * 3
        return (len(self._frame_buffer) * frame_size) / (1024 * 1024)

    def to_dict(self):
        """Serialize video background settings."""
        return {
            "video_path": self.video_path,
            "fit_mode": self.fit_mode,
            "enabled": self.enabled
        }

    def from_dict(self, data):
        """Load video background settings from dict."""
        self.fit_mode = data.get("fit_mode", self.FIT_HEIGHT)
        path = data.get("video_path", "")
        if path and data.get("enabled", False):
            self.load_video(path)
        else:
            self.clear_video()

    def close(self):
        """Release all resources."""
        self.clear_video()


# Global instance
video_background = VideoBackground()
