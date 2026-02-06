"""
PropertiesPanel - Element property editing widget.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QColorDialog, QFileDialog, QComboBox,
    QFormLayout, QScrollArea, QFrame, QCheckBox, QPushButton,
    QStyledItemDelegate, QStyle, QSlider, QDialog, QDialogButtonBox,
    QSizePolicy, QGroupBox
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import QColor, QFont, QPixmap, QFontDatabase, QPainter, QLinearGradient, QPen, QBrush, QIcon


class NoScrollComboBox(QComboBox):
    """ComboBox that ignores wheel events to allow parent scrolling."""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollSpinBox(QSpinBox):
    """SpinBox that ignores wheel events to allow parent scrolling."""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """DoubleSpinBox that ignores wheel events to allow parent scrolling."""
    def wheelEvent(self, event):
        event.ignore()


def create_alignment_icon(align_type, size=20):
    """Create alignment icons programmatically using QPainter.

    align_type options:
    - 'text_left', 'text_center', 'text_right' (text alignment - horizontal lines)
    - 'h_left', 'h_center', 'h_right' (object horizontal alignment)
    - 'v_top', 'v_middle', 'v_bottom' (object vertical alignment)
    - 'dist_h', 'dist_v' (distribute horizontally/vertically)
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)

    color = QColor("#dddddd")
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(color))

    if align_type.startswith('text_'):
        # Text alignment - 4 horizontal bars of varying lengths
        bar_height = 3
        widths = [16, 10, 14, 8]
        y_positions = [2, 7, 12, 17]

        for y, w in zip(y_positions, widths):
            if align_type == 'text_left':
                painter.fillRect(2, y, w, bar_height, color)
            elif align_type == 'text_center':
                x = (size - w) // 2
                painter.fillRect(x, y, w, bar_height, color)
            elif align_type == 'text_right':
                painter.fillRect(size - 2 - w, y, w, bar_height, color)

    elif align_type.startswith('h_'):
        # Horizontal alignment - two rectangles at different heights
        if align_type == 'h_left':
            painter.fillRect(1, 1, 7, 7, color)
            painter.fillRect(1, 11, 15, 7, color)
        elif align_type == 'h_center':
            painter.fillRect(6, 1, 7, 7, color)
            painter.fillRect(2, 11, 15, 7, color)
        elif align_type == 'h_right':
            painter.fillRect(11, 1, 7, 7, color)
            painter.fillRect(3, 11, 15, 7, color)

    elif align_type.startswith('v_'):
        # Vertical alignment - two rectangles side by side
        if align_type == 'v_top':
            painter.fillRect(1, 1, 7, 7, color)
            painter.fillRect(11, 1, 7, 15, color)
        elif align_type == 'v_middle':
            painter.fillRect(1, 6, 7, 7, color)
            painter.fillRect(11, 2, 7, 15, color)
        elif align_type == 'v_bottom':
            painter.fillRect(1, 11, 7, 7, color)
            painter.fillRect(11, 3, 7, 15, color)

    elif align_type.startswith('dist_'):
        # Distribution - 3 evenly spaced rectangles with arrows
        if align_type == 'dist_h':
            # 3 vertical bars evenly spaced horizontally
            painter.fillRect(2, 4, 4, 12, color)
            painter.fillRect(8, 4, 4, 12, color)
            painter.fillRect(14, 4, 4, 12, color)
        elif align_type == 'dist_v':
            # 3 horizontal bars evenly spaced vertically
            painter.fillRect(4, 2, 12, 4, color)
            painter.fillRect(4, 8, 12, 4, color)
            painter.fillRect(4, 14, 12, 4, color)

    painter.end()
    return QIcon(pixmap)


class ColorPickerDialog(QDialog):
    """Custom color picker dialog with opacity slider."""

    def __init__(self, initial_color, initial_opacity=100, title="Select Color", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.color = QColor(initial_color)
        self.opacity = initial_opacity

        layout = QVBoxLayout(self)

        # Embed QColorDialog as a widget
        self.color_dialog = QColorDialog(self.color, self)
        self.color_dialog.setWindowFlags(Qt.WindowType.Widget)
        self.color_dialog.setOptions(
            QColorDialog.ColorDialogOption.DontUseNativeDialog |
            QColorDialog.ColorDialogOption.NoButtons
        )
        self.color_dialog.currentColorChanged.connect(self._on_color_changed)
        layout.addWidget(self.color_dialog)

        # Opacity section
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Opacity:")
        opacity_label.setFixedWidth(60)
        opacity_layout.addWidget(opacity_label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(initial_opacity)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)

        self.opacity_value_label = QLabel(f"{initial_opacity}%")
        self.opacity_value_label.setFixedWidth(40)
        opacity_layout.addWidget(self.opacity_value_label)

        layout.addLayout(opacity_layout)

        # Preview
        preview_layout = QHBoxLayout()
        preview_label = QLabel("Preview:")
        preview_label.setFixedWidth(60)
        preview_layout.addWidget(preview_label)

        self.preview_widget = QWidget()
        self.preview_widget.setFixedHeight(30)
        self._update_preview()
        preview_layout.addWidget(self.preview_widget)

        layout.addLayout(preview_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_color_changed(self, color):
        self.color = color
        self._update_preview()

    def _on_opacity_changed(self, value):
        self.opacity = value
        self.opacity_value_label.setText(f"{value}%")
        self._update_preview()

    def _update_preview(self):
        # Show checkerboard pattern behind color to visualize transparency
        alpha = int(self.opacity * 255 / 100)
        self.preview_widget.setStyleSheet(f"""
            background-color: rgba({self.color.red()}, {self.color.green()}, {self.color.blue()}, {alpha});
            border: 1px solid #555;
            border-radius: 4px;
        """)

    def get_color(self):
        return self.color

    def get_opacity(self):
        return self.opacity


class GradientPreviewWidget(QPushButton):
    """Button that displays a gradient preview and allows clicking to edit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gradient_stops = [(0.0, "#00ff00"), (1.0, "#ff0000")]  # Default green to red
        self.setFixedHeight(26)
        self.setMinimumWidth(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("Click to edit gradient")
        self._update_style()

    def set_gradient(self, stops):
        """Set gradient stops as list of (position, color) tuples."""
        self.gradient_stops = stops if stops else [(0.0, "#00ff00"), (1.0, "#ff0000")]
        self._update_style()

    def get_gradient(self):
        return self.gradient_stops

    def _update_style(self):
        """Update button style to show gradient."""
        # Build CSS gradient string
        stops_css = ", ".join([f"{color} {int(pos * 100)}%" for pos, color in sorted(self.gradient_stops)])
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {self._stops_to_css()});
                border: 1px solid #555;
                border-radius: 4px;
                color: white;
                font-size: 10px;
            }}
            QPushButton:hover {{
                border: 1px solid #888;
            }}
        """)

    def _stops_to_css(self):
        """Convert gradient stops to Qt CSS format."""
        parts = []
        for pos, color in sorted(self.gradient_stops):
            parts.append(f"stop:{pos} {color}")
        return ", ".join(parts)


class GradientEditorDialog(QDialog):
    """Dialog for editing a gradient with multiple color stops."""

    def __init__(self, initial_stops=None, title="Edit Gradient", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        # Default gradient: green to red (good to bad for gauges)
        self.stops = list(initial_stops) if initial_stops else [(0.0, "#00ff96"), (1.0, "#ff4444")]

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Click bar to add stops. Drag stops to reposition. Double-click stop to change color.")
        instructions.setStyleSheet("color: #888; font-size: 11px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Gradient preview/editor
        self.gradient_bar = GradientBarEditor(self.stops)
        self.gradient_bar.stops_changed.connect(self._on_stops_changed)
        layout.addWidget(self.gradient_bar)

        # Stop list
        self.stops_layout = QVBoxLayout()
        self._rebuild_stops_list()
        layout.addLayout(self.stops_layout)

        # Preset gradients
        presets_label = QLabel("Presets:")
        presets_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(presets_label)

        presets_layout = QHBoxLayout()

        preset_good_bad = QPushButton("Good → Bad")
        preset_good_bad.clicked.connect(lambda: self._apply_preset([(0.0, "#00ff96"), (1.0, "#ff4444")]))
        presets_layout.addWidget(preset_good_bad)

        preset_cool_hot = QPushButton("Cool → Hot")
        preset_cool_hot.clicked.connect(lambda: self._apply_preset([(0.0, "#4444ff"), (0.5, "#ffff00"), (1.0, "#ff4444")]))
        presets_layout.addWidget(preset_cool_hot)

        preset_rainbow = QPushButton("Rainbow")
        preset_rainbow.clicked.connect(lambda: self._apply_preset([
            (0.0, "#ff0000"), (0.2, "#ffaa00"), (0.4, "#ffff00"),
            (0.6, "#00ff00"), (0.8, "#0088ff"), (1.0, "#aa00ff")
        ]))
        presets_layout.addWidget(preset_rainbow)

        layout.addLayout(presets_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _apply_preset(self, stops):
        self.stops = list(stops)
        self.gradient_bar.set_stops(self.stops)
        self._rebuild_stops_list()

    def _on_stops_changed(self, stops):
        self.stops = stops
        self._rebuild_stops_list()

    def _rebuild_stops_list(self):
        # Clear existing
        while self.stops_layout.count():
            child = self.stops_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add stop editors
        for i, (pos, color) in enumerate(sorted(self.stops)):
            stop_widget = QWidget()
            stop_layout = QHBoxLayout(stop_widget)
            stop_layout.setContentsMargins(0, 2, 0, 2)

            pos_label = QLabel(f"{int(pos * 100)}%:")
            pos_label.setFixedWidth(40)
            stop_layout.addWidget(pos_label)

            color_btn = QPushButton()
            color_btn.setFixedSize(60, 24)
            color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #555; border-radius: 3px;")
            color_btn.clicked.connect(lambda checked, idx=i: self._edit_stop_color(idx))
            stop_layout.addWidget(color_btn)

            if len(self.stops) > 2:  # Keep at least 2 stops
                remove_btn = QPushButton("×")
                remove_btn.setFixedSize(24, 24)
                remove_btn.clicked.connect(lambda checked, idx=i: self._remove_stop(idx))
                stop_layout.addWidget(remove_btn)

            stop_layout.addStretch()
            self.stops_layout.addWidget(stop_widget)

    def _edit_stop_color(self, index):
        sorted_stops = sorted(self.stops)
        pos, old_color = sorted_stops[index]
        color = QColorDialog.getColor(QColor(old_color), self, "Select Color")
        if color.isValid():
            # Find and update the stop
            for i, (p, c) in enumerate(self.stops):
                if abs(p - pos) < 0.001:
                    self.stops[i] = (p, color.name())
                    break
            self.gradient_bar.set_stops(self.stops)
            self._rebuild_stops_list()

    def _remove_stop(self, index):
        sorted_stops = sorted(self.stops)
        pos, _ = sorted_stops[index]
        self.stops = [(p, c) for p, c in self.stops if abs(p - pos) > 0.001]
        self.gradient_bar.set_stops(self.stops)
        self._rebuild_stops_list()

    def get_stops(self):
        return sorted(self.stops)


class GradientBarEditor(QWidget):
    """Interactive gradient bar for adding/editing/dragging color stops."""
    stops_changed = Signal(list)

    def __init__(self, stops=None, parent=None):
        super().__init__(parent)
        self.stops = list(stops) if stops else [(0.0, "#00ff96"), (1.0, "#ff4444")]
        self.setFixedHeight(50)
        self.setMinimumWidth(300)
        self.setMouseTracking(True)
        self.dragging_index = -1  # Index of stop being dragged, -1 if none
        self.hovered_index = -1   # Index of stop being hovered
        self._update_cursor()

    def set_stops(self, stops):
        self.stops = list(stops)
        self.update()

    def _get_bar_rect(self):
        return QRect(10, 5, self.width() - 20, 20)

    def _pos_to_x(self, pos):
        """Convert gradient position (0-1) to x coordinate."""
        bar_rect = self._get_bar_rect()
        return bar_rect.left() + pos * bar_rect.width()

    def _x_to_pos(self, x):
        """Convert x coordinate to gradient position (0-1)."""
        bar_rect = self._get_bar_rect()
        pos = (x - bar_rect.left()) / bar_rect.width()
        return max(0.0, min(1.0, pos))

    def _find_stop_at(self, x, y):
        """Find stop index at given coordinates, or -1 if none."""
        bar_rect = self._get_bar_rect()
        # Check if in marker area (below the bar)
        if y < 25 or y > 48:
            return -1

        pos = self._x_to_pos(x)
        for i, (stop_pos, _) in enumerate(self.stops):
            if abs(stop_pos - pos) < 0.03:  # ~10px tolerance
                return i
        return -1

    def _update_cursor(self):
        if self.dragging_index >= 0 or self.hovered_index >= 0:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_rect = self._get_bar_rect()

        # Create gradient
        gradient = QLinearGradient(bar_rect.left(), 0, bar_rect.right(), 0)
        for pos, color in self.stops:
            gradient.setColorAt(pos, QColor(color))

        # Draw gradient bar
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#555"), 1))
        painter.drawRoundedRect(bar_rect, 4, 4)

        # Draw stop markers
        for i, (pos, color) in enumerate(self.stops):
            x = self._pos_to_x(pos)
            # Highlight if hovered or dragged
            is_active = (i == self.hovered_index or i == self.dragging_index)

            # Triangle marker
            painter.setBrush(QBrush(QColor(color)))
            if is_active:
                painter.setPen(QPen(QColor("#00aaff"), 2))
            else:
                painter.setPen(QPen(QColor("#fff"), 1))

            painter.drawPolygon([
                QPoint(int(x), 28),
                QPoint(int(x - 6), 42),
                QPoint(int(x + 6), 42)
            ])

            # Draw position indicator when dragging
            if i == self.dragging_index:
                painter.setPen(QPen(QColor("#fff")))
                font = painter.font()
                font.setPixelSize(9)
                painter.setFont(font)
                painter.drawText(int(x - 15), 48, f"{int(pos * 100)}%")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._find_stop_at(event.pos().x(), event.pos().y())
            if idx >= 0:
                # Start dragging this stop
                self.dragging_index = idx
                self._update_cursor()
                return

            # Check if clicking on the bar to add a new stop
            bar_rect = self._get_bar_rect()
            if bar_rect.contains(event.pos()):
                pos = self._x_to_pos(event.pos().x())
                # Add new stop with interpolated color
                color = self._interpolate_color(pos)
                new_color = QColorDialog.getColor(QColor(color), self, "Select Color for New Stop")
                if new_color.isValid():
                    self.stops.append((pos, new_color.name()))
                    self.stops.sort(key=lambda s: s[0])
                    self.update()
                    self.stops_changed.emit(self.stops)

    def mouseMoveEvent(self, event):
        if self.dragging_index >= 0:
            # Update stop position while dragging
            new_pos = self._x_to_pos(event.pos().x())

            # Don't allow dragging past other stops (keep order)
            color = self.stops[self.dragging_index][1]
            self.stops[self.dragging_index] = (new_pos, color)
            self.stops.sort(key=lambda s: s[0])
            # Find new index after sort
            for i, (p, c) in enumerate(self.stops):
                if c == color and abs(p - new_pos) < 0.001:
                    self.dragging_index = i
                    break

            self.update()
            self.stops_changed.emit(self.stops)
        else:
            # Update hover state
            old_hover = self.hovered_index
            self.hovered_index = self._find_stop_at(event.pos().x(), event.pos().y())
            if old_hover != self.hovered_index:
                self._update_cursor()
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_index >= 0:
            self.dragging_index = -1
            self._update_cursor()
            self.update()

    def mouseDoubleClickEvent(self, event):
        """Double-click on a stop to edit its color."""
        idx = self._find_stop_at(event.pos().x(), event.pos().y())
        if idx >= 0:
            pos, color = self.stops[idx]
            new_color = QColorDialog.getColor(QColor(color), self, "Select Color")
            if new_color.isValid():
                self.stops[idx] = (pos, new_color.name())
                self.update()
                self.stops_changed.emit(self.stops)

    def leaveEvent(self, event):
        self.hovered_index = -1
        self._update_cursor()
        self.update()

    def _interpolate_color(self, pos):
        """Get interpolated color at position."""
        sorted_stops = sorted(self.stops)
        if pos <= sorted_stops[0][0]:
            return sorted_stops[0][1]
        if pos >= sorted_stops[-1][0]:
            return sorted_stops[-1][1]

        for i in range(len(sorted_stops) - 1):
            if sorted_stops[i][0] <= pos <= sorted_stops[i + 1][0]:
                p1, c1 = sorted_stops[i]
                p2, c2 = sorted_stops[i + 1]
                t = (pos - p1) / (p2 - p1)
                color1 = QColor(c1)
                color2 = QColor(c2)
                r = int(color1.red() + t * (color2.red() - color1.red()))
                g = int(color1.green() + t * (color2.green() - color1.green()))
                b = int(color1.blue() + t * (color2.blue() - color1.blue()))
                return QColor(r, g, b).name()
        return "#ffffff"


import constants
from constants import DATA_SOURCES, DATA_SOURCES_CATEGORIZED


class FontPreviewDelegate(QStyledItemDelegate):
    """Custom delegate to render font names in their own typeface."""

    def paint(self, painter, option, index):
        font_name = index.data()
        if not font_name or font_name == "":
            super().paint(painter, option, index)
            return

        painter.save()

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        # Set the font to the actual font family
        font = QFont(font_name)
        font.setPixelSize(14)
        painter.setFont(font)

        # Draw the text
        text_rect = option.rect.adjusted(5, 0, -5, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, font_name)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(200, 24)


class PropertiesPanel(QWidget):
    property_changed = Signal()
    property_will_change = Signal()  # Emitted before first change (for undo)
    alignment_changed = Signal()  # Emitted when elements are aligned
    alignment_will_change = Signal()  # Emitted before alignment (for undo)

    def __init__(self):
        super().__init__()
        self.current_element = None
        self.multi_selection_elements = []
        self.multi_selection_indices = []
        self._undo_state_saved = False  # Track if undo state was saved for current edit session

        # Section headers for visibility control
        self.section_headers = {}
        self.section_fields = {}

        self.setup_ui()

    def create_section(self, title):
        """Create a styled section container with title."""
        # Container frame
        frame = QFrame()
        frame.setObjectName("sectionFrame")
        frame.setStyleSheet("""
            QFrame#sectionFrame {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QFrame#sectionFrame QLabel {
                background: transparent;
                border: none;
                min-height: 22px;
                qproperty-alignment: AlignVCenter;
            }
            QFrame#sectionFrame QCheckBox {
                background: transparent;
                border: none;
                color: #ccc;
            }
            QFrame#sectionFrame QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #666;
                border-radius: 3px;
                background-color: #1a1a1a;
            }
            QFrame#sectionFrame QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QFrame#sectionFrame QCheckBox::indicator:hover {
                border-color: #888;
            }
        """)

        # Layout for the section
        section_layout = QVBoxLayout(frame)
        section_layout.setContentsMargins(10, 8, 10, 10)
        section_layout.setSpacing(6)

        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #aaa;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0;
                margin-bottom: 4px;
            }
        """)
        section_layout.addWidget(title_label)

        # Form layout for fields
        form_layout = QFormLayout()
        form_layout.setSpacing(6)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        section_layout.addLayout(form_layout)

        return frame, form_layout

    def create_label(self, text):
        """Create a label with vertical center alignment."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return label

    def _set_svg_icon(self, button, svg_content):
        """Set an SVG icon on a button using QIcon."""
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QPixmap, QPainter
        from PySide6.QtCore import QByteArray

        # Replace currentColor with actual color based on palette
        color = "#cccccc"  # Light gray for dark theme
        svg_content = svg_content.replace("currentColor", color)

        svg_bytes = QByteArray(svg_content.encode('utf-8'))
        renderer = QSvgRenderer(svg_bytes)

        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        button.setIcon(QIcon(pixmap))
        button.setIconSize(pixmap.size())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("Properties")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title)

        # Helper text when no element selected (in a container for proper centering)
        self.no_selection_container = QWidget()
        no_selection_layout = QVBoxLayout(self.no_selection_container)
        no_selection_layout.setContentsMargins(0, 0, 0, 0)
        no_selection_layout.addStretch()
        self.no_selection_label = QLabel("Select an element to edit its properties")
        self.no_selection_label.setStyleSheet("color: #888; padding: 20px; font-style: italic;")
        self.no_selection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_selection_label.setWordWrap(True)
        no_selection_layout.addWidget(self.no_selection_label)
        no_selection_layout.addStretch()
        layout.addWidget(self.no_selection_container)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMaximumWidth(320)
        self.scroll_area = scroll

        self.props_widget = QWidget()
        self.props_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.props_widget.setMaximumWidth(310)
        self.props_layout = QVBoxLayout(self.props_widget)
        self.props_layout.setSpacing(8)
        self.props_layout.setContentsMargins(4, 4, 4, 4)

        # === GENERAL SECTION ===
        general_frame, general_layout = self.create_section("General")
        self.section_headers['general'] = general_frame
        self.props_layout.addWidget(general_frame)

        self.name_edit = QLineEdit()
        self.name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.name_edit.setMinimumWidth(50)
        self.name_edit.textChanged.connect(self.on_property_changed)
        self.name_label = self.create_label("Name:")
        general_layout.addRow(self.name_label, self.name_edit)

        self.section_fields['general'] = [
            (self.name_label, self.name_edit)
        ]

        # === TRANSFORM SECTION ===
        transform_frame, transform_layout = self.create_section("Transform")
        self.section_headers['transform'] = transform_frame
        self.props_layout.addWidget(transform_frame)

        # Position row (X and Y side by side)
        position_layout = QHBoxLayout()
        position_layout.setSpacing(8)

        self.x_spin = NoScrollSpinBox()
        self.x_spin.setRange(0, constants.DISPLAY_WIDTH)
        self.x_spin.valueChanged.connect(self.on_property_changed)
        x_container = QHBoxLayout()
        x_container.setSpacing(4)
        self.x_label = QLabel("X:")
        x_container.addWidget(self.x_label)
        x_container.addWidget(self.x_spin)
        position_layout.addLayout(x_container)

        self.y_spin = NoScrollSpinBox()
        self.y_spin.setRange(0, constants.DISPLAY_HEIGHT)
        self.y_spin.valueChanged.connect(self.on_property_changed)
        y_container = QHBoxLayout()
        y_container.setSpacing(4)
        self.y_label = QLabel("Y:")
        y_container.addWidget(self.y_label)
        y_container.addWidget(self.y_spin)
        position_layout.addLayout(y_container)

        self.position_widget = QWidget()
        self.position_widget.setLayout(position_layout)
        self.position_label = self.create_label("Position:")
        transform_layout.addRow(self.position_label, self.position_widget)

        # Size row (Width and Height side by side)
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)

        self.width_spin = NoScrollSpinBox()
        self.width_spin.setRange(10, constants.DISPLAY_WIDTH)
        self.width_spin.valueChanged.connect(self.on_property_changed)
        w_container = QHBoxLayout()
        w_container.setSpacing(4)
        self.width_label = QLabel("W:")
        w_container.addWidget(self.width_label)
        w_container.addWidget(self.width_spin)
        size_layout.addLayout(w_container)

        self.height_spin = NoScrollSpinBox()
        self.height_spin.setRange(10, constants.DISPLAY_HEIGHT)
        self.height_spin.valueChanged.connect(self.on_property_changed)
        h_container = QHBoxLayout()
        h_container.setSpacing(4)
        self.height_label = QLabel("H:")
        h_container.addWidget(self.height_label)
        h_container.addWidget(self.height_spin)
        size_layout.addLayout(h_container)

        self.size_widget = QWidget()
        self.size_widget.setLayout(size_layout)
        self.size_label = self.create_label("Size:")
        transform_layout.addRow(self.size_label, self.size_widget)

        self.radius_spin = NoScrollSpinBox()
        self.radius_spin.setRange(20, 300)
        self.radius_spin.valueChanged.connect(self.on_property_changed)
        self.radius_label = self.create_label("Radius:")
        transform_layout.addRow(self.radius_label, self.radius_spin)

        self.section_fields['transform'] = [
            (self.position_label, self.position_widget),
            (self.size_label, self.size_widget),
            (self.radius_label, self.radius_spin)
        ]

        # === COLORS SECTION ===
        colors_frame, colors_layout = self.create_section("Colors")
        self.section_headers['colors'] = colors_frame
        self.props_layout.addWidget(colors_frame)

        # Element color
        self.color_btn = QPushButton()
        self.color_btn.setFixedHeight(26)
        self.color_btn.clicked.connect(self.choose_color)
        self.color_label = self.create_label("Color:")
        colors_layout.addRow(self.color_label, self.color_btn)

        # Gradient preview widget (shown when gradient fill is enabled, above BG color)
        self.gradient_preview = GradientPreviewWidget()
        self.gradient_preview.clicked.connect(self.edit_gradient)
        self.gradient_preview_label = self.create_label("Gradient:")
        colors_layout.addRow(self.gradient_preview_label, self.gradient_preview)

        # Background color
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedHeight(26)
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.bg_color_label = self.create_label("BG Color:")
        colors_layout.addRow(self.bg_color_label, self.bg_color_btn)

        # Gradient fill checkbox (for gauges)
        self.gradient_fill_check = QCheckBox("Use Gradient Fill")
        self.gradient_fill_check.stateChanged.connect(self.on_gradient_fill_changed)
        self.gradient_fill_label = QLabel("")
        colors_layout.addRow(self.gradient_fill_label, self.gradient_fill_check)

        # Bar gauge border options - checkbox and group box sub-panel
        self.bar_border_check = QCheckBox("Show Border")
        self.bar_border_check.stateChanged.connect(self.on_bar_border_changed)
        self.bar_border_label = QLabel("")
        colors_layout.addRow(self.bar_border_label, self.bar_border_check)

        # Border options group box (shown when border is enabled)
        self.bar_border_group = QGroupBox("Border")
        border_group_layout = QFormLayout(self.bar_border_group)
        border_group_layout.setContentsMargins(8, 8, 8, 8)

        # Stroke position dropdown
        self.bar_border_position_combo = NoScrollComboBox()
        self.bar_border_position_combo.addItem("Inside", "inside")
        self.bar_border_position_combo.addItem("Center", "center")
        self.bar_border_position_combo.addItem("Outside", "outside")
        self.bar_border_position_combo.currentIndexChanged.connect(self.on_property_changed)
        border_group_layout.addRow(self.create_label("Position:"), self.bar_border_position_combo)

        # Border width
        self.bar_border_width_spin = NoScrollSpinBox()
        self.bar_border_width_spin.setRange(1, 20)
        self.bar_border_width_spin.setValue(2)
        self.bar_border_width_spin.valueChanged.connect(self.on_property_changed)
        border_group_layout.addRow(self.create_label("Width:"), self.bar_border_width_spin)

        # Border color (opacity handled in color picker)
        self.bar_border_color_btn = QPushButton()
        self.bar_border_color_btn.setFixedHeight(26)
        self.bar_border_color_btn.setStyleSheet("background-color: #ffffff;")
        self.bar_border_color_btn.clicked.connect(self.choose_bar_border_color)
        border_group_layout.addRow(self.create_label("Color:"), self.bar_border_color_btn)

        # Add group box to colors layout (hidden by default)
        self.bar_border_group.setVisible(False)
        colors_layout.addRow(self.bar_border_group)

        self.section_fields['colors'] = [
            (self.color_label, self.color_btn),
            (self.gradient_preview_label, self.gradient_preview),
            (self.bg_color_label, self.bg_color_btn),
            (self.gradient_fill_label, self.gradient_fill_check),
            (self.bar_border_label, self.bar_border_check),
            (self.bar_border_group, None)
        ]

        # === APPEARANCE SECTION ===
        appearance_frame, appearance_layout = self.create_section("Appearance")
        self.section_headers['appearance'] = appearance_frame
        self.props_layout.addWidget(appearance_frame)

        self.border_radius_spin = NoScrollSpinBox()
        self.border_radius_spin.setRange(0, 500)
        self.border_radius_spin.valueChanged.connect(self.on_property_changed)
        self.border_radius_label = self.create_label("Border Radius:")
        appearance_layout.addRow(self.border_radius_label, self.border_radius_spin)

        # Glass effect controls
        self.glass_effect_check = QCheckBox("Frosted Glass")
        self.glass_effect_check.stateChanged.connect(self.on_property_changed)
        self.glass_effect_label = self.create_label("Glass Effect:")
        appearance_layout.addRow(self.glass_effect_label, self.glass_effect_check)

        self.glass_blur_spin = NoScrollSpinBox()
        self.glass_blur_spin.setRange(1, 50)
        self.glass_blur_spin.setValue(10)
        self.glass_blur_spin.valueChanged.connect(self.on_property_changed)
        self.glass_blur_label = self.create_label("Glass Blur:")
        appearance_layout.addRow(self.glass_blur_label, self.glass_blur_spin)

        self.glass_opacity_spin = NoScrollSpinBox()
        self.glass_opacity_spin.setRange(0, 100)
        self.glass_opacity_spin.setValue(50)
        self.glass_opacity_spin.setSuffix("%")
        self.glass_opacity_spin.valueChanged.connect(self.on_property_changed)
        self.glass_opacity_label = self.create_label("Glass Tint:")
        appearance_layout.addRow(self.glass_opacity_label, self.glass_opacity_spin)

        self.section_fields['appearance'] = [
            (self.border_radius_label, self.border_radius_spin),
            (self.glass_effect_label, self.glass_effect_check),
            (self.glass_blur_label, self.glass_blur_spin),
            (self.glass_opacity_label, self.glass_opacity_spin)
        ]

        # === TEXT SECTION ===
        text_frame, text_layout = self.create_section("Text")
        self.section_headers['text'] = text_frame
        self.props_layout.addWidget(text_frame)

        # === BAR GAUGE TEXT OPTIONS (at top of text section) ===
        self.bar_text_mode_combo = NoScrollComboBox()
        self.bar_text_mode_combo.addItem("Label + Value", "full")
        self.bar_text_mode_combo.addItem("Value Only", "value_only")
        self.bar_text_mode_combo.addItem("Label Only", "label_only")
        self.bar_text_mode_combo.addItem("Hidden", "none")
        self.bar_text_mode_combo.currentIndexChanged.connect(self.on_property_changed)
        self.bar_text_mode_label = self.create_label("Display:")
        text_layout.addRow(self.bar_text_mode_label, self.bar_text_mode_combo)

        self.bar_text_position_combo = NoScrollComboBox()
        self.bar_text_position_combo.addItem("Inside Bar", "inside")
        self.bar_text_position_combo.addItem("Left of Bar", "left")
        self.bar_text_position_combo.addItem("Right of Bar", "right")
        self.bar_text_position_combo.addItem("Top of Bar", "top")
        self.bar_text_position_combo.addItem("Bottom of Bar", "bottom")
        self.bar_text_position_combo.currentIndexChanged.connect(self.on_property_changed)
        self.bar_text_position_label = self.create_label("Position:")
        text_layout.addRow(self.bar_text_position_label, self.bar_text_position_combo)

        # === STANDALONE TEXT INPUT (for non-circle-gauge elements) ===
        self.text_edit = QLineEdit()
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.text_edit.setMinimumWidth(50)
        self.text_edit.textChanged.connect(self.on_property_changed)
        self.text_label = self.create_label("Text:")
        text_layout.addRow(self.text_label, self.text_edit)

        # === VALUE FONT SUB-SECTION (for circle gauge value display) ===
        self.value_text_group = QGroupBox("Value")
        value_text_layout = QFormLayout(self.value_text_group)
        value_text_layout.setContentsMargins(8, 8, 8, 8)

        self.font_family_combo = NoScrollComboBox()
        self.font_family_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.font_family_combo.setMinimumWidth(50)
        self.font_family_combo.setItemDelegate(FontPreviewDelegate(self.font_family_combo))
        self.font_family_combo.setMaxVisibleItems(15)
        # load_system_fonts() called after label_font_family_combo is created
        self.font_family_combo.currentTextChanged.connect(self.on_property_changed)
        self.font_family_label = self.create_label("Font:")
        value_text_layout.addRow(self.font_family_label, self.font_family_combo)

        self.font_size_spin = NoScrollSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.valueChanged.connect(self.on_property_changed)
        self.font_size_label = self.create_label("Size:")
        value_text_layout.addRow(self.font_size_label, self.font_size_spin)

        font_style_layout = QHBoxLayout()
        self.bold_checkbox = QPushButton("B")
        self.bold_checkbox.setCheckable(True)
        self.bold_checkbox.setFixedWidth(30)
        self.bold_checkbox.setStyleSheet("font-weight: bold;")
        self.bold_checkbox.clicked.connect(self.on_property_changed)
        font_style_layout.addWidget(self.bold_checkbox)

        self.italic_checkbox = QPushButton("I")
        self.italic_checkbox.setCheckable(True)
        self.italic_checkbox.setFixedWidth(30)
        self.italic_checkbox.setStyleSheet("font-style: italic;")
        self.italic_checkbox.clicked.connect(self.on_property_changed)
        font_style_layout.addWidget(self.italic_checkbox)
        font_style_layout.addStretch()

        self.font_style_widget = QWidget()
        self.font_style_widget.setLayout(font_style_layout)
        self.font_style_label = self.create_label("Style:")
        value_text_layout.addRow(self.font_style_label, self.font_style_widget)

        # Value text color (matching Colors pane button style)
        self.value_text_color_btn = QPushButton()
        self.value_text_color_btn.setFixedHeight(26)
        self.value_text_color_btn.clicked.connect(self.choose_value_text_color)
        self.value_text_color_label = self.create_label("Color:")
        value_text_layout.addRow(self.value_text_color_label, self.value_text_color_btn)

        text_layout.addRow(self.value_text_group)

        # === LABEL SUB-SECTION (for circle gauge label) ===
        self.label_text_group = QGroupBox("Label")
        label_text_layout = QFormLayout(self.label_text_group)
        label_text_layout.setContentsMargins(8, 8, 8, 8)

        # Label text input (inside the Label group for circle gauge)
        self.label_text_edit = QLineEdit()
        self.label_text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.label_text_edit.setMinimumWidth(50)
        self.label_text_edit.textChanged.connect(self.on_property_changed)
        self.label_text_input_label = self.create_label("Text:")
        label_text_layout.addRow(self.label_text_input_label, self.label_text_edit)

        self.label_font_family_combo = NoScrollComboBox()
        self.label_font_family_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.label_font_family_combo.setMinimumWidth(50)
        self.label_font_family_combo.setItemDelegate(FontPreviewDelegate(self.label_font_family_combo))
        self.label_font_family_combo.setMaxVisibleItems(15)
        # Now load fonts into both combos
        self.load_system_fonts()
        self.label_font_family_combo.currentTextChanged.connect(self.on_property_changed)
        self.label_font_family_label = self.create_label("Font:")
        label_text_layout.addRow(self.label_font_family_label, self.label_font_family_combo)

        self.label_font_size_spin = NoScrollSpinBox()
        self.label_font_size_spin.setRange(8, 200)
        self.label_font_size_spin.valueChanged.connect(self.on_property_changed)
        self.label_font_size_label = self.create_label("Size:")
        label_text_layout.addRow(self.label_font_size_label, self.label_font_size_spin)

        label_font_style_layout = QHBoxLayout()
        self.label_bold_checkbox = QPushButton("B")
        self.label_bold_checkbox.setCheckable(True)
        self.label_bold_checkbox.setFixedWidth(30)
        self.label_bold_checkbox.setStyleSheet("font-weight: bold;")
        self.label_bold_checkbox.clicked.connect(self.on_property_changed)
        self.label_italic_checkbox = QPushButton("I")
        self.label_italic_checkbox.setCheckable(True)
        self.label_italic_checkbox.setFixedWidth(30)
        self.label_italic_checkbox.setStyleSheet("font-style: italic;")
        self.label_italic_checkbox.clicked.connect(self.on_property_changed)
        label_font_style_layout.addWidget(self.label_bold_checkbox)
        label_font_style_layout.addWidget(self.label_italic_checkbox)
        label_font_style_layout.addStretch()
        self.label_font_style_widget = QWidget()
        self.label_font_style_widget.setLayout(label_font_style_layout)
        self.label_font_style_label = self.create_label("Style:")
        label_text_layout.addRow(self.label_font_style_label, self.label_font_style_widget)

        # Label text color (matching Colors pane button style)
        self.label_text_color_btn = QPushButton()
        self.label_text_color_btn.setFixedHeight(26)
        self.label_text_color_btn.clicked.connect(self.choose_label_text_color)
        self.label_text_color_label = self.create_label("Color:")
        label_text_layout.addRow(self.label_text_color_label, self.label_text_color_btn)

        text_layout.addRow(self.label_text_group)

        # === OTHER TEXT OPTIONS ===
        align_layout = QHBoxLayout()
        self.align_left_btn = QPushButton()
        self.align_left_btn.setIcon(create_alignment_icon('text_left'))
        self.align_left_btn.setCheckable(True)
        self.align_left_btn.setFixedSize(28, 24)
        self.align_left_btn.setToolTip("Align Left")
        self.align_left_btn.clicked.connect(lambda: self.set_alignment("left"))
        align_layout.addWidget(self.align_left_btn)

        self.align_center_btn = QPushButton()
        self.align_center_btn.setIcon(create_alignment_icon('text_center'))
        self.align_center_btn.setCheckable(True)
        self.align_center_btn.setFixedSize(28, 24)
        self.align_center_btn.setToolTip("Align Center")
        self.align_center_btn.clicked.connect(lambda: self.set_alignment("center"))
        align_layout.addWidget(self.align_center_btn)

        self.align_right_btn = QPushButton()
        self.align_right_btn.setIcon(create_alignment_icon('text_right'))
        self.align_right_btn.setCheckable(True)
        self.align_right_btn.setFixedSize(28, 24)
        self.align_right_btn.setToolTip("Align Right")
        self.align_right_btn.clicked.connect(lambda: self.set_alignment("right"))
        align_layout.addWidget(self.align_right_btn)
        align_layout.addStretch()

        self.align_widget = QWidget()
        self.align_widget.setLayout(align_layout)
        self.align_label = self.create_label("Align:")
        text_layout.addRow(self.align_label, self.align_widget)

        self.clip_checkbox = QCheckBox("Clip content to boundary")
        self.clip_checkbox.stateChanged.connect(self.on_property_changed)
        self.clip_label = self.create_label("Clip:")
        text_layout.addRow(self.clip_label, self.clip_checkbox)

        self.section_fields['text'] = [
            (self.bar_text_mode_label, self.bar_text_mode_combo),
            (self.bar_text_position_label, self.bar_text_position_combo),
            (self.text_label, self.text_edit),
            (self.value_text_group, None),
            (self.label_text_group, None),
            (self.align_label, self.align_widget),
            (self.clip_label, self.clip_checkbox)
        ]

        # === DATA SECTION ===
        data_frame, data_layout = self.create_section("Data")
        self.section_headers['data'] = data_frame
        self.props_layout.addWidget(data_frame)

        self.source_combo = NoScrollComboBox()
        self.source_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.source_combo.setMinimumWidth(50)
        self.setup_source_combo()
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        self.source_label = self.create_label("Source:")
        data_layout.addRow(self.source_label, self.source_combo)

        self.value_spin = NoScrollDoubleSpinBox()
        self.value_spin.setRange(0, 100)
        self.value_spin.valueChanged.connect(self.on_property_changed)
        self.value_label = self.create_label("Preview Value:")
        data_layout.addRow(self.value_label, self.value_spin)

        self.section_fields['data'] = [
            (self.source_label, self.source_combo),
            (self.value_label, self.value_spin)
        ]

        # === MEDIA SECTION ===
        media_frame, media_layout = self.create_section("Media")
        self.section_headers['media'] = media_frame
        self.props_layout.addWidget(media_frame)

        self.image_path_edit = QLineEdit()
        self.image_path_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.image_path_edit.setMinimumWidth(50)
        self.image_path_edit.textChanged.connect(self.on_property_changed)
        self.image_browse_btn = QPushButton("...")
        self.image_browse_btn.setFixedWidth(30)
        self.image_browse_btn.clicked.connect(self.browse_image)

        image_layout = QHBoxLayout()
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self.image_path_edit, 1)
        image_layout.addWidget(self.image_browse_btn, 0)

        self.image_widget = QWidget()
        self.image_widget.setLayout(image_layout)
        self.image_label = self.create_label("Image:")
        media_layout.addRow(self.image_label, self.image_widget)

        self.scale_proportionally_check = QCheckBox("Scale Proportionally")
        self.scale_proportionally_check.setToolTip("When enabled, resizing maintains aspect ratio")
        self.scale_proportionally_check.stateChanged.connect(self.on_property_changed)
        self.scale_proportionally_label = QLabel("")
        media_layout.addRow(self.scale_proportionally_label, self.scale_proportionally_check)

        # GIF options
        self.gif_path_edit = QLineEdit()
        self.gif_path_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gif_path_edit.setMinimumWidth(50)
        self.gif_path_edit.textChanged.connect(self.on_property_changed)
        self.gif_browse_btn = QPushButton("...")
        self.gif_browse_btn.setFixedWidth(30)
        self.gif_browse_btn.clicked.connect(self.browse_gif)

        gif_layout = QHBoxLayout()
        gif_layout.setContentsMargins(0, 0, 0, 0)
        gif_layout.addWidget(self.gif_path_edit, 1)
        gif_layout.addWidget(self.gif_browse_btn, 0)

        self.gif_widget = QWidget()
        self.gif_widget.setLayout(gif_layout)
        self.gif_label = self.create_label("GIF:")
        media_layout.addRow(self.gif_label, self.gif_widget)

        self.scale_mode_combo = NoScrollComboBox()
        self.scale_mode_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.scale_mode_combo.setMinimumWidth(50)
        self.scale_mode_combo.addItem("Fit (maintain ratio)", "fit")
        self.scale_mode_combo.addItem("Fill (crop excess)", "fill")
        self.scale_mode_combo.addItem("Stretch", "stretch")
        self.scale_mode_combo.currentIndexChanged.connect(self.on_property_changed)
        self.scale_mode_label = self.create_label("Scale:")
        media_layout.addRow(self.scale_mode_label, self.scale_mode_combo)

        self.section_fields['media'] = [
            (self.image_label, self.image_widget),
            (self.scale_proportionally_label, self.scale_proportionally_check),
            (self.gif_label, self.gif_widget),
            (self.scale_mode_label, self.scale_mode_combo)
        ]

        # === OPTIONS SECTION ===
        options_frame, options_layout = self.create_section("Options")
        self.section_headers['options'] = options_frame
        self.props_layout.addWidget(options_frame)

        # Line chart options
        self.show_background_check = QCheckBox("Show Background")
        self.show_background_check.stateChanged.connect(self.on_property_changed)
        self.show_background_label = QLabel("")
        options_layout.addRow(self.show_background_label, self.show_background_check)

        self.show_label_check = QCheckBox("Show Label")
        self.show_label_check.stateChanged.connect(self.on_property_changed)
        self.show_label_label = QLabel("")
        options_layout.addRow(self.show_label_label, self.show_label_check)

        self.show_gradient_check = QCheckBox("Show Gradient Fill")
        self.show_gradient_check.stateChanged.connect(self.on_property_changed)
        self.show_gradient_label = QLabel("")
        options_layout.addRow(self.show_gradient_label, self.show_gradient_check)

        self.line_thickness_spin = NoScrollSpinBox()
        self.line_thickness_spin.setRange(1, 10)
        self.line_thickness_spin.setValue(2)
        self.line_thickness_spin.valueChanged.connect(self.on_property_changed)
        self.line_thickness_label = self.create_label("Line Thickness:")
        options_layout.addRow(self.line_thickness_label, self.line_thickness_spin)

        self.smooth_check = QCheckBox("Smooth Line")
        self.smooth_check.setToolTip("Enable smooth curve interpolation instead of jagged lines")
        self.smooth_check.stateChanged.connect(self.on_property_changed)
        self.smooth_label = QLabel("")
        options_layout.addRow(self.smooth_label, self.smooth_check)

        # Bar gauge - Rounded corners option
        self.rounded_corners_check = QCheckBox("Rounded Corners")
        self.rounded_corners_check.stateChanged.connect(self.on_property_changed)
        self.rounded_corners_label = QLabel("")
        options_layout.addRow(self.rounded_corners_label, self.rounded_corners_check)

        # Circle gauge - Rounded arc ends option
        self.gauge_rounded_ends_check = QCheckBox("Rounded Arc Ends")
        self.gauge_rounded_ends_check.setToolTip("Draw pill-shaped rounded ends on the gauge arc")
        self.gauge_rounded_ends_check.stateChanged.connect(self.on_property_changed)
        self.gauge_rounded_ends_label = QLabel("")
        options_layout.addRow(self.gauge_rounded_ends_label, self.gauge_rounded_ends_check)

        # Gauge options - Smooth transitions
        self.animate_gauge_check = QCheckBox("Smooth Transitions")
        self.animate_gauge_check.setToolTip("Smoothly animate gauge transitions when values change")
        self.animate_gauge_check.stateChanged.connect(self.on_property_changed)
        self.animate_gauge_label = QLabel("")
        options_layout.addRow(self.animate_gauge_label, self.animate_gauge_check)

        # Gauge options - Auto color change
        self.auto_color_change_check = QCheckBox("Auto Color (warn/critical)")
        self.auto_color_change_check.setToolTip("Automatically change color at warning (70%) and critical (90%) thresholds")
        self.auto_color_change_check.stateChanged.connect(self.on_property_changed)
        self.auto_color_change_label = QLabel("")
        options_layout.addRow(self.auto_color_change_label, self.auto_color_change_check)

        # Temperature display option
        self.temp_hide_unit_check = QCheckBox("Hide unit letter (show ° only)")
        self.temp_hide_unit_check.setToolTip("Show 45° instead of 45°C for temperature")
        self.temp_hide_unit_check.stateChanged.connect(self.on_property_changed)
        self.temp_hide_unit_label = QLabel("")
        options_layout.addRow(self.temp_hide_unit_label, self.temp_hide_unit_check)

        # Digital clock time format options
        self.time_format_combo = NoScrollComboBox()
        self.time_format_combo.addItem("24-Hour (Military)", "24h")
        self.time_format_combo.addItem("12-Hour (Standard)", "12h")
        self.time_format_combo.currentIndexChanged.connect(self.on_property_changed)
        self.time_format_label = self.create_label("Time Format:")
        options_layout.addRow(self.time_format_label, self.time_format_combo)

        self.show_am_pm_check = QCheckBox("Show AM/PM")
        self.show_am_pm_check.stateChanged.connect(self.on_property_changed)
        self.show_am_pm_label = QLabel("")
        options_layout.addRow(self.show_am_pm_label, self.show_am_pm_check)

        self.show_seconds_check = QCheckBox("Show Seconds")
        self.show_seconds_check.stateChanged.connect(self.on_property_changed)
        self.show_seconds_label = QLabel("")
        options_layout.addRow(self.show_seconds_label, self.show_seconds_check)

        self.show_leading_zero_check = QCheckBox("Show Leading Zero (09 vs 9)")
        self.show_leading_zero_check.stateChanged.connect(self.on_property_changed)
        self.show_leading_zero_label = QLabel("")
        options_layout.addRow(self.show_leading_zero_label, self.show_leading_zero_check)

        # Analog clock options
        self.show_seconds_hand_check = QCheckBox("Show Seconds Hand")
        self.show_seconds_hand_check.stateChanged.connect(self.on_property_changed)
        self.show_seconds_hand_label = QLabel("")
        options_layout.addRow(self.show_seconds_hand_label, self.show_seconds_hand_check)

        self.show_clock_border_check = QCheckBox("Show Clock Border")
        self.show_clock_border_check.stateChanged.connect(self.on_property_changed)
        self.show_clock_border_label = QLabel("")
        options_layout.addRow(self.show_clock_border_label, self.show_clock_border_check)

        self.clock_face_style_combo = NoScrollComboBox()
        self.clock_face_style_combo.addItem("Numbers (1-12)", "numbers")
        self.clock_face_style_combo.addItem("Tick Marks", "ticks")
        self.clock_face_style_combo.addItem("None", "none")
        self.clock_face_style_combo.currentIndexChanged.connect(self.on_property_changed)
        self.clock_face_style_label = self.create_label("Face Style:")
        options_layout.addRow(self.clock_face_style_label, self.clock_face_style_combo)

        self.smooth_animation_check = QCheckBox("Smooth Animation")
        self.smooth_animation_check.stateChanged.connect(self.on_property_changed)
        self.smooth_animation_label = QLabel("")
        options_layout.addRow(self.smooth_animation_label, self.smooth_animation_check)

        self.section_fields['options'] = [
            (self.show_background_label, self.show_background_check),
            (self.show_label_label, self.show_label_check),
            (self.show_gradient_label, self.show_gradient_check),
            (self.line_thickness_label, self.line_thickness_spin),
            (self.smooth_label, self.smooth_check),
            (self.rounded_corners_label, self.rounded_corners_check),
            (self.gauge_rounded_ends_label, self.gauge_rounded_ends_check),
            (self.animate_gauge_label, self.animate_gauge_check),
            (self.auto_color_change_label, self.auto_color_change_check),
            (self.temp_hide_unit_label, self.temp_hide_unit_check),
            (self.time_format_label, self.time_format_combo),
            (self.show_am_pm_label, self.show_am_pm_check),
            (self.show_seconds_label, self.show_seconds_check),
            (self.show_leading_zero_label, self.show_leading_zero_check),
            (self.show_seconds_hand_label, self.show_seconds_hand_check),
            (self.show_clock_border_label, self.show_clock_border_check),
            (self.clock_face_style_label, self.clock_face_style_combo),
            (self.smooth_animation_label, self.smooth_animation_check)
        ]

        # Add stretch at the end to push sections to top
        self.props_layout.addStretch()

        scroll.setWidget(self.props_widget)
        layout.addWidget(scroll)

        # Multi-selection panel with scroll area
        self.multi_scroll = QScrollArea()
        self.multi_scroll.setWidgetResizable(True)
        self.multi_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.multi_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.multi_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.multi_scroll.setMaximumWidth(320)

        self.multi_widget = QWidget()
        self.multi_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.multi_widget.setMaximumWidth(310)
        self.multi_layout = QVBoxLayout(self.multi_widget)
        self.multi_layout.setSpacing(8)
        self.multi_layout.setContentsMargins(4, 4, 4, 4)

        # === MULTI-SELECTION GENERAL SECTION ===
        self.multi_general_frame, multi_general_layout = self.create_section("General")
        self.multi_layout.addWidget(self.multi_general_frame)

        self.multi_name_label = self.create_label("Selection:")
        self.multi_name_value = QLabel("0 elements")
        self.multi_name_value.setStyleSheet("color: #0096ff; font-weight: bold;")
        self.multi_name_value.setMaximumWidth(200)
        multi_general_layout.addRow(self.multi_name_label, self.multi_name_value)

        self.group_name_edit = QLineEdit()
        self.group_name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.group_name_edit.setMinimumWidth(50)
        self.group_name_edit.setMaximumWidth(200)
        self.group_name_edit.setPlaceholderText("Group name")
        self.group_name_edit.textChanged.connect(self.on_group_name_changed)
        self.group_name_label = self.create_label("Group:")
        multi_general_layout.addRow(self.group_name_label, self.group_name_edit)

        # === MULTI-SELECTION TRANSFORM SECTION ===
        self.multi_transform_frame, multi_transform_layout = self.create_section("Transform")
        self.multi_layout.addWidget(self.multi_transform_frame)

        # Position row (X and Y side by side)
        multi_position_layout = QHBoxLayout()
        multi_position_layout.setSpacing(8)

        self.multi_x_spin = NoScrollSpinBox()
        self.multi_x_spin.setRange(-1000, constants.DISPLAY_WIDTH + 1000)
        self.multi_x_spin.valueChanged.connect(self.on_multi_transform_changed)
        multi_x_container = QHBoxLayout()
        multi_x_container.setSpacing(4)
        multi_x_label = QLabel("X:")
        multi_x_container.addWidget(multi_x_label)
        multi_x_container.addWidget(self.multi_x_spin)
        multi_position_layout.addLayout(multi_x_container)

        self.multi_y_spin = NoScrollSpinBox()
        self.multi_y_spin.setRange(-1000, constants.DISPLAY_HEIGHT + 1000)
        self.multi_y_spin.valueChanged.connect(self.on_multi_transform_changed)
        multi_y_container = QHBoxLayout()
        multi_y_container.setSpacing(4)
        multi_y_label = QLabel("Y:")
        multi_y_container.addWidget(multi_y_label)
        multi_y_container.addWidget(self.multi_y_spin)
        multi_position_layout.addLayout(multi_y_container)

        multi_position_widget = QWidget()
        multi_position_widget.setLayout(multi_position_layout)
        multi_transform_layout.addRow(QLabel("Position:"), multi_position_widget)

        # Size row (Width and Height side by side)
        multi_size_layout = QHBoxLayout()
        multi_size_layout.setSpacing(8)

        self.multi_w_spin = NoScrollSpinBox()
        self.multi_w_spin.setRange(1, constants.DISPLAY_WIDTH * 2)
        self.multi_w_spin.valueChanged.connect(self.on_multi_size_changed)
        multi_w_container = QHBoxLayout()
        multi_w_container.setSpacing(4)
        multi_w_label = QLabel("W:")
        multi_w_container.addWidget(multi_w_label)
        multi_w_container.addWidget(self.multi_w_spin)
        multi_size_layout.addLayout(multi_w_container)

        self.multi_h_spin = NoScrollSpinBox()
        self.multi_h_spin.setRange(1, constants.DISPLAY_HEIGHT * 2)
        self.multi_h_spin.valueChanged.connect(self.on_multi_size_changed)
        multi_h_container = QHBoxLayout()
        multi_h_container.setSpacing(4)
        multi_h_label = QLabel("H:")
        multi_h_container.addWidget(multi_h_label)
        multi_h_container.addWidget(self.multi_h_spin)
        multi_size_layout.addLayout(multi_h_container)

        multi_size_widget = QWidget()
        multi_size_widget.setLayout(multi_size_layout)
        self.multi_size_label = self.create_label("Size:")
        multi_transform_layout.addRow(self.multi_size_label, multi_size_widget)

        # === ALIGNMENT SECTION ===
        self.alignment_frame, alignment_layout = self.create_section("Alignment")
        self.multi_layout.addWidget(self.alignment_frame)

        # Horizontal alignment
        h_align_layout = QHBoxLayout()
        self.align_h_left_btn = QPushButton()
        self.align_h_left_btn.setIcon(create_alignment_icon('h_left'))
        self.align_h_left_btn.setFixedSize(32, 26)
        self.align_h_left_btn.setToolTip("Align Left Edges")
        self.align_h_left_btn.clicked.connect(self.align_left)
        h_align_layout.addWidget(self.align_h_left_btn)

        self.align_h_center_btn = QPushButton()
        self.align_h_center_btn.setIcon(create_alignment_icon('h_center'))
        self.align_h_center_btn.setFixedSize(32, 26)
        self.align_h_center_btn.setToolTip("Align Horizontal Centers")
        self.align_h_center_btn.clicked.connect(self.align_h_center)
        h_align_layout.addWidget(self.align_h_center_btn)

        self.align_h_right_btn = QPushButton()
        self.align_h_right_btn.setIcon(create_alignment_icon('h_right'))
        self.align_h_right_btn.setFixedSize(32, 26)
        self.align_h_right_btn.setToolTip("Align Right Edges")
        self.align_h_right_btn.clicked.connect(self.align_right)
        h_align_layout.addWidget(self.align_h_right_btn)
        h_align_layout.addStretch()

        h_align_widget = QWidget()
        h_align_widget.setLayout(h_align_layout)
        alignment_layout.addRow(QLabel("Horizontal:"), h_align_widget)

        # Vertical alignment
        v_align_layout = QHBoxLayout()
        self.align_v_top_btn = QPushButton()
        self.align_v_top_btn.setIcon(create_alignment_icon('v_top'))
        self.align_v_top_btn.setFixedSize(32, 26)
        self.align_v_top_btn.setToolTip("Align Top Edges")
        self.align_v_top_btn.clicked.connect(self.align_top)
        v_align_layout.addWidget(self.align_v_top_btn)

        self.align_v_middle_btn = QPushButton()
        self.align_v_middle_btn.setIcon(create_alignment_icon('v_middle'))
        self.align_v_middle_btn.setFixedSize(32, 26)
        self.align_v_middle_btn.setToolTip("Align Vertical Centers")
        self.align_v_middle_btn.clicked.connect(self.align_v_middle)
        v_align_layout.addWidget(self.align_v_middle_btn)

        self.align_v_bottom_btn = QPushButton()
        self.align_v_bottom_btn.setIcon(create_alignment_icon('v_bottom'))
        self.align_v_bottom_btn.setFixedSize(32, 26)
        self.align_v_bottom_btn.setToolTip("Align Bottom Edges")
        self.align_v_bottom_btn.clicked.connect(self.align_bottom)
        v_align_layout.addWidget(self.align_v_bottom_btn)
        v_align_layout.addStretch()

        v_align_widget = QWidget()
        v_align_widget.setLayout(v_align_layout)
        alignment_layout.addRow(QLabel("Vertical:"), v_align_widget)

        # Distribution
        dist_layout = QHBoxLayout()
        self.dist_h_btn = QPushButton()
        self.dist_h_btn.setIcon(create_alignment_icon('dist_h'))
        self.dist_h_btn.setFixedSize(32, 26)
        self.dist_h_btn.setToolTip("Distribute Horizontally")
        self.dist_h_btn.clicked.connect(self.distribute_horizontal)
        dist_layout.addWidget(self.dist_h_btn)

        self.dist_v_btn = QPushButton()
        self.dist_v_btn.setIcon(create_alignment_icon('dist_v'))
        self.dist_v_btn.setFixedSize(32, 26)
        self.dist_v_btn.setToolTip("Distribute Vertically")
        self.dist_v_btn.clicked.connect(self.distribute_vertical)
        dist_layout.addWidget(self.dist_v_btn)

        dist_widget = QWidget()
        dist_widget.setLayout(dist_layout)
        alignment_layout.addRow(QLabel("Distribute:"), dist_widget)

        self.multi_layout.addStretch()
        self.multi_scroll.setWidget(self.multi_widget)
        layout.addWidget(self.multi_scroll)
        self.multi_scroll.setVisible(False)

        # Keep old reference for compatibility
        self.alignment_widget = self.multi_scroll

        # Initial state: show helper text, hide properties
        self.no_selection_container.setVisible(True)
        self.scroll_area.setVisible(False)

    def load_system_fonts(self):
        font_db = QFontDatabase()
        families = font_db.families()

        common_fonts = ["Arial", "Segoe UI", "Tahoma", "Verdana", "Times New Roman",
                        "Calibri", "Consolas", "Courier New", "Georgia", "Impact"]

        added = set()
        for font in common_fonts:
            if font in families:
                self.font_family_combo.addItem(font)
                self.label_font_family_combo.addItem(font)
                added.add(font)

        self.font_family_combo.insertSeparator(len(added))
        self.label_font_family_combo.insertSeparator(len(added))

        for family in sorted(families):
            if family not in added and not family.startswith("@"):
                self.font_family_combo.addItem(family)
                self.label_font_family_combo.addItem(family)

    def setup_source_combo(self):
        """Setup the source combo box with categorized items."""
        self.source_combo.clear()

        for category, sources in DATA_SOURCES_CATEGORIZED.items():
            # Add category header (disabled, styled differently)
            self.source_combo.addItem(f"── {category} ──")
            idx = self.source_combo.count() - 1
            # Make header item non-selectable
            self.source_combo.model().item(idx).setEnabled(False)

            # Add sources in this category
            for source_info in sources:
                source_id, source_name, unit_type, unit_symbol = source_info
                # Don't show unit symbol for static value
                if source_id == "static":
                    self.source_combo.addItem(f"    {source_name}")
                else:
                    self.source_combo.addItem(f"    {source_name} ({unit_symbol})")
                idx = self.source_combo.count() - 1
                # Store the actual source ID in item data
                self.source_combo.setItemData(idx, source_id, Qt.ItemDataRole.UserRole)

    def get_selected_source(self):
        """Get the currently selected source ID."""
        idx = self.source_combo.currentIndex()
        source_id = self.source_combo.itemData(idx, Qt.ItemDataRole.UserRole)
        return source_id if source_id else "static"

    def set_source_by_id(self, source_id):
        """Set the combo box selection by source ID."""
        for i in range(self.source_combo.count()):
            if self.source_combo.itemData(i, Qt.ItemDataRole.UserRole) == source_id:
                self.source_combo.setCurrentIndex(i)
                return
        # Fallback to static if not found
        self.set_source_by_id("static")

    def on_source_changed(self, index):
        """Handle source combo box selection change."""
        # Skip if header item selected (find next valid item)
        source_id = self.source_combo.itemData(index, Qt.ItemDataRole.UserRole)
        if source_id is None:
            # Find next valid item
            for i in range(index + 1, self.source_combo.count()):
                if self.source_combo.itemData(i, Qt.ItemDataRole.UserRole):
                    self.source_combo.setCurrentIndex(i)
                    return
            return

        # Update preview value visibility based on whether source is static
        is_static = source_id == "static"
        self.value_label.setVisible(is_static and self.value_label.parent().isVisible())
        self.value_spin.setVisible(is_static and self.value_spin.parent().isVisible())

        if self.current_element:
            if self.current_element.locked:
                return
            if not self._undo_state_saved:
                self.property_will_change.emit()
                self._undo_state_saved = True
            self.current_element.source = source_id
            self.property_changed.emit()

    def set_alignment(self, align):
        self.align_left_btn.blockSignals(True)
        self.align_center_btn.blockSignals(True)
        self.align_right_btn.blockSignals(True)

        self.align_left_btn.setChecked(align == "left")
        self.align_center_btn.setChecked(align == "center")
        self.align_right_btn.setChecked(align == "right")

        self.align_left_btn.blockSignals(False)
        self.align_center_btn.blockSignals(False)
        self.align_right_btn.blockSignals(False)

        self.on_property_changed()

    def update_visible_fields(self, element_type):
        field_visibility = {
            "circle_gauge": {
                "width": False, "height": False, "radius": True,
                "color": True, "bg_color": True, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "value_text_group": True, "label_text_group": True,
                "align": False, "clip": False, "source": True, "value": True, "image": False,
                "auto_color_change": True, "animate_gauge": True, "gauge_rounded_ends": True
            },
            "text": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": False, "text": True,
                "font": False, "font_size": False, "font_style": False,
                "value_text_group": True, "label_text_group": False,
                "align": True, "clip": True, "source": True, "value": True, "image": False
            },
            "clock": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": False, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "value_text_group": True, "label_text_group": False,
                "align": True, "clip": True, "source": False, "value": False, "image": False,
                "time_format": True, "show_am_pm": True, "show_seconds": True, "show_leading_zero": True
            },
            "rectangle": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": False, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "align": False, "clip": False, "source": False, "value": False, "image": False,
                "border_radius": True, "glass_effect": True
            },
            "image": {
                "width": True, "height": True, "radius": False,
                "color": False, "bg_color": False, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "align": False, "clip": False, "source": False, "value": False, "image": True
            },
            "gif": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": False, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "align": False, "clip": False, "source": False, "value": False, "image": False,
                "gif": True, "scale_mode": True
            },
            "line_chart": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": True, "text": True,
                "font": False, "font_size": False, "font_style": False,
                "value_text_group": True, "label_text_group": False,
                "align": False, "clip": False, "source": True, "value": True, "image": False,
                "show_background": True, "show_label": True, "show_gradient": True,
                "rounded_corners": False, "gradient_fill": False,
                "line_thickness": True, "smooth": True
            },
            "bar_gauge": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": True, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "value_text_group": True, "label_text_group": True,
                "align": False, "clip": False, "source": True, "value": True, "image": False,
                "show_background": False, "show_label": False, "show_gradient": False,
                "rounded_corners": True, "gradient_fill": True,
                "auto_color_change": True, "animate_gauge": True,
                "bar_text_mode": True, "bar_text_position": True,
                "bar_border": True
            },
            "analog_clock": {
                "width": False, "height": False, "radius": True,
                "color": True, "bg_color": True, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "value_text_group": True, "label_text_group": False,
                "align": False, "clip": False, "source": False, "value": False, "image": False,
                "show_seconds_hand": True, "show_clock_border": True,
                "clock_face_style": True, "smooth_animation": True
            }
        }

        visibility = field_visibility.get(element_type, {})

        # Track visibility for each section
        section_visible = {section: False for section in self.section_headers}

        # General section - always visible (name is always shown)
        section_visible['general'] = True

        # Transform section
        width_visible = visibility.get("width", True)
        height_visible = visibility.get("height", True)
        radius_visible = visibility.get("radius", False)

        # Size row shows if either width or height is visible
        size_visible = width_visible or height_visible
        self.size_label.setVisible(size_visible)
        self.size_widget.setVisible(size_visible)

        self.radius_label.setVisible(radius_visible)
        self.radius_spin.setVisible(radius_visible)

        # Position (X/Y) is always visible in transform
        section_visible['transform'] = True

        # Colors section
        color_visible = visibility.get("color", True)
        bg_color_visible = visibility.get("bg_color", False)

        # Gradient fill option is only for bar_gauge and circle_gauge
        gradient_fill_visible = element_type in ["bar_gauge", "circle_gauge"]
        use_gradient = gradient_fill_visible and self.gradient_fill_check.isChecked()

        # Batch visibility updates to prevent flicker
        self.setUpdatesEnabled(False)

        # Show color button only when not using gradient fill
        self.color_label.setVisible(color_visible and not use_gradient)
        self.color_btn.setVisible(color_visible and not use_gradient)
        self.bg_color_label.setVisible(bg_color_visible)
        self.bg_color_btn.setVisible(bg_color_visible)

        # Gradient fill checkbox and preview
        self.gradient_fill_label.setVisible(gradient_fill_visible)
        self.gradient_fill_check.setVisible(gradient_fill_visible)
        self.gradient_preview_label.setVisible(use_gradient)
        self.gradient_preview.setVisible(use_gradient)

        self.setUpdatesEnabled(True)

        section_visible['colors'] = color_visible or bg_color_visible or gradient_fill_visible

        # Appearance section
        border_radius_visible = visibility.get("border_radius", False)
        glass_visible = visibility.get("glass_effect", False)

        self.border_radius_label.setVisible(border_radius_visible)
        self.border_radius_spin.setVisible(border_radius_visible)
        self.glass_effect_label.setVisible(glass_visible)
        self.glass_effect_check.setVisible(glass_visible)
        self.glass_blur_label.setVisible(glass_visible)
        self.glass_blur_spin.setVisible(glass_visible)
        self.glass_opacity_label.setVisible(glass_visible)
        self.glass_opacity_spin.setVisible(glass_visible)

        section_visible['appearance'] = border_radius_visible or glass_visible

        # Text section
        text_visible = visibility.get("text", True)
        font_visible = visibility.get("font", True)
        font_size_visible = visibility.get("font_size", True)
        font_style_visible = visibility.get("font_style", True)
        value_text_group_visible = visibility.get("value_text_group", False)
        label_text_group_visible = visibility.get("label_text_group", False)
        align_visible = visibility.get("align", False)
        clip_visible = visibility.get("clip", False)
        bar_text_mode_visible = visibility.get("bar_text_mode", False)
        bar_text_position_visible = visibility.get("bar_text_position", False)

        # Bar gauge text display/position options (at top of text section)
        self.bar_text_mode_label.setVisible(bar_text_mode_visible)
        self.bar_text_mode_combo.setVisible(bar_text_mode_visible)
        self.bar_text_position_label.setVisible(bar_text_position_visible)
        self.bar_text_position_combo.setVisible(bar_text_position_visible)

        self.text_label.setVisible(text_visible)
        self.text_edit.setVisible(text_visible)
        self.value_text_group.setVisible(value_text_group_visible)
        # Only show as sub-pane (with border/title) when label group is also visible
        # For text/clock/line_chart, show controls directly without the group box styling
        if value_text_group_visible and not label_text_group_visible:
            self.value_text_group.setFlat(True)
            self.value_text_group.setTitle("")
            self.value_text_group.setStyleSheet("QGroupBox { border: none; margin: 0; padding: 0; }")
            self.value_text_group.layout().setContentsMargins(0, 0, 0, 0)
        else:
            self.value_text_group.setFlat(False)
            self.value_text_group.setTitle("Value")
            self.value_text_group.setStyleSheet("")
            self.value_text_group.layout().setContentsMargins(8, 8, 8, 8)
        self.label_text_group.setVisible(label_text_group_visible)

        # Show all label options for both circle_gauge and bar_gauge
        self.label_text_input_label.setVisible(label_text_group_visible)
        self.label_text_edit.setVisible(label_text_group_visible)
        self.label_font_family_label.setVisible(label_text_group_visible)
        self.label_font_family_combo.setVisible(label_text_group_visible)

        # Show font controls when standalone OR inside value_text_group
        show_standalone_font = font_visible and not value_text_group_visible
        show_font_controls = show_standalone_font or value_text_group_visible
        self.font_family_label.setVisible(show_font_controls)
        self.font_family_combo.setVisible(show_font_controls)
        self.font_size_label.setVisible(show_font_controls)
        self.font_size_spin.setVisible(show_font_controls)
        self.font_style_label.setVisible(show_font_controls)
        self.font_style_widget.setVisible(show_font_controls)
        self.align_label.setVisible(align_visible)
        self.align_widget.setVisible(align_visible)
        self.clip_label.setVisible(clip_visible)
        self.clip_checkbox.setVisible(clip_visible)

        section_visible['text'] = (text_visible or font_visible or font_size_visible or
                                   font_style_visible or value_text_group_visible or
                                   label_text_group_visible or align_visible or clip_visible or
                                   bar_text_mode_visible or bar_text_position_visible)

        # Data section
        source_visible = visibility.get("source", False)
        value_visible = visibility.get("value", False)
        # Preview value only shown when source is "static"
        is_static = self.get_selected_source() == "static" if self.current_element else True
        show_preview_value = value_visible and is_static

        self.source_label.setVisible(source_visible)
        self.source_combo.setVisible(source_visible)
        self.value_label.setVisible(show_preview_value)
        self.value_spin.setVisible(show_preview_value)

        section_visible['data'] = source_visible or show_preview_value

        # Media section
        image_visible = visibility.get("image", False)
        gif_visible = visibility.get("gif", False)
        scale_mode_visible = visibility.get("scale_mode", False)

        self.image_label.setVisible(image_visible)
        self.image_widget.setVisible(image_visible)
        self.scale_proportionally_label.setVisible(image_visible)
        self.scale_proportionally_check.setVisible(image_visible)
        self.gif_label.setVisible(gif_visible)
        self.gif_widget.setVisible(gif_visible)
        self.scale_mode_label.setVisible(scale_mode_visible)
        self.scale_mode_combo.setVisible(scale_mode_visible)

        section_visible['media'] = image_visible or gif_visible or scale_mode_visible

        # Options section - element-specific options
        show_background_visible = visibility.get("show_background", False)
        show_label_visible = visibility.get("show_label", False)
        show_gradient_visible = visibility.get("show_gradient", False)
        line_thickness_visible = visibility.get("line_thickness", False)
        smooth_visible = visibility.get("smooth", False)
        rounded_corners_visible = visibility.get("rounded_corners", False)
        auto_color_change_visible = visibility.get("auto_color_change", False)
        animate_gauge_visible = visibility.get("animate_gauge", False)
        gauge_rounded_ends_visible = visibility.get("gauge_rounded_ends", False)
        time_format_visible = visibility.get("time_format", False)
        show_am_pm_visible = visibility.get("show_am_pm", False)
        show_seconds_visible = visibility.get("show_seconds", False)
        show_leading_zero_visible = visibility.get("show_leading_zero", False)
        show_seconds_hand_visible = visibility.get("show_seconds_hand", False)
        show_clock_border_visible = visibility.get("show_clock_border", False)
        clock_face_style_visible = visibility.get("clock_face_style", False)
        smooth_animation_visible = visibility.get("smooth_animation", False)

        self.show_background_label.setVisible(show_background_visible)
        self.show_background_check.setVisible(show_background_visible)
        self.show_label_label.setVisible(show_label_visible)
        self.show_label_check.setVisible(show_label_visible)
        self.show_gradient_label.setVisible(show_gradient_visible)
        self.show_gradient_check.setVisible(show_gradient_visible)
        self.line_thickness_label.setVisible(line_thickness_visible)
        self.line_thickness_spin.setVisible(line_thickness_visible)
        self.smooth_label.setVisible(smooth_visible)
        self.smooth_check.setVisible(smooth_visible)
        self.rounded_corners_label.setVisible(rounded_corners_visible)
        self.rounded_corners_check.setVisible(rounded_corners_visible)

        # Bar border options - visible for bar gauge, sub-options depend on checkbox
        bar_border_visible = visibility.get("bar_border", False)
        bar_border_enabled = self.bar_border_check.isChecked() if bar_border_visible else False
        self.bar_border_label.setVisible(bar_border_visible)
        self.bar_border_check.setVisible(bar_border_visible)
        self.bar_border_group.setVisible(bar_border_visible and bar_border_enabled)

        # Temperature hide unit option - visible only for temperature sources
        temp_sources = ["cpu_temp", "gpu_temp"]
        current_source = getattr(self.current_element, 'source', 'static') if self.current_element else 'static'
        temp_hide_unit_visible = current_source in temp_sources
        self.temp_hide_unit_label.setVisible(temp_hide_unit_visible)
        self.temp_hide_unit_check.setVisible(temp_hide_unit_visible)

        self.auto_color_change_label.setVisible(auto_color_change_visible)
        self.auto_color_change_check.setVisible(auto_color_change_visible)
        self.animate_gauge_label.setVisible(animate_gauge_visible)
        self.animate_gauge_check.setVisible(animate_gauge_visible)
        self.gauge_rounded_ends_label.setVisible(gauge_rounded_ends_visible)
        self.gauge_rounded_ends_check.setVisible(gauge_rounded_ends_visible)
        self.time_format_label.setVisible(time_format_visible)
        self.time_format_combo.setVisible(time_format_visible)
        self.show_am_pm_label.setVisible(show_am_pm_visible)
        self.show_am_pm_check.setVisible(show_am_pm_visible)
        self.show_seconds_label.setVisible(show_seconds_visible)
        self.show_seconds_check.setVisible(show_seconds_visible)
        self.show_leading_zero_label.setVisible(show_leading_zero_visible)
        self.show_leading_zero_check.setVisible(show_leading_zero_visible)
        self.show_seconds_hand_label.setVisible(show_seconds_hand_visible)
        self.show_seconds_hand_check.setVisible(show_seconds_hand_visible)
        self.show_clock_border_label.setVisible(show_clock_border_visible)
        self.show_clock_border_check.setVisible(show_clock_border_visible)
        self.clock_face_style_label.setVisible(clock_face_style_visible)
        self.clock_face_style_combo.setVisible(clock_face_style_visible)
        self.smooth_animation_label.setVisible(smooth_animation_visible)
        self.smooth_animation_check.setVisible(smooth_animation_visible)

        section_visible['options'] = (show_background_visible or show_label_visible or
                                      show_gradient_visible or line_thickness_visible or
                                      smooth_visible or rounded_corners_visible or
                                      temp_hide_unit_visible or auto_color_change_visible or
                                      animate_gauge_visible or gauge_rounded_ends_visible or
                                      time_format_visible or
                                      show_am_pm_visible or show_seconds_visible or
                                      show_leading_zero_visible or show_seconds_hand_visible or
                                      show_clock_border_visible or clock_face_style_visible or
                                      smooth_animation_visible)

        # Update section header visibility
        for section, header in self.section_headers.items():
            header.setVisible(section_visible.get(section, False))

    def set_element(self, element):
        self.current_element = None
        self.multi_selection_elements = []
        self.multi_selection_indices = []

        # Batch visibility updates to prevent flicker
        self.setUpdatesEnabled(False)

        if element is None:
            self.no_selection_container.setVisible(True)
            self.scroll_area.setVisible(False)
            self.alignment_widget.setVisible(False)
            self.setUpdatesEnabled(True)
            return

        self.no_selection_container.setVisible(False)
        self.scroll_area.setVisible(True)
        self.alignment_widget.setVisible(False)

        self.setUpdatesEnabled(True)

        self.update_visible_fields(element.type)

        self.name_edit.blockSignals(True)
        self.x_spin.blockSignals(True)
        self.y_spin.blockSignals(True)
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.border_radius_spin.blockSignals(True)
        self.glass_effect_check.blockSignals(True)
        self.glass_blur_spin.blockSignals(True)
        self.glass_opacity_spin.blockSignals(True)
        self.radius_spin.blockSignals(True)
        self.text_edit.blockSignals(True)
        self.label_text_edit.blockSignals(True)
        self.font_family_combo.blockSignals(True)
        self.font_size_spin.blockSignals(True)
        self.bold_checkbox.blockSignals(True)
        self.italic_checkbox.blockSignals(True)
        self.align_left_btn.blockSignals(True)
        self.align_center_btn.blockSignals(True)
        self.align_right_btn.blockSignals(True)
        self.clip_checkbox.blockSignals(True)
        self.source_combo.blockSignals(True)
        self.value_spin.blockSignals(True)
        self.image_path_edit.blockSignals(True)
        self.scale_proportionally_check.blockSignals(True)
        self.show_background_check.blockSignals(True)
        self.show_label_check.blockSignals(True)
        self.show_gradient_check.blockSignals(True)
        self.line_thickness_spin.blockSignals(True)
        self.smooth_check.blockSignals(True)
        self.rounded_corners_check.blockSignals(True)
        self.bar_border_check.blockSignals(True)
        self.bar_border_width_spin.blockSignals(True)
        self.bar_border_position_combo.blockSignals(True)
        self.gradient_fill_check.blockSignals(True)
        self.auto_color_change_check.blockSignals(True)
        self.animate_gauge_check.blockSignals(True)
        self.gauge_rounded_ends_check.blockSignals(True)
        self.label_font_size_spin.blockSignals(True)
        self.label_font_family_combo.blockSignals(True)
        self.label_bold_checkbox.blockSignals(True)
        self.label_italic_checkbox.blockSignals(True)
        self.temp_hide_unit_check.blockSignals(True)
        self.gif_path_edit.blockSignals(True)
        self.scale_mode_combo.blockSignals(True)
        self.bar_text_mode_combo.blockSignals(True)
        self.bar_text_position_combo.blockSignals(True)
        self.time_format_combo.blockSignals(True)
        self.show_am_pm_check.blockSignals(True)
        self.show_seconds_check.blockSignals(True)
        self.show_leading_zero_check.blockSignals(True)
        self.show_seconds_hand_check.blockSignals(True)
        self.show_clock_border_check.blockSignals(True)
        self.clock_face_style_combo.blockSignals(True)
        self.smooth_animation_check.blockSignals(True)

        self.name_edit.setText(element.name)
        self.x_spin.setValue(element.x)
        self.y_spin.setValue(element.y)
        self.width_spin.setValue(element.width)
        self.height_spin.setValue(element.height)
        self.border_radius_spin.setValue(getattr(element, 'border_radius', 0))
        self.glass_effect_check.setChecked(getattr(element, 'glass_effect', False))
        self.glass_blur_spin.setValue(getattr(element, 'glass_blur', 10))
        self.glass_opacity_spin.setValue(getattr(element, 'glass_opacity', 50))
        self.radius_spin.setValue(element.radius)
        self.text_edit.setText(element.text)
        self.label_text_edit.setText(element.text)  # For circle gauge label
        self.font_size_spin.setValue(element.font_size)
        self.value_spin.setValue(element.value)
        self.image_path_edit.setText(element.image_path)
        self.clip_checkbox.setChecked(element.clip)
        self.scale_proportionally_check.setChecked(element.scale_proportionally)
        self.show_background_check.setChecked(element.show_background)
        self.show_label_check.setChecked(element.show_label)
        self.show_gradient_check.setChecked(element.show_gradient)
        self.line_thickness_spin.setValue(getattr(element, 'line_thickness', 2))
        self.smooth_check.setChecked(getattr(element, 'smooth', False))
        self.rounded_corners_check.setChecked(element.rounded_corners)
        # Load bar border settings
        self.bar_border_check.setChecked(getattr(element, 'bar_border', False))
        self.bar_border_width_spin.setValue(getattr(element, 'bar_border_width', 2))
        bar_border_color = getattr(element, 'bar_border_color', '#ffffff')
        self.bar_border_color_btn.setStyleSheet(f"background-color: {bar_border_color};")
        # Load border position
        border_position = getattr(element, 'bar_border_position', 'center')
        pos_idx = self.bar_border_position_combo.findData(border_position)
        if pos_idx >= 0:
            self.bar_border_position_combo.setCurrentIndex(pos_idx)
        # Show/hide group based on checkbox
        self.bar_border_group.setVisible(getattr(element, 'bar_border', False))
        self.gradient_fill_check.setChecked(element.gradient_fill)
        # Load gradient stops
        gradient_stops = getattr(element, 'gradient_stops', [(0.0, "#00ff96"), (1.0, "#ff4444")])
        self.gradient_preview.set_gradient(gradient_stops)
        self.auto_color_change_check.setChecked(getattr(element, 'auto_color_change', True))
        self.animate_gauge_check.setChecked(getattr(element, 'animate_gauge', False))
        self.gauge_rounded_ends_check.setChecked(getattr(element, 'gauge_rounded_ends', False))
        self.label_font_size_spin.setValue(getattr(element, 'label_font_size', 16))
        self.label_font_family_combo.setCurrentText(getattr(element, 'label_font_family', 'Arial'))
        self.label_bold_checkbox.setChecked(getattr(element, 'label_font_bold', False))
        self.label_italic_checkbox.setChecked(getattr(element, 'label_font_italic', False))
        self.temp_hide_unit_check.setChecked(getattr(element, 'temp_hide_unit', False))

        # GIF options
        self.gif_path_edit.setText(getattr(element, 'gif_path', ''))
        scale_mode = getattr(element, 'scale_mode', 'fit')
        scale_idx = self.scale_mode_combo.findData(scale_mode)
        if scale_idx >= 0:
            self.scale_mode_combo.setCurrentIndex(scale_idx)

        # Bar gauge text options
        bar_text_mode = getattr(element, 'bar_text_mode', 'full')
        bar_text_mode_idx = self.bar_text_mode_combo.findData(bar_text_mode)
        if bar_text_mode_idx >= 0:
            self.bar_text_mode_combo.setCurrentIndex(bar_text_mode_idx)

        bar_text_position = getattr(element, 'bar_text_position', 'inside')
        bar_text_position_idx = self.bar_text_position_combo.findData(bar_text_position)
        if bar_text_position_idx >= 0:
            self.bar_text_position_combo.setCurrentIndex(bar_text_position_idx)

        # Digital clock time format options
        time_format = getattr(element, 'time_format', '24h')
        time_format_idx = self.time_format_combo.findData(time_format)
        if time_format_idx >= 0:
            self.time_format_combo.setCurrentIndex(time_format_idx)
        self.show_am_pm_check.setChecked(getattr(element, 'show_am_pm', True))
        self.show_seconds_check.setChecked(getattr(element, 'show_seconds', True))
        self.show_leading_zero_check.setChecked(getattr(element, 'show_leading_zero', True))

        # Analog clock options
        self.show_seconds_hand_check.setChecked(getattr(element, 'show_seconds_hand', True))
        self.show_clock_border_check.setChecked(getattr(element, 'show_clock_border', True))
        clock_face_style = getattr(element, 'clock_face_style', 'numbers')
        clock_face_style_idx = self.clock_face_style_combo.findData(clock_face_style)
        if clock_face_style_idx >= 0:
            self.clock_face_style_combo.setCurrentIndex(clock_face_style_idx)
        self.smooth_animation_check.setChecked(getattr(element, 'smooth_animation', True))

        idx = self.font_family_combo.findText(element.font_family)
        if idx >= 0:
            self.font_family_combo.setCurrentIndex(idx)
        else:
            self.font_family_combo.setCurrentIndex(0)

        self.bold_checkbox.setChecked(element.font_bold)
        self.italic_checkbox.setChecked(element.font_italic)

        self.align_left_btn.setChecked(element.text_align == "left")
        self.align_center_btn.setChecked(element.text_align == "center")
        self.align_right_btn.setChecked(element.text_align == "right")

        self.color_btn.setStyleSheet(f"background-color: {element.color};")
        self.bg_color_btn.setStyleSheet(f"background-color: {element.background_color};")

        # Value and label text colors
        value_text_color = getattr(element, 'text_color', element.color)
        self.value_text_color_btn.setStyleSheet(f"background-color: {value_text_color};")
        label_text_color = getattr(element, 'label_text_color', element.color)
        self.label_text_color_btn.setStyleSheet(f"background-color: {label_text_color};")

        self.set_source_by_id(element.source)

        self.name_edit.blockSignals(False)
        self.x_spin.blockSignals(False)
        self.y_spin.blockSignals(False)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self.border_radius_spin.blockSignals(False)
        self.glass_effect_check.blockSignals(False)
        self.glass_blur_spin.blockSignals(False)
        self.glass_opacity_spin.blockSignals(False)
        self.radius_spin.blockSignals(False)
        self.text_edit.blockSignals(False)
        self.label_text_edit.blockSignals(False)
        self.font_family_combo.blockSignals(False)
        self.font_size_spin.blockSignals(False)
        self.bold_checkbox.blockSignals(False)
        self.italic_checkbox.blockSignals(False)
        self.align_left_btn.blockSignals(False)
        self.align_center_btn.blockSignals(False)
        self.align_right_btn.blockSignals(False)
        self.clip_checkbox.blockSignals(False)
        self.source_combo.blockSignals(False)
        self.value_spin.blockSignals(False)
        self.image_path_edit.blockSignals(False)
        self.scale_proportionally_check.blockSignals(False)
        self.show_background_check.blockSignals(False)
        self.show_label_check.blockSignals(False)
        self.show_gradient_check.blockSignals(False)
        self.line_thickness_spin.blockSignals(False)
        self.smooth_check.blockSignals(False)
        self.rounded_corners_check.blockSignals(False)
        self.bar_border_check.blockSignals(False)
        self.bar_border_width_spin.blockSignals(False)
        self.bar_border_position_combo.blockSignals(False)
        self.gradient_fill_check.blockSignals(False)
        self.auto_color_change_check.blockSignals(False)
        self.animate_gauge_check.blockSignals(False)
        self.gauge_rounded_ends_check.blockSignals(False)
        self.label_font_size_spin.blockSignals(False)
        self.label_font_family_combo.blockSignals(False)
        self.label_bold_checkbox.blockSignals(False)
        self.label_italic_checkbox.blockSignals(False)
        self.temp_hide_unit_check.blockSignals(False)
        self.gif_path_edit.blockSignals(False)
        self.scale_mode_combo.blockSignals(False)
        self.bar_text_mode_combo.blockSignals(False)
        self.bar_text_position_combo.blockSignals(False)
        self.time_format_combo.blockSignals(False)
        self.show_am_pm_check.blockSignals(False)
        self.show_seconds_check.blockSignals(False)
        self.show_leading_zero_check.blockSignals(False)
        self.show_seconds_hand_check.blockSignals(False)
        self.show_clock_border_check.blockSignals(False)
        self.clock_face_style_combo.blockSignals(False)
        self.smooth_animation_check.blockSignals(False)

        self.current_element = element
        self._undo_state_saved = False

        # Re-run visibility now that all values are set (needed for gradient fill, etc.)
        self.update_visible_fields(element.type)

        # Enable/disable controls based on locked state
        self.set_controls_enabled(not element.locked)

    def set_controls_enabled(self, enabled):
        """Enable or disable all property controls."""
        # Name is always editable to allow renaming locked elements
        # self.name_edit.setEnabled(enabled)

        # Position and size
        self.x_spin.setEnabled(enabled)
        self.y_spin.setEnabled(enabled)
        self.width_spin.setEnabled(enabled)
        self.height_spin.setEnabled(enabled)
        self.border_radius_spin.setEnabled(enabled)
        self.glass_effect_check.setEnabled(enabled)
        self.glass_blur_spin.setEnabled(enabled)
        self.glass_opacity_spin.setEnabled(enabled)
        self.radius_spin.setEnabled(enabled)

        # Colors
        self.color_btn.setEnabled(enabled)
        self.bg_color_btn.setEnabled(enabled)
        self.value_text_color_btn.setEnabled(enabled)
        self.label_text_color_btn.setEnabled(enabled)

        # Text properties
        self.text_edit.setEnabled(enabled)
        self.label_text_edit.setEnabled(enabled)
        self.font_family_combo.setEnabled(enabled)
        self.font_size_spin.setEnabled(enabled)
        self.bold_checkbox.setEnabled(enabled)
        self.italic_checkbox.setEnabled(enabled)
        self.align_left_btn.setEnabled(enabled)
        self.align_center_btn.setEnabled(enabled)
        self.align_right_btn.setEnabled(enabled)
        self.clip_checkbox.setEnabled(enabled)

        # Source and value
        self.source_combo.setEnabled(enabled)
        self.value_spin.setEnabled(enabled)

        # Image properties
        self.image_path_edit.setEnabled(enabled)
        self.image_browse_btn.setEnabled(enabled)
        self.scale_proportionally_check.setEnabled(enabled)

        # Line chart options
        self.show_background_check.setEnabled(enabled)
        self.show_label_check.setEnabled(enabled)
        self.show_gradient_check.setEnabled(enabled)
        self.line_thickness_spin.setEnabled(enabled)
        self.smooth_check.setEnabled(enabled)

        # Bar gauge options
        self.rounded_corners_check.setEnabled(enabled)
        self.bar_border_check.setEnabled(enabled)
        self.bar_border_width_spin.setEnabled(enabled)
        self.bar_border_color_btn.setEnabled(enabled)
        self.bar_border_position_combo.setEnabled(enabled)
        self.gradient_fill_check.setEnabled(enabled)
        self.bar_text_mode_combo.setEnabled(enabled)
        self.bar_text_position_combo.setEnabled(enabled)
        self.auto_color_change_check.setEnabled(enabled)
        self.animate_gauge_check.setEnabled(enabled)
        self.gauge_rounded_ends_check.setEnabled(enabled)

        # GIF options
        self.gif_path_edit.setEnabled(enabled)
        self.gif_browse_btn.setEnabled(enabled)
        self.scale_mode_combo.setEnabled(enabled)

        # Digital clock time format options
        self.time_format_combo.setEnabled(enabled)
        self.show_am_pm_check.setEnabled(enabled)
        self.show_seconds_check.setEnabled(enabled)
        self.show_leading_zero_check.setEnabled(enabled)

        # Analog clock options
        self.show_seconds_hand_check.setEnabled(enabled)
        self.show_clock_border_check.setEnabled(enabled)
        self.clock_face_style_combo.setEnabled(enabled)
        self.smooth_animation_check.setEnabled(enabled)

    def on_property_changed(self):
        if self.current_element is None:
            return

        # Don't allow changes to locked elements
        if self.current_element.locked:
            return

        # Save undo state before first change
        if not self._undo_state_saved:
            self.property_will_change.emit()
            self._undo_state_saved = True

        self.current_element.name = self.name_edit.text()
        self.current_element.x = self.x_spin.value()
        self.current_element.y = self.y_spin.value()
        self.current_element.width = self.width_spin.value()
        self.current_element.height = self.height_spin.value()
        self.current_element.border_radius = self.border_radius_spin.value()
        self.current_element.glass_effect = self.glass_effect_check.isChecked()
        self.current_element.glass_blur = self.glass_blur_spin.value()
        self.current_element.glass_opacity = self.glass_opacity_spin.value()
        self.current_element.radius = self.radius_spin.value()
        # For circle_gauge and bar_gauge, use label_text_edit; for others use text_edit
        if self.current_element.type in ["circle_gauge", "bar_gauge"]:
            self.current_element.text = self.label_text_edit.text()
        else:
            self.current_element.text = self.text_edit.text()
        self.current_element.font_family = self.font_family_combo.currentText()
        self.current_element.font_size = self.font_size_spin.value()
        self.current_element.font_bold = self.bold_checkbox.isChecked()
        self.current_element.font_italic = self.italic_checkbox.isChecked()
        self.current_element.clip = self.clip_checkbox.isChecked()

        if self.align_left_btn.isChecked():
            self.current_element.text_align = "left"
        elif self.align_right_btn.isChecked():
            self.current_element.text_align = "right"
        else:
            self.current_element.text_align = "center"

        # Source is handled by on_source_changed, but sync here for safety
        self.current_element.source = self.get_selected_source()
        self.current_element.value = self.value_spin.value()
        self.current_element.image_path = self.image_path_edit.text()
        self.current_element.scale_proportionally = self.scale_proportionally_check.isChecked()

        # Line chart options
        self.current_element.show_background = self.show_background_check.isChecked()
        self.current_element.show_label = self.show_label_check.isChecked()
        self.current_element.show_gradient = self.show_gradient_check.isChecked()
        self.current_element.line_thickness = self.line_thickness_spin.value()
        self.current_element.smooth = self.smooth_check.isChecked()

        # Bar gauge options
        self.current_element.rounded_corners = self.rounded_corners_check.isChecked()
        self.current_element.bar_border = self.bar_border_check.isChecked()
        self.current_element.bar_border_width = self.bar_border_width_spin.value()
        self.current_element.bar_border_position = self.bar_border_position_combo.currentData() or 'center'
        self.current_element.gradient_fill = self.gradient_fill_check.isChecked()
        self.current_element.bar_text_mode = self.bar_text_mode_combo.currentData() or 'full'
        self.current_element.bar_text_position = self.bar_text_position_combo.currentData() or 'inside'

        # Gauge options
        self.current_element.auto_color_change = self.auto_color_change_check.isChecked()
        self.current_element.animate_gauge = self.animate_gauge_check.isChecked()
        self.current_element.gauge_rounded_ends = self.gauge_rounded_ends_check.isChecked()

        # Circle gauge label font options
        self.current_element.label_font_size = self.label_font_size_spin.value()
        self.current_element.label_font_family = self.label_font_family_combo.currentText()
        self.current_element.label_font_bold = self.label_bold_checkbox.isChecked()
        self.current_element.label_font_italic = self.label_italic_checkbox.isChecked()

        # Temperature display options
        self.current_element.temp_hide_unit = self.temp_hide_unit_check.isChecked()

        # GIF options
        self.current_element.gif_path = self.gif_path_edit.text()
        self.current_element.scale_mode = self.scale_mode_combo.currentData() or 'fit'

        # Digital clock time format options
        self.current_element.time_format = self.time_format_combo.currentData() or '24h'
        self.current_element.show_am_pm = self.show_am_pm_check.isChecked()
        self.current_element.show_seconds = self.show_seconds_check.isChecked()
        self.current_element.show_leading_zero = self.show_leading_zero_check.isChecked()

        # Analog clock options
        self.current_element.show_seconds_hand = self.show_seconds_hand_check.isChecked()
        self.current_element.show_clock_border = self.show_clock_border_check.isChecked()
        self.current_element.clock_face_style = self.clock_face_style_combo.currentData() or 'numbers'
        self.current_element.smooth_animation = self.smooth_animation_check.isChecked()

        # Handle proportional scaling for images
        if self.current_element.type == "image" and self.current_element.scale_proportionally:
            # Check which dimension changed and adjust the other
            if hasattr(self, '_last_width') and hasattr(self, '_last_height'):
                if self._last_width != self.width_spin.value() and self.current_element.aspect_ratio > 0:
                    # Width changed, adjust height
                    new_height = int(self.width_spin.value() / self.current_element.aspect_ratio)
                    self.height_spin.blockSignals(True)
                    self.height_spin.setValue(new_height)
                    self.current_element.height = new_height
                    self.height_spin.blockSignals(False)
                elif self._last_height != self.height_spin.value() and self.current_element.aspect_ratio > 0:
                    # Height changed, adjust width
                    new_width = int(self.height_spin.value() * self.current_element.aspect_ratio)
                    self.width_spin.blockSignals(True)
                    self.width_spin.setValue(new_width)
                    self.current_element.width = new_width
                    self.width_spin.blockSignals(False)

        self._last_width = self.width_spin.value()
        self._last_height = self.height_spin.value()

        self.property_changed.emit()

    def choose_color(self):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        opacity = getattr(self.current_element, 'color_opacity', 100)
        dialog = ColorPickerDialog(
            self.current_element.color, opacity, "Select Color", self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            color = dialog.get_color()
            self.current_element.color = color.name()
            self.current_element.color_opacity = dialog.get_opacity()
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.property_changed.emit()

    def choose_bg_color(self):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        opacity = getattr(self.current_element, 'background_color_opacity', 100)
        dialog = ColorPickerDialog(
            self.current_element.background_color, opacity, "Select Background Color", self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            color = dialog.get_color()
            self.current_element.background_color = color.name()
            self.current_element.background_color_opacity = dialog.get_opacity()
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.property_changed.emit()

    def choose_value_text_color(self):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        text_color = getattr(self.current_element, 'text_color', self.current_element.color)
        opacity = getattr(self.current_element, 'text_color_opacity', 100)
        dialog = ColorPickerDialog(
            text_color, opacity, "Select Value Text Color", self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            color = dialog.get_color()
            self.current_element.text_color = color.name()
            self.current_element.text_color_opacity = dialog.get_opacity()
            self.value_text_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.property_changed.emit()

    def choose_label_text_color(self):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        label_text_color = getattr(self.current_element, 'label_text_color', self.current_element.color)
        opacity = getattr(self.current_element, 'text_color_opacity', 100)
        dialog = ColorPickerDialog(
            label_text_color, opacity, "Select Label Text Color", self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            color = dialog.get_color()
            self.current_element.label_text_color = color.name()
            self.label_text_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.property_changed.emit()

    def on_gradient_fill_changed(self, state):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        use_gradient = state == Qt.CheckState.Checked.value
        self.current_element.gradient_fill = use_gradient

        # Batch visibility updates to prevent flicker
        self.setUpdatesEnabled(False)

        # Show/hide color button vs gradient preview
        self.color_label.setVisible(not use_gradient)
        self.color_btn.setVisible(not use_gradient)
        self.gradient_preview_label.setVisible(use_gradient)
        self.gradient_preview.setVisible(use_gradient)

        # Update gradient preview when enabled
        if use_gradient:
            gradient_stops = getattr(self.current_element, 'gradient_stops', [(0.0, "#00ff96"), (1.0, "#ff4444")])
            self.current_element.gradient_stops = gradient_stops
            self.gradient_preview.set_gradient(gradient_stops)

        self.setUpdatesEnabled(True)
        self.property_changed.emit()

    def choose_bar_border_color(self):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        border_color = getattr(self.current_element, 'bar_border_color', '#ffffff')
        opacity = getattr(self.current_element, 'bar_border_opacity', 100)
        dialog = ColorPickerDialog(
            border_color, opacity, "Select Border Color", self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            color = dialog.get_color()
            self.current_element.bar_border_color = color.name()
            self.current_element.bar_border_opacity = dialog.get_opacity()
            self.bar_border_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.property_changed.emit()

    def on_bar_border_changed(self, state):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        show_border = state == Qt.CheckState.Checked.value
        self.current_element.bar_border = show_border

        # Show/hide border options panel based on checkbox state
        self.bar_border_group.setVisible(show_border)

        self.property_changed.emit()

    def edit_gradient(self):
        if self.current_element is None:
            return
        if self.current_element.locked:
            return

        current_stops = getattr(self.current_element, 'gradient_stops', [(0.0, "#00ff96"), (1.0, "#ff4444")])
        dialog = GradientEditorDialog(list(current_stops), "Edit Gradient", self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save undo state before change
            if not self._undo_state_saved:
                self.property_will_change.emit()
                self._undo_state_saved = True

            new_stops = dialog.get_stops()
            self.current_element.gradient_stops = new_stops
            self.gradient_preview.set_gradient(new_stops)
            self.property_changed.emit()

    def browse_gif(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select GIF", "",
            "GIF Images (*.gif)"
        )
        if path:
            self.gif_path_edit.setText(path)

            # Get GIF dimensions and set element size to match
            if self.current_element:
                try:
                    from PIL import Image
                    gif = Image.open(path)
                    img_width, img_height = gif.size

                    # Set dimensions (capped at display size)
                    max_width = min(img_width, constants.DISPLAY_WIDTH)
                    max_height = min(img_height, constants.DISPLAY_HEIGHT)

                    if img_width > max_width or img_height > max_height:
                        scale = min(max_width / img_width, max_height / img_height)
                        img_width = int(img_width * scale)
                        img_height = int(img_height * scale)

                    self.current_element.width = img_width
                    self.current_element.height = img_height

                    self.width_spin.blockSignals(True)
                    self.height_spin.blockSignals(True)
                    self.width_spin.setValue(img_width)
                    self.height_spin.setValue(img_height)
                    self.width_spin.blockSignals(False)
                    self.height_spin.blockSignals(False)
                except Exception as e:
                    print(f"Error reading GIF dimensions: {e}")

    def browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.image_path_edit.setText(path)

            # Get image dimensions and set element size to match
            if self.current_element:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    img_width = pixmap.width()
                    img_height = pixmap.height()

                    # Set aspect ratio
                    if img_height > 0:
                        self.current_element.aspect_ratio = img_width / img_height
                    else:
                        self.current_element.aspect_ratio = 1.0

                    # Set dimensions to match image (capped at display size)
                    max_width = min(img_width, constants.DISPLAY_WIDTH)
                    max_height = min(img_height, constants.DISPLAY_HEIGHT)

                    # Scale down if too large while maintaining aspect ratio
                    if img_width > max_width or img_height > max_height:
                        scale = min(max_width / img_width, max_height / img_height)
                        img_width = int(img_width * scale)
                        img_height = int(img_height * scale)

                    self.current_element.width = img_width
                    self.current_element.height = img_height

                    # Update UI
                    self.width_spin.blockSignals(True)
                    self.height_spin.blockSignals(True)
                    self.width_spin.setValue(img_width)
                    self.height_spin.setValue(img_height)
                    self._last_width = img_width
                    self._last_height = img_height
                    self.width_spin.blockSignals(False)
                    self.height_spin.blockSignals(False)

    def set_multi_selection(self, elements, indices):
        """Show alignment panel for multiple selected elements."""
        self.current_element = None
        self.multi_selection_elements = elements
        self.multi_selection_indices = indices
        self._multi_transform_updating = True  # Prevent feedback loops

        self.no_selection_container.setVisible(False)
        self.scroll_area.setVisible(False)
        self.multi_scroll.setVisible(True)

        # Check if this is a single group (all elements have same group name)
        group_names = set(el.group for el in elements if el.group)
        is_single_group = len(group_names) == 1 and all(el.group for el in elements)
        group_name = list(group_names)[0] if is_single_group else ""

        # Update general section
        if is_single_group:
            self.multi_name_value.setText(f"Group: {group_name}")
            self.group_name_label.setVisible(True)
            self.group_name_edit.setVisible(True)
            self.group_name_edit.blockSignals(True)
            self.group_name_edit.setText(group_name)
            self.group_name_edit.blockSignals(False)
        else:
            self.multi_name_value.setText(f"{len(elements)} elements")
            self.group_name_label.setVisible(False)
            self.group_name_edit.setVisible(False)

        # Calculate combined bounding box
        bounds = self.get_multi_selection_bounds()
        if bounds:
            x, y, w, h = bounds
            self._multi_bounds = bounds  # Store for delta calculation

            self.multi_x_spin.blockSignals(True)
            self.multi_y_spin.blockSignals(True)
            self.multi_w_spin.blockSignals(True)
            self.multi_h_spin.blockSignals(True)

            self.multi_x_spin.setValue(int(x))
            self.multi_y_spin.setValue(int(y))
            self.multi_w_spin.setValue(int(w))
            self.multi_h_spin.setValue(int(h))

            self.multi_x_spin.blockSignals(False)
            self.multi_y_spin.blockSignals(False)
            self.multi_w_spin.blockSignals(False)
            self.multi_h_spin.blockSignals(False)

        self._multi_transform_updating = False

    def get_multi_selection_bounds(self):
        """Get combined bounding box of all selected elements."""
        if not self.multi_selection_elements:
            return None

        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for el in self.multi_selection_elements:
            x, y, w, h = self.get_element_bounds(el)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)

        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def on_group_name_changed(self, text):
        """Handle group name change for selected group."""
        if not self.multi_selection_elements:
            return

        # Update group name for all elements
        for el in self.multi_selection_elements:
            el.group = text if text else None

        self.property_changed.emit()

    def on_multi_transform_changed(self):
        """Handle position change for multi-selection."""
        if getattr(self, '_multi_transform_updating', False):
            return
        if not self.multi_selection_elements:
            return

        # Calculate delta from previous bounds
        old_bounds = getattr(self, '_multi_bounds', None)
        if not old_bounds:
            return

        old_x, old_y, old_w, old_h = old_bounds
        new_x = self.multi_x_spin.value()
        new_y = self.multi_y_spin.value()

        dx = new_x - old_x
        dy = new_y - old_y

        if dx == 0 and dy == 0:
            return

        # Save undo state
        if not self._undo_state_saved:
            self.property_will_change.emit()
            self._undo_state_saved = True

        # Move all elements by delta
        for el in self.multi_selection_elements:
            if not el.locked:
                el.x += dx
                el.y += dy

        # Update stored bounds
        self._multi_bounds = (new_x, new_y, old_w, old_h)

        self.property_changed.emit()

    def on_multi_size_changed(self):
        """Handle size change for multi-selection (scales elements proportionally)."""
        if getattr(self, '_multi_transform_updating', False):
            return
        if not self.multi_selection_elements:
            return

        old_bounds = getattr(self, '_multi_bounds', None)
        if not old_bounds:
            return

        old_x, old_y, old_w, old_h = old_bounds
        new_w = self.multi_w_spin.value()
        new_h = self.multi_h_spin.value()

        if new_w == old_w and new_h == old_h:
            return
        if old_w == 0 or old_h == 0:
            return

        # Calculate scale factors
        scale_x = new_w / old_w
        scale_y = new_h / old_h

        # Save undo state
        if not self._undo_state_saved:
            self.property_will_change.emit()
            self._undo_state_saved = True

        # Scale all elements relative to group origin
        for el in self.multi_selection_elements:
            if el.locked:
                continue

            bounds = self.get_element_bounds(el)
            el_x, el_y, el_w, el_h = bounds

            # Calculate new position relative to group origin
            rel_x = el_x - old_x
            rel_y = el_y - old_y
            new_el_x = old_x + rel_x * scale_x
            new_el_y = old_y + rel_y * scale_y

            # Scale size
            new_el_w = el_w * scale_x
            new_el_h = el_h * scale_y

            # Apply changes based on element type
            if el.type in ["circle_gauge", "analog_clock"]:
                el.radius = int(max(new_el_w, new_el_h) / 2)
                el.x = int(new_el_x + el.radius)
                el.y = int(new_el_y + el.radius)
            else:
                el.x = int(new_el_x)
                el.y = int(new_el_y)
                el.width = int(max(10, new_el_w))
                el.height = int(max(10, new_el_h))

        # Update stored bounds
        self._multi_bounds = (old_x, old_y, new_w, new_h)

        self.property_changed.emit()

    def get_element_bounds(self, element):
        """Get the bounding box for an element."""
        if element.type in ["circle_gauge", "analog_clock"]:
            return (
                element.x - element.radius,
                element.y - element.radius,
                element.radius * 2,
                element.radius * 2
            )
        else:
            return (element.x, element.y, element.width, element.height)

    def set_element_position(self, element, x, y):
        """Set element position, accounting for circle_gauge and analog_clock center."""
        if element.type in ["circle_gauge", "analog_clock"]:
            element.x = int(x + element.radius)
            element.y = int(y + element.radius)
        else:
            element.x = int(x)
            element.y = int(y)

    def get_alignment_units(self):
        """
        Get alignment units - groups are treated as single units, ungrouped elements as individual units.
        Locked elements/groups are excluded from alignment.
        Returns list of dicts: {'elements': [elements], 'bounds': (x, y, w, h)}
        """
        units = []
        grouped = {}  # group_name -> [elements]

        for el in self.multi_selection_elements:
            # Skip locked elements
            if el.locked:
                continue

            if el.group:
                if el.group not in grouped:
                    grouped[el.group] = []
                grouped[el.group].append(el)
            else:
                # Ungrouped element is its own unit
                bounds = self.get_element_bounds(el)
                units.append({'elements': [el], 'bounds': bounds})

        # Add grouped elements as single units
        for group_name, elements in grouped.items():
            # Calculate combined bounding box for the group
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')

            for el in elements:
                x, y, w, h = self.get_element_bounds(el)
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + w)
                max_y = max(max_y, y + h)

            bounds = (min_x, min_y, max_x - min_x, max_y - min_y)
            units.append({'elements': elements, 'bounds': bounds})

        return units

    def move_unit(self, unit, new_x, new_y):
        """Move an alignment unit to a new position (top-left of bounding box)."""
        old_x, old_y, _, _ = unit['bounds']
        dx = new_x - old_x
        dy = new_y - old_y

        for el in unit['elements']:
            el_x, el_y, _, _ = self.get_element_bounds(el)
            self.set_element_position(el, el_x + dx, el_y + dy)

    def align_left(self):
        """Align all selected elements/groups to the left edge."""
        if len(self.multi_selection_elements) < 2:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 2:
            self.alignment_changed.emit()
            return

        # Find minimum x across all units
        min_x = min(unit['bounds'][0] for unit in units)

        # Move each unit to align left
        for unit in units:
            x, y, w, h = unit['bounds']
            self.move_unit(unit, min_x, y)

        self.alignment_changed.emit()
        self.property_changed.emit()

    def align_h_center(self):
        """Align all selected elements/groups to horizontal center."""
        if len(self.multi_selection_elements) < 2:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 2:
            self.alignment_changed.emit()
            return

        # Find the combined bounding box of all units
        min_x = min(unit['bounds'][0] for unit in units)
        max_x = max(unit['bounds'][0] + unit['bounds'][2] for unit in units)
        center_x = (min_x + max_x) / 2

        # Move each unit to center
        for unit in units:
            x, y, w, h = unit['bounds']
            new_x = center_x - w / 2
            self.move_unit(unit, new_x, y)

        self.alignment_changed.emit()
        self.property_changed.emit()

    def align_right(self):
        """Align all selected elements/groups to the right edge."""
        if len(self.multi_selection_elements) < 2:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 2:
            self.alignment_changed.emit()
            return

        # Find maximum right edge across all units
        max_right = max(unit['bounds'][0] + unit['bounds'][2] for unit in units)

        # Move each unit to align right
        for unit in units:
            x, y, w, h = unit['bounds']
            self.move_unit(unit, max_right - w, y)

        self.alignment_changed.emit()
        self.property_changed.emit()

    def align_top(self):
        """Align all selected elements/groups to the top edge."""
        if len(self.multi_selection_elements) < 2:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 2:
            self.alignment_changed.emit()
            return

        # Find minimum y across all units
        min_y = min(unit['bounds'][1] for unit in units)

        # Move each unit to align top
        for unit in units:
            x, y, w, h = unit['bounds']
            self.move_unit(unit, x, min_y)

        self.alignment_changed.emit()
        self.property_changed.emit()

    def align_v_middle(self):
        """Align all selected elements/groups to vertical center."""
        if len(self.multi_selection_elements) < 2:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 2:
            self.alignment_changed.emit()
            return

        # Find the combined bounding box of all units
        min_y = min(unit['bounds'][1] for unit in units)
        max_y = max(unit['bounds'][1] + unit['bounds'][3] for unit in units)
        center_y = (min_y + max_y) / 2

        # Move each unit to center
        for unit in units:
            x, y, w, h = unit['bounds']
            new_y = center_y - h / 2
            self.move_unit(unit, x, new_y)

        self.alignment_changed.emit()
        self.property_changed.emit()

    def align_bottom(self):
        """Align all selected elements/groups to the bottom edge."""
        if len(self.multi_selection_elements) < 2:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 2:
            self.alignment_changed.emit()
            return

        # Find maximum bottom edge across all units
        max_bottom = max(unit['bounds'][1] + unit['bounds'][3] for unit in units)

        # Move each unit to align bottom
        for unit in units:
            x, y, w, h = unit['bounds']
            self.move_unit(unit, x, max_bottom - h)

        self.alignment_changed.emit()
        self.property_changed.emit()

    def distribute_horizontal(self):
        """Distribute elements/groups evenly horizontally."""
        if len(self.multi_selection_elements) < 3:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 3:
            self.alignment_changed.emit()
            return

        # Sort units by x position
        units.sort(key=lambda u: u['bounds'][0])

        # Get total span
        first_x = units[0]['bounds'][0]
        last_unit = units[-1]
        last_right = last_unit['bounds'][0] + last_unit['bounds'][2]

        # Calculate total unit width
        total_width = sum(u['bounds'][2] for u in units)

        # Calculate gaps
        available_space = last_right - first_x - total_width
        gap = available_space / (len(units) - 1)

        # Position units
        current_x = first_x
        for unit in units:
            x, y, w, h = unit['bounds']
            self.move_unit(unit, current_x, y)
            current_x += w + gap

        self.alignment_changed.emit()
        self.property_changed.emit()

    def distribute_vertical(self):
        """Distribute elements/groups evenly vertically."""
        if len(self.multi_selection_elements) < 3:
            return

        self.alignment_will_change.emit()
        units = self.get_alignment_units()
        if len(units) < 3:
            self.alignment_changed.emit()
            return

        # Sort units by y position
        units.sort(key=lambda u: u['bounds'][1])

        # Get total span
        first_y = units[0]['bounds'][1]
        last_unit = units[-1]
        last_bottom = last_unit['bounds'][1] + last_unit['bounds'][3]

        # Calculate total unit height
        total_height = sum(u['bounds'][3] for u in units)

        # Calculate gaps
        available_space = last_bottom - first_y - total_height
        gap = available_space / (len(units) - 1)

        # Position units
        current_y = first_y
        for unit in units:
            x, y, w, h = unit['bounds']
            self.move_unit(unit, x, current_y)
            current_y += h + gap

        self.alignment_changed.emit()
        self.property_changed.emit()
