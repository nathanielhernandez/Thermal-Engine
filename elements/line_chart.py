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
    "line_thickness": 2,
    "smooth": False,
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


def catmull_rom_spline(points, num_interpolated=10):
    """
    Generate smooth curve points using Catmull-Rom spline interpolation.

    Args:
        points: List of (x, y) tuples or QPointF objects
        num_interpolated: Number of points to interpolate between each pair

    Returns:
        List of interpolated points
    """
    if len(points) < 2:
        return points

    # Convert QPointF to tuples if needed
    pts = []
    for p in points:
        if hasattr(p, 'x') and callable(getattr(p, 'x', None)):
            pts.append((p.x(), p.y()))
        elif hasattr(p, 'x'):
            pts.append((p.x, p.y))
        else:
            pts.append(p)

    # Duplicate first and last points for boundary conditions
    pts = [pts[0]] + pts + [pts[-1]]

    result = []

    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i-1], pts[i], pts[i+1], pts[i+2]

        for t_idx in range(num_interpolated):
            t = t_idx / num_interpolated
            t2 = t * t
            t3 = t2 * t

            # Catmull-Rom basis functions
            x = 0.5 * ((2 * p1[0]) +
                      (-p0[0] + p2[0]) * t +
                      (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                      (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3)

            y = 0.5 * ((2 * p1[1]) +
                      (-p0[1] + p2[1]) * t +
                      (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                      (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3)

            result.append((x, y))

    # Add the last point
    result.append(pts[-2])

    return result


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
    line_thickness = getattr(element, 'line_thickness', 2)
    smooth = getattr(element, 'smooth', False)

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
        # Apply smoothing if enabled
        if smooth and len(points) >= 3:
            smooth_pts = catmull_rom_spline(points, num_interpolated=8)
            draw_points = [QPointF(p[0], p[1]) for p in smooth_pts]
        else:
            draw_points = points

        # Build the line path
        line_path = QPainterPath()
        line_path.moveTo(draw_points[0])

        # Connect points
        for i in range(1, len(draw_points)):
            line_path.lineTo(draw_points[i])

        # Create fill path (closed polygon under the line)
        fill_path = QPainterPath()
        fill_path.moveTo(draw_points[0].x(), y + height)  # Start at bottom-left
        for point in draw_points:
            fill_path.lineTo(point)  # Trace the line
        fill_path.lineTo(draw_points[-1].x(), y + height)  # Go to bottom-right
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
        pen = QPen(color, line_thickness * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line_path)

        # Draw current value dot
        if draw_points:
            last_point = draw_points[-1]
            dot_size = max(3, line_thickness + 1) * scale
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(last_point, dot_size, dot_size)

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
    line_thickness = getattr(element, 'line_thickness', 2)
    smooth = getattr(element, 'smooth', False)

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
        # Apply smoothing if enabled
        if smooth and len(points) >= 3:
            draw_points = catmull_rom_spline(points, num_interpolated=8)
            draw_points = [(int(p[0]), int(p[1])) for p in draw_points]
        else:
            draw_points = points

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
            fill_points = draw_points + [(draw_points[-1][0], y + height), (draw_points[0][0], y + height)]

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

        # Calculate dot size based on line thickness
        dot_size = max(3, line_thickness + 1)

        # Draw the line segments with opacity
        if color_opacity < 100:
            overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            line_color = (r, g, b, int(255 * color_opacity / 100))
            for i in range(len(draw_points) - 1):
                overlay_draw.line([draw_points[i], draw_points[i + 1]], fill=line_color, width=line_thickness)
            last_x, last_y = draw_points[-1]
            overlay_draw.ellipse([last_x - dot_size, last_y - dot_size, last_x + dot_size, last_y + dot_size], fill=line_color)
            if img.mode == 'RGBA':
                img.alpha_composite(overlay)
            else:
                temp_img = img.convert('RGBA')
                temp_img = PILImage.alpha_composite(temp_img, overlay)
                img.paste(temp_img.convert('RGB'), (0, 0))
            draw = ImageDraw.Draw(img)
        else:
            # Draw the line segments
            for i in range(len(draw_points) - 1):
                draw.line([draw_points[i], draw_points[i + 1]], fill=color, width=line_thickness)
            # Draw current value dot
            last_x, last_y = draw_points[-1]
            draw.ellipse([last_x - dot_size, last_y - dot_size, last_x + dot_size, last_y + dot_size], fill=color)

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
