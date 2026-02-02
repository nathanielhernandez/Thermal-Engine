"""
PresetsPanel - Theme preset management widget.
"""

import os
import json
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPixmap

from constants import DISPLAY_WIDTH, DISPLAY_HEIGHT
from element import ThemeElement
from app_path import get_resource_path


# Default theme elements (same as main_window.py)
DEFAULT_THEME = {
    "name": "Default",
    "background_color": "#0f0f19",
    "elements": [
        {"type": "circle_gauge", "name": "cpu_temp_gauge", "x": 200, "y": 240, "radius": 120,
         "text": "CPU TEMP", "source": "cpu_temp", "color": "#00ff96", "value": 45},
        {"type": "circle_gauge", "name": "cpu_load_gauge", "x": 480, "y": 240, "radius": 120,
         "text": "CPU LOAD", "source": "cpu_percent", "color": "#00c8ff", "value": 30},
        {"type": "circle_gauge", "name": "gpu_load_gauge", "x": 760, "y": 240, "radius": 120,
         "text": "GPU LOAD", "source": "gpu_percent", "color": "#c864ff", "value": 55},
        {"type": "circle_gauge", "name": "gpu_temp_gauge", "x": 1040, "y": 240, "radius": 120,
         "text": "GPU TEMP", "source": "gpu_temp", "color": "#ff9632", "value": 62},
        {"type": "text", "name": "title", "x": 490, "y": 20, "text": "SYSTEM MONITOR",
         "font_size": 36, "color": "#666680", "width": 300, "height": 50},
    ]
}


class PresetThumbnail(QWidget):
    """Widget that displays a small preview thumbnail of a preset."""
    clicked = Signal(str)  # Emits preset name
    delete_requested = Signal(str)  # Emits preset name for deletion

    def __init__(self, preset_name, preset_data, is_builtin=False):
        super().__init__()
        self.preset_name = preset_name
        self.preset_data = preset_data
        self.is_builtin = is_builtin
        self.setFixedSize(150, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Click to load: {preset_name}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        bg_color = QColor(self.preset_data.get("background_color", "#0f0f19"))
        painter.fillRect(0, 0, self.width(), self.height() - 20, bg_color)

        # Draw border
        painter.setPen(QPen(QColor(60, 60, 80), 2))
        painter.drawRect(0, 0, self.width(), self.height() - 20)

        # Scale factor for preview
        scale_x = self.width() / DISPLAY_WIDTH
        scale_y = (self.height() - 20) / DISPLAY_HEIGHT

        # Draw simplified element previews
        elements = self.preset_data.get("elements", [])
        for el_data in elements:
            el_type = el_data.get("type", "")
            color = QColor(el_data.get("color", "#00ff96"))
            x = int(el_data.get("x", 0) * scale_x)
            y = int(el_data.get("y", 0) * scale_y)

            if el_type in ["circle_gauge", "analog_clock"]:
                radius = int(el_data.get("radius", 50) * min(scale_x, scale_y))
                painter.setPen(QPen(color, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)
            elif el_type in ["bar_gauge", "rectangle", "text", "clock", "image", "line_chart", "gif"]:
                width = int(el_data.get("width", 100) * scale_x)
                height = int(el_data.get("height", 30) * scale_y)
                painter.setPen(QPen(color, 1))
                painter.setBrush(QBrush(color.darker(200)))
                painter.drawRect(x, y, max(width, 3), max(height, 3))

        # Draw name label at bottom
        painter.fillRect(0, self.height() - 20, self.width(), 20, QColor(35, 35, 40))
        painter.setPen(QPen(QColor(200, 200, 200)))
        font = QFont()
        font.setPixelSize(11)
        painter.setFont(font)

        # Truncate name if too long
        display_name = self.preset_name
        if len(display_name) > 18:
            display_name = display_name[:15] + "..."

        painter.drawText(5, self.height() - 5, display_name)

        # Draw star for built-in presets
        if self.is_builtin:
            painter.setPen(QPen(QColor(255, 200, 0)))
            painter.drawText(self.width() - 15, self.height() - 5, "★")

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.preset_name)

    def contextMenuEvent(self, event):
        if not self.is_builtin:
            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Preset")
            action = menu.exec(event.globalPos())
            if action == delete_action:
                self.delete_requested.emit(self.preset_name)


class PresetsPanel(QWidget):
    preset_selected = Signal(dict)  # Emits preset data when selected
    preset_saved = Signal(str)  # Emits preset name when saved

    PRESETS_PER_PAGE = 8

    def __init__(self):
        super().__init__()
        self.presets = {}
        self.current_page = 0
        self.presets_dir = get_resource_path("presets")
        self.setup_ui()
        self.load_presets()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title = QLabel("Presets")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title)

        # Preset grid container
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        layout.addWidget(self.grid_container)

        # Pagination controls
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_widget)
        pagination_layout.setContentsMargins(0, 5, 0, 0)

        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setFixedWidth(70)
        pagination_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1/1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setFixedWidth(70)
        pagination_layout.addWidget(self.next_btn)

        layout.addWidget(self.pagination_widget)

        layout.addStretch()

    def ensure_presets_dir(self):
        """Create presets directory if it doesn't exist."""
        if not os.path.exists(self.presets_dir):
            os.makedirs(self.presets_dir)

    def load_presets(self):
        """Load all presets from the presets folder."""
        self.presets = {}

        # Always include the default preset
        self.presets["Default"] = {
            "data": DEFAULT_THEME,
            "builtin": True
        }

        # Load presets from folder
        self.ensure_presets_dir()
        for filename in os.listdir(self.presets_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.presets_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    preset_name = data.get("name", filename[:-5])
                    self.presets[preset_name] = {
                        "data": data,
                        "builtin": False,
                        "filepath": filepath
                    }
                except Exception as e:
                    print(f"Failed to load preset {filename}: {e}")

        self.refresh_display()

    def refresh_display(self):
        """Refresh the preset thumbnails display."""
        # Clear existing thumbnails properly
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        # Process events to ensure widgets are removed
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        # Get sorted preset names (Default first, then alphabetical)
        preset_names = sorted(self.presets.keys(), key=lambda x: (x != "Default", x.lower()))

        # Calculate pagination
        total_presets = len(preset_names)
        total_pages = max(1, math.ceil(total_presets / self.PRESETS_PER_PAGE))
        self.current_page = min(self.current_page, total_pages - 1)

        # Get presets for current page
        start_idx = self.current_page * self.PRESETS_PER_PAGE
        end_idx = start_idx + self.PRESETS_PER_PAGE
        page_presets = preset_names[start_idx:end_idx]

        # Create thumbnails in a 2-column grid
        for i, name in enumerate(page_presets):
            preset_info = self.presets[name]
            thumbnail = PresetThumbnail(
                name,
                preset_info["data"],
                preset_info.get("builtin", False)
            )
            thumbnail.clicked.connect(self.on_preset_clicked)
            thumbnail.delete_requested.connect(self.on_delete_preset)
            row = i // 2
            col = i % 2
            self.grid_layout.addWidget(thumbnail, row, col)

        # Update pagination controls
        self.page_label.setText(f"Page {self.current_page + 1}/{total_pages}")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)
        self.pagination_widget.setVisible(total_pages > 1)

        # Force layout update
        self.grid_container.updateGeometry()
        self.updateGeometry()
        self.update()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_display()

    def next_page(self):
        total_pages = math.ceil(len(self.presets) / self.PRESETS_PER_PAGE)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.refresh_display()

    def on_preset_clicked(self, preset_name):
        """Handle preset selection."""
        if preset_name in self.presets:
            preset_data = self.presets[preset_name]["data"]
            self.preset_selected.emit(preset_data)

    def on_delete_preset(self, preset_name):
        """Handle preset deletion request."""
        if preset_name in self.presets and not self.presets[preset_name].get("builtin", False):
            reply = QMessageBox.question(
                self, "Delete Preset",
                f"Are you sure you want to delete the preset '{preset_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                filepath = self.presets[preset_name].get("filepath")
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to delete preset file: {e}")
                        return
                del self.presets[preset_name]
                self.refresh_display()

    def save_preset(self, name, theme_data):
        """Save a theme as a preset."""
        self.ensure_presets_dir()

        # Clean the name for filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "preset"

        filepath = os.path.join(self.presets_dir, f"{safe_name}.json")

        # Check if overwriting
        if os.path.exists(filepath):
            reply = QMessageBox.question(
                self, "Overwrite Preset",
                f"A preset named '{name}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False

        try:
            with open(filepath, 'w') as f:
                json.dump(theme_data, f, indent=2)

            self.presets[name] = {
                "data": theme_data,
                "builtin": False,
                "filepath": filepath
            }
            self.refresh_display()
            self.preset_saved.emit(name)
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save preset: {e}")
            return False
