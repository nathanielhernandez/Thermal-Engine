"""
CanvasPreview - Visual preview and editing widget.
"""

import os
import time

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPixmap, QImage

from constants import DISPLAY_WIDTH, DISPLAY_HEIGHT, PREVIEW_SCALE, SOURCE_UNITS
from elements import get_custom_element
from video_background import video_background


def apply_opacity(color, opacity):
    """Apply opacity (0-100) to a QColor and return the modified color."""
    if isinstance(color, str):
        color = QColor(color)
    else:
        color = QColor(color)  # Make a copy
    alpha = int(255 * opacity / 100)
    color.setAlpha(alpha)
    return color


def get_text_color(element):
    """Get the effective text color for an element, with opacity applied."""
    if getattr(element, 'use_custom_text_color', False):
        color = getattr(element, 'text_color', element.color)
        opacity = getattr(element, 'text_color_opacity', 100)
    else:
        color = element.color
        opacity = getattr(element, 'color_opacity', 100)
    return apply_opacity(color, opacity)


def interpolate_gradient_color(gradient_stops, position):
    """Interpolate color from gradient stops at a given position (0-1)."""
    if not gradient_stops:
        return QColor("#00ff96")

    sorted_stops = sorted(gradient_stops)

    # Clamp position
    position = max(0.0, min(1.0, position))

    # Find surrounding stops
    if position <= sorted_stops[0][0]:
        return QColor(sorted_stops[0][1])
    if position >= sorted_stops[-1][0]:
        return QColor(sorted_stops[-1][1])

    for i in range(len(sorted_stops) - 1):
        p1, c1 = sorted_stops[i]
        p2, c2 = sorted_stops[i + 1]
        if p1 <= position <= p2:
            # Interpolate between these two stops
            t = (position - p1) / (p2 - p1) if p2 != p1 else 0
            color1 = QColor(c1)
            color2 = QColor(c2)
            r = int(color1.red() + t * (color2.red() - color1.red()))
            g = int(color1.green() + t * (color2.green() - color1.green()))
            b = int(color1.blue() + t * (color2.blue() - color1.blue()))
            return QColor(r, g, b)

    return QColor(sorted_stops[-1][1])


def get_value_with_unit(value, source, temp_hide_unit=False):
    """Format a value with its appropriate unit symbol."""
    unit_info = SOURCE_UNITS.get(source, {"symbol": "%", "type": "percent"})
    symbol = unit_info["symbol"]
    unit_type = unit_info["type"]

    if unit_type == "clock":
        return f"{value:.0f}{symbol}"
    elif unit_type == "temp":
        if temp_hide_unit:
            return f"{value:.0f}°"
        return f"{value:.0f}{symbol}"
    elif unit_type == "power":
        return f"{value:.0f}{symbol}"
    elif unit_type == "size":
        return f"{value:.1f}{symbol}"
    elif unit_type == "speed":
        return f"{value:.1f}{symbol}"
    else:  # percent
        return f"{value:.0f}{symbol}"


class CanvasPreview(QWidget):
    element_selected = Signal(int)  # Single selection (for backwards compat)
    elements_selected = Signal(list)  # Multi-selection
    element_moved = Signal(int, int, int)
    element_resized = Signal(int)  # Emitted when element is resized
    drag_started = Signal()  # Emitted when drag/resize starts (for undo)

    # Resize handle positions
    HANDLE_NONE = 0
    HANDLE_TL = 1  # Top-left
    HANDLE_TR = 2  # Top-right
    HANDLE_BL = 3  # Bottom-left
    HANDLE_BR = 4  # Bottom-right

    def __init__(self):
        super().__init__()
        self.elements = []
        self.selected_indices = []  # Support multiple selection
        self.dragging = False
        self.resizing = False
        self.resize_handle = self.HANDLE_NONE
        self.drag_offset = QPointF(0, 0)
        self.drag_start_positions = {}  # Store start positions for multi-drag
        self.resize_start_pos = QPointF(0, 0)
        self.resize_start_pos_element = (0, 0)
        self.resize_start_size = (0, 0)
        self.resize_start_bounds = None  # For multi-element resize
        self.scale = PREVIEW_SCALE
        self.background_color = QColor(15, 15, 25)
        self.handle_size = 10
        self.group_selection_mode = False  # True when a complete group is selected
        self._glass_background = None  # Cached background for glass effect
        self._glass_cache_valid = False  # Track if glass cache needs rebuild
        self._has_glass_cache = None  # Cache result of _has_glass_elements()
        self._animated_values = {}  # Track display values for animated gauges {element_name: current_display_value}

        self.setFixedSize(
            int(DISPLAY_WIDTH * self.scale),
            int(DISPLAY_HEIGHT * self.scale)
        )
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Enable keyboard input

    def set_elements(self, elements):
        self.elements = elements
        self._glass_cache_valid = False  # Invalidate glass cache when elements change
        self._has_glass_cache = None  # Clear has_glass cache
        self.update()

    def get_animated_value(self, element):
        """Get the display value for a gauge, handling animation if enabled."""
        target_value = float(element.value)

        if not getattr(element, 'animate_gauge', False):
            return target_value

        # Use element name as key for tracking
        key = element.name

        if key not in self._animated_values:
            # Initialize with current value
            self._animated_values[key] = target_value
            return target_value

        current = self._animated_values[key]
        diff = target_value - current

        # Pixel-perfect threshold - stop when difference is negligible
        if abs(diff) < 0.001:
            self._animated_values[key] = target_value
            return target_value

        # Ultra-smooth animation using ease-out cubic
        # This creates natural deceleration as it approaches target
        speed = getattr(element, 'animation_speed', 0.05)

        # Ease-out: faster at start, slower near end (feels more natural)
        # The further from target, the bigger the step
        t = min(1.0, abs(diff) / 50.0)  # Normalize distance (50% gauge = full speed)
        eased_speed = speed * (1.0 + t * 2.0)  # Speed up for large changes

        step = diff * eased_speed

        # Minimum step for pixel-by-pixel movement (prevents stalling)
        min_step = 0.05
        if abs(step) < min_step and abs(diff) >= 0.001:
            step = min_step if diff > 0 else -min_step

        new_value = current + step
        self._animated_values[key] = new_value
        return new_value

    def set_selected(self, index):
        """Set single selection (backwards compatible)."""
        if index >= 0:
            self.selected_indices = [index]
        else:
            self.selected_indices = []
        self.group_selection_mode = False  # Single selection is never a group selection
        self.update()

    def set_selected_indices(self, indices, group_selection=False):
        """Set multiple selected indices.

        Args:
            indices: List of element indices to select
            group_selection: True if this selection represents a complete group
                             (from clicking on group in tree, not individual elements)
        """
        self.selected_indices = list(indices)
        self.group_selection_mode = group_selection
        self.update()

    def get_selected_index(self):
        """Get single selected index (backwards compatible)."""
        return self.selected_indices[0] if len(self.selected_indices) == 1 else -1

    def set_background_color(self, color):
        self.background_color = QColor(color)
        self._glass_cache_valid = False  # Invalidate glass cache
        self.update()

    def _has_glass_elements(self):
        """Check if any element has glass effect enabled (cached)."""
        if self._has_glass_cache is None:
            self._has_glass_cache = any(
                el.type == "rectangle" and getattr(el, 'glass_effect', False)
                for el in self.elements
            )
        return self._has_glass_cache

    def _render_background_for_glass(self):
        """Render everything except glass effects to a buffer for blur source."""
        buffer = QPixmap(self.size())
        buffer.fill(Qt.GlobalColor.transparent)

        painter = QPainter(buffer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw video background if enabled, otherwise solid color
        if video_background.enabled:
            pixmap = video_background.get_frame_qpixmap(self.scale)
            if pixmap:
                painter.drawPixmap(0, 0, pixmap)
            else:
                painter.fillRect(self.rect(), self.background_color)
        else:
            painter.fillRect(self.rect(), self.background_color)

        # Draw elements without glass effect and without selection boxes
        for i in range(len(self.elements) - 1, -1, -1):
            element = self.elements[i]
            # Skip glass rectangles - they'll use this buffer
            if element.type == "rectangle" and getattr(element, 'glass_effect', False):
                continue
            self.draw_element(painter, element, False)

        painter.end()
        return buffer

    def paintEvent(self, event):
        # If we have glass elements, pre-render the background for blur
        # Only rebuild if cache is invalid or video is playing (video changes every frame)
        if self._has_glass_elements():
            needs_rebuild = not self._glass_cache_valid or video_background.enabled
            if needs_rebuild or self._glass_background is None:
                self._glass_background = self._render_background_for_glass()
                self._glass_cache_valid = True
        else:
            self._glass_background = None

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw video background if enabled, otherwise solid color
        if video_background.enabled:
            pixmap = video_background.get_frame_qpixmap(self.scale)
            if pixmap:
                painter.drawPixmap(0, 0, pixmap)
            else:
                painter.fillRect(self.rect(), self.background_color)
        else:
            painter.fillRect(self.rect(), self.background_color)

        painter.setPen(QPen(QColor(60, 60, 80), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        # Draw elements in reverse: last in list drawn first (back), first in list drawn last (front)
        # Tree shows first element at top, so top of tree = front of display
        for i in range(len(self.elements) - 1, -1, -1):
            # In group selection mode, don't draw individual selection boxes
            # (we'll draw only the combined box instead)
            is_selected = i in self.selected_indices
            draw_individual_selection = is_selected and not self.group_selection_mode
            self.draw_element(painter, self.elements[i], draw_individual_selection)

        # Draw combined selection box if multiple elements selected (always for groups,
        # or for multi-select of individual elements)
        if len(self.selected_indices) > 1:
            self.draw_multi_selection_box(painter)

        painter.end()

    def draw_element(self, painter, element, selected):
        x = int(element.x * self.scale)
        y = int(element.y * self.scale)

        # Only apply clipping for text/clock elements that have clip enabled
        needs_clip = element.clip and element.type in ["text", "clock"]
        if needs_clip:
            clip_rect = QRectF(x, y, element.width * self.scale, element.height * self.scale)
            painter.setClipRect(clip_rect)

        if element.type == "circle_gauge":
            self.draw_circle_gauge(painter, element, x, y, selected)
        elif element.type == "bar_gauge":
            self.draw_bar_gauge(painter, element, x, y, selected)
        elif element.type == "text":
            self.draw_text(painter, element, x, y, selected)
        elif element.type == "rectangle":
            self.draw_rectangle(painter, element, x, y, selected)
        elif element.type == "clock":
            self.draw_clock(painter, element, x, y, selected)
        elif element.type == "analog_clock":
            self.draw_analog_clock(painter, element, x, y, selected)
        elif element.type == "image":
            self.draw_image(painter, element, x, y, selected)
        else:
            # Try custom element
            custom = get_custom_element(element.type)
            if custom and custom.get('draw_preview'):
                try:
                    custom['draw_preview'](painter, element, x, y, self.scale)
                except Exception as e:
                    print(f"Custom element draw error: {e}")

        if needs_clip:
            painter.setClipping(False)

        if selected:
            self.draw_selection_box(painter, element, x, y)

    def draw_circle_gauge(self, painter, element, x, y, selected):
        radius = int(element.radius * self.scale)
        color = apply_opacity(element.color, getattr(element, 'color_opacity', 100))
        bg_color = apply_opacity(element.background_color, getattr(element, 'background_color_opacity', 100))

        # Get animated display value
        display_value = self.get_animated_value(element)

        painter.setPen(QPen(bg_color, int(15 * self.scale)))
        painter.drawArc(
            x - radius, y - radius, radius * 2, radius * 2,
            225 * 16, -270 * 16
        )

        use_gradient = getattr(element, 'gradient_fill', False)
        sweep = int(-270 * (display_value / 100) * 16)

        if use_gradient and display_value > 0:
            # Draw gradient arc using multiple small segments
            from PySide6.QtGui import QColor as QC
            gradient_stops = getattr(element, 'gradient_stops', [(0.0, "#00ff96"), (1.0, "#ff4444")])
            pen_width = int(15 * self.scale)
            # Draw in small increments for smooth gradient
            num_segments = max(1, int(display_value * 2.7))  # ~2.7 segments per percent (270 degrees / 100)
            for i in range(num_segments):
                t = i / (270.0)  # Position along full arc range (0 to 1 for full 270 degrees)
                segment_color = interpolate_gradient_color(gradient_stops, t)
                painter.setPen(QPen(QC(segment_color), pen_width))
                segment_start = 225 * 16 - int(i * 16)
                segment_sweep = -16  # 1 degree at a time
                painter.drawArc(
                    x - radius, y - radius, radius * 2, radius * 2,
                    segment_start, segment_sweep
                )
        else:
            fill_color = color
            painter.setPen(QPen(fill_color, int(15 * self.scale)))
            painter.drawArc(
                x - radius, y - radius, radius * 2, radius * 2,
                225 * 16, sweep
            )

        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont(element.font_family)
        font.setPixelSize(int(element.font_size * self.scale * 0.8))
        font.setBold(element.font_bold)
        font.setItalic(element.font_italic)
        painter.setFont(font)

        text = get_value_with_unit(display_value, element.source, getattr(element, 'temp_hide_unit', False))
        text_rect = QRectF(x - radius, y - radius / 2, radius * 2, radius)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        font.setPixelSize(int(element.font_size * self.scale * 0.5))
        painter.setFont(font)
        painter.setPen(QPen(get_text_color(element)))
        label_rect = QRectF(x - radius, y + radius / 4, radius * 2, radius / 2)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, element.text)

    def draw_bar_gauge(self, painter, element, x, y, selected):
        from PySide6.QtGui import QPainterPath, QLinearGradient

        width = int(element.width * self.scale)
        height = int(element.height * self.scale)
        color = apply_opacity(element.color, getattr(element, 'color_opacity', 100))
        bg_color = apply_opacity(element.background_color, getattr(element, 'background_color_opacity', 100))

        # Get animated display value
        display_value = self.get_animated_value(element)

        rounded = getattr(element, 'rounded_corners', False)
        use_gradient = getattr(element, 'gradient_fill', False)
        corner_radius = height // 2 if rounded else 0

        # Draw background
        if rounded:
            bg_path = QPainterPath()
            bg_path.addRoundedRect(x, y, width, height, corner_radius, corner_radius)
            painter.fillPath(bg_path, bg_color)
        else:
            painter.fillRect(x, y, width, height, bg_color)

        # Draw fill
        fill_width = int(width * display_value / 100)
        if fill_width > 0:
            if use_gradient:
                # Use horizontal gradient with custom stops
                gradient_stops = getattr(element, 'gradient_stops', [(0.0, "#00ff96"), (1.0, "#ff4444")])
                grad = QLinearGradient(x, y, x + width, y)
                for pos, stop_color in gradient_stops:
                    grad.setColorAt(pos, QColor(stop_color))
                fill_brush = QBrush(grad)
            else:
                fill_brush = QBrush(color)

            if rounded:
                fill_path = QPainterPath()
                fill_path.addRoundedRect(x, y, fill_width, height, corner_radius, corner_radius)
                painter.fillPath(fill_path, fill_brush)
            else:
                painter.fillRect(x, y, fill_width, height, fill_brush)

        # Draw text based on bar_text_mode and bar_text_position
        bar_text_mode = getattr(element, 'bar_text_mode', 'full')
        bar_text_position = getattr(element, 'bar_text_position', 'inside')

        if bar_text_mode != 'none':
            painter.setPen(QPen(get_text_color(element)))
            font = QFont(element.font_family)
            font.setPixelSize(int(element.font_size * self.scale * 0.6))
            font.setBold(element.font_bold)
            font.setItalic(element.font_italic)
            painter.setFont(font)

            value_text = get_value_with_unit(display_value, element.source, getattr(element, 'temp_hide_unit', False))
            if bar_text_mode == 'full':
                display_text = f"{element.text}: {value_text}"
            else:  # value_only
                display_text = value_text

            if bar_text_position == 'inside':
                text_rect = QRectF(x, y, width, height)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, display_text)
            else:  # left
                metrics = painter.fontMetrics()
                text_width = metrics.horizontalAdvance(display_text)
                text_x = x - text_width - 10 * self.scale  # 10px spacing
                text_y = y + (height + metrics.ascent() - metrics.descent()) / 2
                painter.drawText(int(text_x), int(text_y), display_text)

    def draw_text(self, painter, element, x, y, selected):
        color = apply_opacity(element.color, getattr(element, 'color_opacity', 100))

        painter.setPen(QPen(color))
        font = QFont(element.font_family)
        font.setPixelSize(int(element.font_size * self.scale))
        font.setBold(element.font_bold)
        font.setItalic(element.font_italic)
        painter.setFont(font)

        # Determine text to display based on source
        source = getattr(element, 'source', 'static')
        if source and source != 'static':
            # Display sensor value, optionally with label
            value_text = get_value_with_unit(element.value, source, getattr(element, 'temp_hide_unit', False))
            if element.text:
                text = f"{element.text}: {value_text}"
            else:
                text = value_text
        else:
            text = element.text

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        width = int(element.width * self.scale)
        height = int(element.height * self.scale)

        if element.text_align == "left":
            draw_x = x
        elif element.text_align == "right":
            draw_x = x + width - text_width
        else:
            draw_x = x + (width - text_width) // 2

        draw_y = y + (height + text_height) // 2 - metrics.descent()

        painter.drawText(draw_x, draw_y, text)

    def draw_rectangle(self, painter, element, x, y, selected):
        width = int(element.width * self.scale)
        height = int(element.height * self.scale)
        color = apply_opacity(element.color, getattr(element, 'color_opacity', 100))
        border_radius = int(getattr(element, 'border_radius', 0) * self.scale)
        glass_effect = getattr(element, 'glass_effect', False)

        if glass_effect:
            self.draw_glass_rectangle(painter, element, x, y, width, height, border_radius, color)
        elif border_radius > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(x, y, width, height, border_radius, border_radius)
        else:
            painter.fillRect(x, y, width, height, color)

    def draw_glass_rectangle(self, painter, element, x, y, width, height, border_radius, color):
        """Draw a frosted glass effect rectangle using pre-rendered background."""
        from PySide6.QtGui import QPainterPath

        glass_blur = getattr(element, 'glass_blur', 10)
        glass_opacity = getattr(element, 'glass_opacity', 50)

        # Use the pre-rendered background (no recursive grab needed)
        if self._glass_background is not None and width > 0 and height > 0:
            # Extract the region we need to blur
            region = self._glass_background.copy(x, y, width, height)

            # Apply blur by downscaling and upscaling (fast box blur approximation)
            blur_amount = max(2, glass_blur // 2)
            small = region.scaled(
                max(1, width // blur_amount),
                max(1, height // blur_amount),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            blurred = small.scaled(
                width, height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            # Draw the blurred background
            if border_radius > 0:
                path = QPainterPath()
                path.addRoundedRect(x, y, width, height, border_radius, border_radius)
                painter.setClipPath(path)
                painter.drawPixmap(x, y, blurred)
                painter.setClipping(False)
            else:
                painter.drawPixmap(x, y, blurred)

        # Draw semi-transparent tinted overlay
        tint_color = QColor(color)
        tint_color.setAlpha(int(255 * glass_opacity / 100))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(tint_color))

        if border_radius > 0:
            painter.drawRoundedRect(x, y, width, height, border_radius, border_radius)
        else:
            painter.fillRect(x, y, width, height, tint_color)

        # Draw subtle border for glass effect
        border_color = QColor(255, 255, 255, 40)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if border_radius > 0:
            painter.drawRoundedRect(x, y, width, height, border_radius, border_radius)
        else:
            painter.drawRect(x, y, width, height)

    def draw_clock(self, painter, element, x, y, selected):
        color = apply_opacity(element.color, getattr(element, 'color_opacity', 100))

        painter.setPen(QPen(color))
        font = QFont(element.font_family)
        font.setPixelSize(int(element.font_size * self.scale))
        font.setBold(element.font_bold)
        font.setItalic(element.font_italic)
        painter.setFont(font)

        # Build time format string based on element settings
        time_format = getattr(element, 'time_format', '24h')
        show_seconds = getattr(element, 'show_seconds', True)
        show_am_pm = getattr(element, 'show_am_pm', True)
        show_leading_zero = getattr(element, 'show_leading_zero', True)

        if time_format == '12h':
            fmt = "%I:%M:%S" if show_seconds else "%I:%M"
            if show_am_pm:
                fmt += " %p"
        else:  # 24h
            fmt = "%H:%M:%S" if show_seconds else "%H:%M"

        current_time = time.strftime(fmt)

        # Remove leading zero from hour if disabled
        if not show_leading_zero and current_time[0] == '0':
            current_time = current_time[1:]

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(current_time)
        text_height = metrics.height()

        width = int(element.width * self.scale)
        height = int(element.height * self.scale)

        if element.text_align == "left":
            draw_x = x
        elif element.text_align == "right":
            draw_x = x + width - text_width
        else:
            draw_x = x + (width - text_width) // 2

        draw_y = y + (height + text_height) // 2 - metrics.descent()

        painter.drawText(draw_x, draw_y, current_time)

    def draw_analog_clock(self, painter, element, x, y, selected):
        import math
        import datetime

        radius = int(element.radius * self.scale)
        color = apply_opacity(element.color, getattr(element, 'color_opacity', 100))
        bg_color = apply_opacity(element.background_color, getattr(element, 'background_color_opacity', 100))

        # Get options
        show_seconds = getattr(element, 'show_seconds_hand', True)
        show_border = getattr(element, 'show_clock_border', True)
        face_style = getattr(element, 'clock_face_style', 'numbers')
        smooth = getattr(element, 'smooth_animation', True)

        # Get current time with milliseconds for smooth animation
        now = datetime.datetime.now()
        hours = now.hour % 12
        minutes = now.minute
        seconds = now.second
        microseconds = now.microsecond

        if smooth:
            # Smooth movement - include fractional parts
            second_angle = (seconds + microseconds / 1000000) * 6  # 360/60 = 6 degrees per second
            minute_angle = (minutes + seconds / 60) * 6  # 6 degrees per minute
            hour_angle = (hours + minutes / 60) * 30  # 30 degrees per hour
        else:
            # Tick movement - discrete steps
            second_angle = seconds * 6
            minute_angle = minutes * 6
            hour_angle = hours * 30 + minutes * 0.5  # Still smooth hour hand

        # Draw clock face background
        painter.setBrush(QBrush(bg_color))
        if show_border:
            painter.setPen(QPen(color, 2 * self.scale))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)

        # Draw tick marks or numbers
        text_color = get_text_color(element)
        painter.setPen(QPen(text_color, 1 * self.scale))
        font = QFont(getattr(element, 'font_family', 'Arial'))
        font.setPixelSize(int(getattr(element, 'font_size', 14) * self.scale * 0.8))
        painter.setFont(font)

        for i in range(12):
            angle_rad = math.radians(i * 30 - 90)  # Start at 12 o'clock

            if face_style == 'numbers':
                # Draw numbers 1-12
                num = i if i > 0 else 12
                text = str(num)
                metrics = painter.fontMetrics()
                text_width = metrics.horizontalAdvance(text)
                text_height = metrics.height()

                text_radius = radius * 0.78
                tx = x + text_radius * math.cos(angle_rad) - text_width / 2
                ty = y + text_radius * math.sin(angle_rad) + text_height / 4

                painter.drawText(int(tx), int(ty), text)

            elif face_style == 'ticks':
                # Draw tick marks
                inner_radius = radius * 0.85
                outer_radius = radius * 0.95

                # Longer ticks for 12, 3, 6, 9
                if i % 3 == 0:
                    inner_radius = radius * 0.75
                    painter.setPen(QPen(text_color, 2 * self.scale))
                else:
                    painter.setPen(QPen(text_color, 1 * self.scale))

                x1 = x + inner_radius * math.cos(angle_rad)
                y1 = y + inner_radius * math.sin(angle_rad)
                x2 = x + outer_radius * math.cos(angle_rad)
                y2 = y + outer_radius * math.sin(angle_rad)

                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw center dot
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        center_radius = int(4 * self.scale)
        painter.drawEllipse(x - center_radius, y - center_radius, center_radius * 2, center_radius * 2)

        # Draw hour hand (shortest, thickest)
        hour_length = radius * 0.5
        hour_rad = math.radians(hour_angle - 90)
        hx = x + hour_length * math.cos(hour_rad)
        hy = y + hour_length * math.sin(hour_rad)
        painter.setPen(QPen(color, 4 * self.scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(x, y, int(hx), int(hy))

        # Draw minute hand (longer, medium thickness)
        minute_length = radius * 0.7
        minute_rad = math.radians(minute_angle - 90)
        mx = x + minute_length * math.cos(minute_rad)
        my = y + minute_length * math.sin(minute_rad)
        painter.setPen(QPen(color, 3 * self.scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(x, y, int(mx), int(my))

        # Draw second hand (longest, thinnest) - optional
        if show_seconds:
            second_length = radius * 0.85
            second_rad = math.radians(second_angle - 90)
            sx = x + second_length * math.cos(second_rad)
            sy = y + second_length * math.sin(second_rad)
            # Second hand in a slightly different shade (reddish)
            second_color = QColor(255, 80, 80)
            second_color.setAlpha(color.alpha())
            painter.setPen(QPen(second_color, 1.5 * self.scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(x, y, int(sx), int(sy))

    def draw_image(self, painter, element, x, y, selected):
        width = int(element.width * self.scale)
        height = int(element.height * self.scale)

        if element.image_path and os.path.exists(element.image_path):
            pixmap = QPixmap(element.image_path)
            if element.scale_proportionally:
                # Maintain aspect ratio - fit within bounds
                pixmap = pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            else:
                # Stretch to fill exact dimensions
                pixmap = pixmap.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(x, y, pixmap)
        else:
            painter.fillRect(x, y, width, height, QColor(40, 40, 60))
            painter.setPen(QPen(QColor(100, 100, 120)))
            painter.drawRect(x, y, width, height)
            painter.drawText(x + 5, y + height // 2, "No Image")

    def get_element_bounds(self, element):
        """Get the bounding rectangle for an element."""
        x = int(element.x * self.scale)
        y = int(element.y * self.scale)

        if element.type in ["circle_gauge", "analog_clock"]:
            radius = int(element.radius * self.scale)
            return QRectF(x - radius, y - radius, radius * 2, radius * 2)
        elif hasattr(element, 'width') and hasattr(element, 'height') and element.width > 0 and element.height > 0:
            width = int(element.width * self.scale)
            height = int(element.height * self.scale)
            return QRectF(x, y, width, height)
        else:
            return QRectF(x, y, 100, 50)

    def draw_selection_box(self, painter, element, x, y):
        bounds = self.get_element_bounds(element)

        pen = QPen(QColor(0, 150, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(bounds)

        # Draw resize handles at corners
        hs = self.handle_size
        handles = [
            (bounds.left(), bounds.top()),      # TL
            (bounds.right(), bounds.top()),     # TR
            (bounds.left(), bounds.bottom()),   # BL
            (bounds.right(), bounds.bottom()),  # BR
        ]

        painter.setPen(Qt.PenStyle.NoPen)
        for hx, hy in handles:
            painter.setBrush(QBrush(QColor(0, 150, 255)))
            painter.drawRect(int(hx - hs / 2), int(hy - hs / 2), hs, hs)

    def get_multi_selection_bounds(self):
        """Get combined bounding rectangle for all selected elements."""
        if not self.selected_indices:
            return None

        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for idx in self.selected_indices:
            if 0 <= idx < len(self.elements):
                bounds = self.get_element_bounds(self.elements[idx])
                min_x = min(min_x, bounds.left())
                min_y = min(min_y, bounds.top())
                max_x = max(max_x, bounds.right())
                max_y = max(max_y, bounds.bottom())

        if min_x == float('inf'):
            return None

        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def draw_multi_selection_box(self, painter):
        """Draw a combined selection box around all selected elements."""
        bounds = self.get_multi_selection_bounds()
        if bounds is None:
            return

        # Draw outer selection box
        pen = QPen(QColor(0, 150, 255), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(bounds)

        # Draw resize handles at corners
        hs = self.handle_size
        handles = [
            (bounds.left(), bounds.top()),
            (bounds.right(), bounds.top()),
            (bounds.left(), bounds.bottom()),
            (bounds.right(), bounds.bottom()),
        ]

        painter.setPen(Qt.PenStyle.NoPen)
        for hx, hy in handles:
            painter.setBrush(QBrush(QColor(0, 150, 255)))
            painter.drawRect(int(hx - hs / 2), int(hy - hs / 2), hs, hs)

    def get_handle_at(self, pos, element):
        """Check if position is over a resize handle. Returns handle type or HANDLE_NONE."""
        bounds = self.get_element_bounds(element)
        hs = self.handle_size

        handles = {
            self.HANDLE_TL: (bounds.left(), bounds.top()),
            self.HANDLE_TR: (bounds.right(), bounds.top()),
            self.HANDLE_BL: (bounds.left(), bounds.bottom()),
            self.HANDLE_BR: (bounds.right(), bounds.bottom()),
        }

        for handle_type, (hx, hy) in handles.items():
            handle_rect = QRectF(hx - hs, hy - hs, hs * 2, hs * 2)
            if handle_rect.contains(pos):
                return handle_type

        return self.HANDLE_NONE

    def get_element_at(self, pos):
        # Check from index 0 first (top of tree = front of display)
        # This matches rendering order where index 0 is drawn last (on top)
        for i in range(len(self.elements)):
            element = self.elements[i]
            x = element.x * self.scale
            y = element.y * self.scale

            if element.type in ["circle_gauge", "analog_clock"]:
                radius = element.radius * self.scale
                dist = ((pos.x() - x) ** 2 + (pos.y() - y) ** 2) ** 0.5
                if dist <= radius:
                    return i
            elif hasattr(element, 'width') and hasattr(element, 'height') and element.width > 0 and element.height > 0:
                # Any element with width/height properties
                width = element.width * self.scale
                height = element.height * self.scale
                if x <= pos.x() <= x + width and y <= pos.y() <= y + height:
                    return i

        return -1

    def get_multi_handle_at(self, pos):
        """Check if position is over a resize handle for multi-selection."""
        bounds = self.get_multi_selection_bounds()
        if bounds is None:
            return self.HANDLE_NONE

        hs = self.handle_size
        handles = {
            self.HANDLE_TL: (bounds.left(), bounds.top()),
            self.HANDLE_TR: (bounds.right(), bounds.top()),
            self.HANDLE_BL: (bounds.left(), bounds.bottom()),
            self.HANDLE_BR: (bounds.right(), bounds.bottom()),
        }

        for handle_type, (hx, hy) in handles.items():
            handle_rect = QRectF(hx - hs, hy - hs, hs * 2, hs * 2)
            if handle_rect.contains(pos):
                return handle_type

        return self.HANDLE_NONE

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            modifiers = event.modifiers()
            ctrl_held = modifiers & Qt.KeyboardModifier.ControlModifier
            shift_held = modifiers & Qt.KeyboardModifier.ShiftModifier

            # Check if clicking on resize handle of selected element(s)
            # Don't allow resizing if any selected element is locked
            any_locked = any(self.elements[idx].locked for idx in self.selected_indices) if self.selected_indices else False

            if len(self.selected_indices) > 1 and not any_locked:
                # Multi-selection resize handle check
                handle = self.get_multi_handle_at(pos)
                if handle != self.HANDLE_NONE:
                    self.drag_started.emit()
                    self.resizing = True
                    self.resize_handle = handle
                    self.resize_start_pos = pos
                    self.resize_start_bounds = self.get_multi_selection_bounds()
                    # Store original positions and sizes for all selected elements
                    self.resize_start_elements = {}
                    for idx in self.selected_indices:
                        el = self.elements[idx]
                        if el.type in ["circle_gauge", "analog_clock"]:
                            self.resize_start_elements[idx] = (el.x, el.y, el.radius, el.radius)
                        else:
                            self.resize_start_elements[idx] = (el.x, el.y, el.width, el.height)
                    return
            elif len(self.selected_indices) == 1 and not any_locked:
                element = self.elements[self.selected_indices[0]]
                handle = self.get_handle_at(pos, element)
                if handle != self.HANDLE_NONE:
                    self.drag_started.emit()
                    self.resizing = True
                    self.resize_handle = handle
                    self.resize_start_pos = pos
                    self.resize_start_pos_element = (element.x, element.y)
                    if element.type in ["circle_gauge", "analog_clock"]:
                        self.resize_start_size = (element.radius, element.radius)
                    else:
                        self.resize_start_size = (element.width, element.height)
                    return

            # Check if clicking on an element
            index = self.get_element_at(pos)

            if index >= 0:
                clicked_element = self.elements[index]
                clicked_group = getattr(clicked_element, 'group', None)

                if ctrl_held:
                    # Ctrl+click: Toggle selection (respects groups)
                    if clicked_group:
                        # Get all indices in this group
                        group_indices = [i for i, el in enumerate(self.elements) if getattr(el, 'group', None) == clicked_group]
                        # Check if entire group is selected
                        all_selected = all(i in self.selected_indices for i in group_indices)
                        if all_selected:
                            # Deselect entire group
                            for i in group_indices:
                                if i in self.selected_indices:
                                    self.selected_indices.remove(i)
                        else:
                            # Select entire group
                            for i in group_indices:
                                if i not in self.selected_indices:
                                    self.selected_indices.append(i)
                    else:
                        # Ungrouped element - toggle individual
                        if index in self.selected_indices:
                            self.selected_indices.remove(index)
                        else:
                            self.selected_indices.append(index)
                elif shift_held and self.selected_indices:
                    # Shift+click: Range selection
                    last_selected = self.selected_indices[-1]
                    start, end = min(last_selected, index), max(last_selected, index)
                    for i in range(start, end + 1):
                        if i not in self.selected_indices:
                            self.selected_indices.append(i)
                else:
                    # Normal click behavior:
                    # - If element already selected (e.g., via tree), keep current selection for dragging
                    # - If element not selected, select entire group (or just element if ungrouped)
                    if index in self.selected_indices:
                        # Already selected - keep current selection (allows dragging individual from tree selection)
                        pass
                    elif clicked_group:
                        # Not selected, but in a group - select entire group
                        group_indices = [i for i, el in enumerate(self.elements) if getattr(el, 'group', None) == clicked_group]
                        self.selected_indices = group_indices
                        self.group_selection_mode = True
                    else:
                        # Ungrouped element - single selection
                        self.selected_indices = [index]
                        self.group_selection_mode = False

                # Check if any selected element is locked - don't allow dragging
                any_locked = any(self.elements[idx].locked for idx in self.selected_indices)

                # Start dragging (only if not locked)
                if not any_locked:
                    self.drag_started.emit()
                    self.dragging = True
                    # Store start positions for all selected elements
                    self.drag_start_positions = {}
                    for idx in self.selected_indices:
                        el = self.elements[idx]
                        self.drag_start_positions[idx] = (el.x, el.y)
                    self.drag_start_mouse = pos

                # Emit signals
                if len(self.selected_indices) == 1:
                    self.element_selected.emit(self.selected_indices[0])
                else:
                    self.element_selected.emit(-1)  # -1 indicates multi-select
                self.elements_selected.emit(self.selected_indices.copy())
            else:
                # Clicked on empty space
                if not ctrl_held and not shift_held:
                    self.selected_indices = []
                    self.element_selected.emit(-1)
                    self.elements_selected.emit([])

            self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()

        # Handle multi-element resizing
        if self.resizing and len(self.selected_indices) > 1 and self.resize_start_bounds:
            dx = (pos.x() - self.resize_start_pos.x()) / self.scale
            dy = (pos.y() - self.resize_start_pos.y()) / self.scale

            orig_bounds = self.resize_start_bounds
            orig_w = orig_bounds.width() / self.scale
            orig_h = orig_bounds.height() / self.scale

            # Calculate scale factors
            if self.resize_handle in [self.HANDLE_TR, self.HANDLE_BR]:
                scale_x = (orig_w + dx) / orig_w if orig_w > 0 else 1
            elif self.resize_handle in [self.HANDLE_TL, self.HANDLE_BL]:
                scale_x = (orig_w - dx) / orig_w if orig_w > 0 else 1
            else:
                scale_x = 1

            if self.resize_handle in [self.HANDLE_BL, self.HANDLE_BR]:
                scale_y = (orig_h + dy) / orig_h if orig_h > 0 else 1
            elif self.resize_handle in [self.HANDLE_TL, self.HANDLE_TR]:
                scale_y = (orig_h - dy) / orig_h if orig_h > 0 else 1
            else:
                scale_y = 1

            scale_x = max(0.1, scale_x)
            scale_y = max(0.1, scale_y)

            # Apply scale to all selected elements
            anchor_x = orig_bounds.right() / self.scale if self.resize_handle in [self.HANDLE_TL, self.HANDLE_BL] else orig_bounds.left() / self.scale
            anchor_y = orig_bounds.bottom() / self.scale if self.resize_handle in [self.HANDLE_TL, self.HANDLE_TR] else orig_bounds.top() / self.scale

            for idx, (ox, oy, ow, oh) in self.resize_start_elements.items():
                el = self.elements[idx]
                if el.type in ["circle_gauge", "analog_clock"]:
                    new_radius = max(30, int(ow * (scale_x + scale_y) / 2))
                    el.radius = new_radius
                    el.x = int(anchor_x + (ox - anchor_x) * scale_x)
                    el.y = int(anchor_y + (oy - anchor_y) * scale_y)
                else:
                    el.width = max(20, int(ow * scale_x))
                    el.height = max(20, int(oh * scale_y))
                    el.x = int(anchor_x + (ox - anchor_x) * scale_x)
                    el.y = int(anchor_y + (oy - anchor_y) * scale_y)

            self.element_resized.emit(-1)
            self.update()
            return

        # Handle single element resizing
        if self.resizing and len(self.selected_indices) == 1:
            element = self.elements[self.selected_indices[0]]
            dx = (pos.x() - self.resize_start_pos.x()) / self.scale
            dy = (pos.y() - self.resize_start_pos.y()) / self.scale

            if element.type in ["circle_gauge", "analog_clock"]:
                if self.resize_handle in [self.HANDLE_BR, self.HANDLE_TR]:
                    new_radius = max(30, int(self.resize_start_size[0] + (dx + dy) / 2))
                else:
                    new_radius = max(30, int(self.resize_start_size[0] - (dx + dy) / 2))
                element.radius = new_radius
            else:
                new_width, new_height = self.resize_start_size

                if self.resize_handle in [self.HANDLE_TR, self.HANDLE_BR]:
                    new_width = max(20, int(self.resize_start_size[0] + dx))
                elif self.resize_handle in [self.HANDLE_TL, self.HANDLE_BL]:
                    new_width = max(20, int(self.resize_start_size[0] - dx))
                    element.x = int(self.resize_start_pos_element[0] + dx)

                if self.resize_handle in [self.HANDLE_BL, self.HANDLE_BR]:
                    new_height = max(20, int(self.resize_start_size[1] + dy))
                elif self.resize_handle in [self.HANDLE_TL, self.HANDLE_TR]:
                    new_height = max(20, int(self.resize_start_size[1] - dy))
                    element.y = int(self.resize_start_pos_element[1] + dy)

                if element.type == "image" and element.scale_proportionally and element.aspect_ratio > 0:
                    width_ratio = new_width / self.resize_start_size[0] if self.resize_start_size[0] > 0 else 1
                    height_ratio = new_height / self.resize_start_size[1] if self.resize_start_size[1] > 0 else 1

                    if abs(width_ratio - 1) > abs(height_ratio - 1):
                        new_height = max(20, int(new_width / element.aspect_ratio))
                    else:
                        new_width = max(20, int(new_height * element.aspect_ratio))

                    if self.resize_handle == self.HANDLE_TL:
                        element.x = int(self.resize_start_pos_element[0] + self.resize_start_size[0] - new_width)
                        element.y = int(self.resize_start_pos_element[1] + self.resize_start_size[1] - new_height)
                    elif self.resize_handle == self.HANDLE_TR:
                        element.y = int(self.resize_start_pos_element[1] + self.resize_start_size[1] - new_height)
                    elif self.resize_handle == self.HANDLE_BL:
                        element.x = int(self.resize_start_pos_element[0] + self.resize_start_size[0] - new_width)

                element.width = new_width
                element.height = new_height

            self.element_resized.emit(self.selected_indices[0])
            self.update()
            return

        # Handle dragging (single or multiple elements)
        if self.dragging and self.selected_indices:
            dx = (pos.x() - self.drag_start_mouse.x()) / self.scale
            dy = (pos.y() - self.drag_start_mouse.y()) / self.scale

            for idx in self.selected_indices:
                if idx in self.drag_start_positions:
                    start_x, start_y = self.drag_start_positions[idx]
                    new_x = int(start_x + dx)
                    new_y = int(start_y + dy)
                    new_x = max(0, min(new_x, DISPLAY_WIDTH - 50))
                    new_y = max(0, min(new_y, DISPLAY_HEIGHT - 50))
                    self.elements[idx].x = new_x
                    self.elements[idx].y = new_y

            if len(self.selected_indices) == 1:
                el = self.elements[self.selected_indices[0]]
                self.element_moved.emit(self.selected_indices[0], el.x, el.y)
            self.update()
            return

        # Update cursor based on hover
        if len(self.selected_indices) > 1:
            # Multi-selection - check for multi-selection resize handles
            handle = self.get_multi_handle_at(pos)
            if handle in [self.HANDLE_TL, self.HANDLE_BR]:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in [self.HANDLE_TR, self.HANDLE_BL]:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        elif len(self.selected_indices) == 1:
            element = self.elements[self.selected_indices[0]]
            handle = self.get_handle_at(pos, element)
            if handle in [self.HANDLE_TL, self.HANDLE_BR]:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in [self.HANDLE_TR, self.HANDLE_BL]:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            self.resize_handle = self.HANDLE_NONE

    def keyPressEvent(self, event):
        """Handle arrow key nudging for selected elements."""
        if not self.selected_indices:
            return

        # Check if any selected element is locked
        any_locked = any(self.elements[idx].locked for idx in self.selected_indices)
        if any_locked:
            return

        key = event.key()
        shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        # Determine nudge amount: 10px with Shift, 1px without
        nudge = 10 if shift_held else 1

        dx, dy = 0, 0
        if key == Qt.Key.Key_Left:
            dx = -nudge
        elif key == Qt.Key.Key_Right:
            dx = nudge
        elif key == Qt.Key.Key_Up:
            dy = -nudge
        elif key == Qt.Key.Key_Down:
            dy = nudge
        else:
            # Not an arrow key, pass to parent
            super().keyPressEvent(event)
            return

        # Emit drag_started for undo state
        self.drag_started.emit()

        # Move all selected elements
        for idx in self.selected_indices:
            element = self.elements[idx]
            element.x += dx
            element.y += dy
            self.element_moved.emit(idx, element.x, element.y)

        self.update()
