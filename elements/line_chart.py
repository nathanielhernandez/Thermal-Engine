"""
Line Chart Element

A smooth line chart that shows current value on the right
and history of values scrolling left.
"""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QPainterPath, QLinearGradient

# Import SOURCE_UNITS for proper unit display
try:
    from constants import SOURCE_UNITS
except ImportError:
    SOURCE_UNITS = {}


def get_value_with_unit(value, source):
    """Format a value with its appropriate unit symbol."""
    unit_info = SOURCE_UNITS.get(source, {"symbol": "%", "type": "percent"})
    symbol = unit_info.get("symbol", "%")
    unit_type = unit_info.get("type", "percent")

    if unit_type in ["clock", "temp", "power"]:
        return f"{value:.0f}{symbol}"
    elif unit_type in ["size", "speed"]:
        return f"{value:.1f}{symbol}"
    else:  # percent
        return f"{value:.0f}{symbol}"

ELEMENT_TYPE = "line_chart"
ELEMENT_NAME = "Line Chart"

DEFAULT_PROPS = {
    "x": 100,
    "y": 100,
    "width": 300,
    "height": 100,
    "color": "#00ff96",
    "background_color": "#1a1a2e",
    "source": "cpu_percent",
    "value": 50,
    "text": "CPU",
    "font_size": 14,
    "show_background": True,
    "show_label": True,
    "show_gradient": True,
}

# Store history per element (keyed by element name)
_value_history = {}
_last_update_time = {}
MAX_HISTORY = 100
UPDATE_INTERVAL = 0.05  # Add a point every 50ms (20 points per second max)


def get_history(element):
    """Get or create history for this element."""
    key = getattr(element, 'name', id(element))
    if key not in _value_history:
        _value_history[key] = []
    return _value_history[key]


def add_value(element, value):
    """Add a value to the history with rate limiting."""
    import time
    key = getattr(element, 'name', id(element))
    current_time = time.time()
    last_time = _last_update_time.get(key, 0)

    # Only add value if enough time has passed (rate limiting)
    if current_time - last_time >= UPDATE_INTERVAL:
        history = get_history(element)
        history.append(float(value))
        if len(history) > MAX_HISTORY:
            history.pop(0)
        _last_update_time[key] = current_time
        return True
    return False


def apply_opacity(color, opacity):
    """Apply opacity (0-100) to a QColor."""
    if isinstance(color, str):
        color = QColor(color)
    else:
        color = QColor(color)
    alpha = int(255 * opacity / 100)
    color.setAlpha(alpha)
    return color


def draw_preview(painter, element, x, y, scale):
    """Draw the chart in the Qt preview canvas."""
    width = int(element.width * scale)
    height = int(element.height * scale)

    # Get opacity values
    color_opacity = getattr(element, 'color_opacity', 100)
    bg_opacity = getattr(element, 'background_color_opacity', 100)

    color = apply_opacity(element.color, color_opacity)
    bg_color = apply_opacity(element.background_color, bg_opacity)

    # Get display options (default to True for backwards compatibility)
    show_background = getattr(element, 'show_background', True)
    show_label = getattr(element, 'show_label', True)
    show_gradient = getattr(element, 'show_gradient', True)

    # Draw background
    if show_background:
        painter.fillRect(x, y, width, height, bg_color)
        # Draw border
        painter.setPen(QPen(QColor(60, 60, 80), 1))
        painter.drawRect(x, y, width, height)

    # Get history and add current value (rate-limited)
    add_value(element, element.value)
    history = get_history(element)

    if len(history) < 2:
        return

    # Calculate points for the chart
    num_points = min(len(history), int(width / 3))  # One point every 3 pixels
    if num_points < 2:
        return

    points = []
    history_slice = history[-num_points:]

    for i, value in enumerate(history_slice):
        px = x + (i / (num_points - 1)) * width
        # Clamp value between 0-100 for percentage-based sources
        clamped_value = max(0, min(100, value))
        py = y + height - (clamped_value / 100) * height
        points.append(QPointF(px, py))

    # Create path for the line
    if len(points) >= 2:
        # Build the line path
        line_path = QPainterPath()
        line_path.moveTo(points[0])

        # Connect points with straight lines (simpler, more reliable)
        for i in range(1, len(points)):
            line_path.lineTo(points[i])

        # Create fill path (closed polygon under the line)
        fill_path = QPainterPath()
        fill_path.moveTo(points[0].x(), y + height)  # Start at bottom-left
        for point in points:
            fill_path.lineTo(point)  # Trace the line
        fill_path.lineTo(points[-1].x(), y + height)  # Go to bottom-right
        fill_path.closeSubpath()  # Close back to start

        # Draw gradient fill
        if show_gradient:
            gradient = QLinearGradient(x, y, x, y + height)
            fill_color = QColor(color)
            # Scale alpha based on color opacity
            fill_color.setAlpha(int(100 * color_opacity / 100))
            gradient.setColorAt(0, fill_color)
            fill_color_bottom = QColor(color)
            fill_color_bottom.setAlpha(int(20 * color_opacity / 100))
            gradient.setColorAt(1, fill_color_bottom)

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(fill_path)

        # Draw the line
        pen = QPen(color, 2 * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line_path)

        # Draw current value dot
        if points:
            last_point = points[-1]
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(last_point, 4 * scale, 4 * scale)

    # Draw label and value
    if show_label:
        from PySide6.QtGui import QFont
        font = QFont("Arial")
        font.setPixelSize(int(element.font_size * scale))
        painter.setFont(font)
        painter.setPen(QPen(color))

        label_text = f"{element.text}: {get_value_with_unit(element.value, element.source)}"
        painter.drawText(x + 5, y + int(element.font_size * scale) + 2, label_text)


def hex_to_rgba(hex_color, opacity=100):
    """Convert hex color and opacity (0-100) to RGBA tuple."""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(255 * opacity / 100)
    return (r, g, b, a)


def render_image(draw, img, element):
    """Render the chart using PIL for the actual display."""
    from PIL import Image as PILImage, ImageDraw

    x, y = element.x, element.y
    width, height = element.width, element.height
    color = element.color
    bg_color = element.background_color

    # Get opacity values
    color_opacity = getattr(element, 'color_opacity', 100)
    bg_opacity = getattr(element, 'background_color_opacity', 100)

    # Get display options (default to True for backwards compatibility)
    show_background = getattr(element, 'show_background', True)
    show_label = getattr(element, 'show_label', True)
    show_gradient = getattr(element, 'show_gradient', True)

    # Draw background with opacity
    if show_background:
        if bg_opacity < 100:
            overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            bg_rgba = hex_to_rgba(bg_color, bg_opacity)
            overlay_draw.rectangle([x, y, x + width, y + height], fill=bg_rgba, outline=(60, 60, 80, 255))
            if img.mode == 'RGBA':
                img.alpha_composite(overlay)
            else:
                temp_img = img.convert('RGBA')
                temp_img = PILImage.alpha_composite(temp_img, overlay)
                img.paste(temp_img.convert('RGB'), (0, 0))
            draw = ImageDraw.Draw(img)
        else:
            draw.rectangle([x, y, x + width, y + height], fill=bg_color, outline="#3c3c50")

    # Get history and add current value (rate-limited)
    add_value(element, element.value)
    history = get_history(element)

    if len(history) < 2:
        return

    # Calculate points
    num_points = min(len(history), width // 3)
    if num_points < 2:
        return

    history_slice = history[-num_points:]
    points = []

    for i, value in enumerate(history_slice):
        px = x + (i / (num_points - 1)) * width
        clamped_value = max(0, min(100, value))
        py = y + height - (clamped_value / 100) * height
        points.append((int(px), int(py)))

    if len(points) >= 2:
        # Parse color to RGB
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
        else:
            r, g, b = 0, 255, 150

        # Draw gradient fill
        if show_gradient:
            # Create fill polygon points (line points + bottom corners)
            fill_points = points + [(points[-1][0], y + height), (points[0][0], y + height)]

            # Create RGBA overlay for gradient effect
            overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)

            # Draw semi-transparent fill polygon (scale alpha by color_opacity)
            fill_alpha = int(60 * color_opacity / 100)
            overlay_draw.polygon(fill_points, fill=(r, g, b, fill_alpha))

            # Composite onto main image
            if img.mode == 'RGBA':
                img.alpha_composite(overlay)
            else:
                temp_img = img.convert('RGBA')
                temp_img = PILImage.alpha_composite(temp_img, overlay)
                img.paste(temp_img.convert('RGB'), (0, 0))

            # Redraw on fresh draw context after paste
            draw = ImageDraw.Draw(img)

        # Draw the line segments with opacity
        if color_opacity < 100:
            overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            line_color = (r, g, b, int(255 * color_opacity / 100))
            for i in range(len(points) - 1):
                overlay_draw.line([points[i], points[i + 1]], fill=line_color, width=2)
            last_x, last_y = points[-1]
            overlay_draw.ellipse([last_x - 4, last_y - 4, last_x + 4, last_y + 4], fill=line_color)
            if img.mode == 'RGBA':
                img.alpha_composite(overlay)
            else:
                temp_img = img.convert('RGBA')
                temp_img = PILImage.alpha_composite(temp_img, overlay)
                img.paste(temp_img.convert('RGB'), (0, 0))
            draw = ImageDraw.Draw(img)
        else:
            # Draw the line segments
            for i in range(len(points) - 1):
                draw.line([points[i], points[i + 1]], fill=color, width=2)
            # Draw current value dot
            last_x, last_y = points[-1]
            draw.ellipse([last_x - 4, last_y - 4, last_x + 4, last_y + 4], fill=color)

    # Draw label
    if show_label:
        try:
            from PIL import ImageFont
            import os
            font_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf')
            font = ImageFont.truetype(font_path, element.font_size)
        except:
            font = None

        label_text = f"{element.text}: {get_value_with_unit(element.value, element.source)}"

        if color_opacity < 100:
            overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            label_rgba = hex_to_rgba(color, color_opacity)
            overlay_draw.text((x + 5, y + 2), label_text, fill=label_rgba, font=font)
            if img.mode == 'RGBA':
                img.alpha_composite(overlay)
            else:
                temp_img = img.convert('RGBA')
                temp_img = PILImage.alpha_composite(temp_img, overlay)
                img.paste(temp_img.convert('RGB'), (0, 0))
        else:
            draw.text((x + 5, y + 2), label_text, fill=color, font=font)
