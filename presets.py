"""
PresetsPanel - Theme preset management widget.
"""

import os
import json
import math
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QScrollArea, QFrame, QGridLayout, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPixmap

import constants
from element import ThemeElement
from app_path import get_resource_path
from security import validate_preset_schema, is_safe_filename, sanitize_preset_name
from settings import get_setting, set_setting

# Thumbnail dimensions (maintain aspect ratio of display)
THUMBNAIL_WIDTH = 150
LABEL_HEIGHT = 20


def get_thumbnail_height():
    """Compute thumbnail height from current display resolution."""
    return int(THUMBNAIL_WIDTH * constants.DISPLAY_HEIGHT / constants.DISPLAY_WIDTH)


# Per-resolution builtin default themes
BUILTIN_DEFAULTS = {
    "1280x480": {
        "name": "Default",
        "background_color": "#0f0f19",
        "display_width": 1280,
        "display_height": 480,
        "elements": [
            {"type": "circle_gauge", "name": "cpu_temp_gauge", "x": 200, "y": 240, "radius": 120,
             "text": "CPU TEMP", "source": "cpu_temp", "color": "#00ff96", "value": 45},
            {"type": "circle_gauge", "name": "cpu_util_gauge", "x": 480, "y": 240, "radius": 120,
             "text": "CPU UTIL", "source": "cpu_percent", "color": "#00c8ff", "value": 30},
            {"type": "circle_gauge", "name": "gpu_util_gauge", "x": 760, "y": 240, "radius": 120,
             "text": "GPU UTIL", "source": "gpu_percent", "color": "#c864ff", "value": 55},
            {"type": "circle_gauge", "name": "gpu_temp_gauge", "x": 1040, "y": 240, "radius": 120,
             "text": "GPU TEMP", "source": "gpu_temp", "color": "#ff9632", "value": 62},
            {"type": "text", "name": "title", "x": 490, "y": 20, "text": "SYSTEM MONITOR",
             "font_size": 36, "color": "#666680", "width": 300, "height": 50},
        ]
    },
    "480x480": {
        "name": "Default",
        "background_color": "#0f0f19",
        "display_width": 480,
        "display_height": 480,
        "elements": [
            {"type": "circle_gauge", "name": "cpu_temp_gauge", "x": 120, "y": 140, "radius": 80,
             "text": "CPU TEMP", "source": "cpu_temp", "color": "#00ff96", "value": 45},
            {"type": "circle_gauge", "name": "cpu_util_gauge", "x": 360, "y": 140, "radius": 80,
             "text": "CPU UTIL", "source": "cpu_percent", "color": "#00c8ff", "value": 30},
            {"type": "circle_gauge", "name": "gpu_util_gauge", "x": 120, "y": 360, "radius": 80,
             "text": "GPU UTIL", "source": "gpu_percent", "color": "#c864ff", "value": 55},
            {"type": "circle_gauge", "name": "gpu_temp_gauge", "x": 360, "y": 360, "radius": 80,
             "text": "GPU TEMP", "source": "gpu_temp", "color": "#ff9632", "value": 62},
        ]
    },
}


class PresetThumbnail(QWidget):
    """Widget that displays a small preview thumbnail of a preset."""
    clicked = Signal(str)  # Emits preset name
    delete_requested = Signal(str)  # Emits preset name for deletion
    set_default_requested = Signal(str)  # Emits preset name to set as default

    def __init__(self, preset_name, preset_data, is_builtin=False, is_default=False, thumbnail_path=None, display_name=None):
        super().__init__()
        self.preset_name = preset_name
        self.display_name = display_name or preset_name
        self.preset_data = preset_data
        self.is_builtin = is_builtin
        self.is_default = is_default
        self.thumbnail_path = thumbnail_path
        self.thumbnail_pixmap = None
        self._thumbnail_height = get_thumbnail_height()

        # Load thumbnail image if it exists
        if thumbnail_path and os.path.exists(thumbnail_path):
            self.thumbnail_pixmap = QPixmap(thumbnail_path)

        self.setFixedSize(THUMBNAIL_WIDTH, self._thumbnail_height + LABEL_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        tooltip = f"Click to load: {preset_name}"
        if is_default:
            tooltip += " (Default)"
        self.setToolTip(tooltip)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        preview_height = self._thumbnail_height

        # Use saved thumbnail if available, otherwise generate preview
        if self.thumbnail_pixmap and not self.thumbnail_pixmap.isNull():
            # Draw the saved thumbnail scaled to fill the preview area exactly
            scaled_pixmap = self.thumbnail_pixmap.scaled(
                THUMBNAIL_WIDTH, preview_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled_pixmap)

            # Draw border
            painter.setPen(QPen(QColor(60, 60, 80), 2))
            painter.drawRect(0, 0, THUMBNAIL_WIDTH, preview_height)
        else:
            # Fall back to generated preview
            # Draw background
            bg_color = QColor(self.preset_data.get("background_color", "#0f0f19"))
            painter.fillRect(0, 0, THUMBNAIL_WIDTH, preview_height, bg_color)

            # Draw border
            painter.setPen(QPen(QColor(60, 60, 80), 2))
            painter.drawRect(0, 0, THUMBNAIL_WIDTH, preview_height)

            # Scale factor for preview — use the preset's own resolution
            preset_w = self.preset_data.get("display_width", constants.DISPLAY_WIDTH)
            preset_h = self.preset_data.get("display_height", constants.DISPLAY_HEIGHT)
            scale_x = THUMBNAIL_WIDTH / preset_w
            scale_y = preview_height / preset_h

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
        label_y = self._thumbnail_height
        painter.fillRect(0, label_y, THUMBNAIL_WIDTH, LABEL_HEIGHT, QColor(35, 35, 40))
        painter.setPen(QPen(QColor(200, 200, 200)))
        font = QFont()
        font.setPixelSize(11)
        painter.setFont(font)

        # Truncate name if too long
        display_name = self.display_name
        if len(display_name) > 18:
            display_name = display_name[:15] + "..."

        painter.drawText(5, label_y + LABEL_HEIGHT - 5, display_name)

        # Draw indicators on the right side
        indicator_x = THUMBNAIL_WIDTH - 15

        # Draw checkmark for default preset
        if self.is_default:
            painter.setPen(QPen(QColor(0, 255, 150)))
            painter.drawText(indicator_x, label_y + LABEL_HEIGHT - 5, "✓")
            indicator_x -= 15

        # Draw star for built-in presets
        if self.is_builtin:
            painter.setPen(QPen(QColor(255, 200, 0)))
            painter.drawText(indicator_x, label_y + LABEL_HEIGHT - 5, "★")

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.preset_name)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)

        # Set as default option (available for all presets)
        if self.is_default:
            default_action = menu.addAction("✓ Default Preset")
            default_action.setEnabled(False)
        else:
            default_action = menu.addAction("Set as Default")

        # Delete option (only for non-builtin)
        delete_action = None
        if not self.is_builtin:
            menu.addSeparator()
            delete_action = menu.addAction("Delete Preset")

        action = menu.exec(event.globalPos())
        if action == default_action and not self.is_default:
            self.set_default_requested.emit(self.preset_name)
        elif action == delete_action:
            self.delete_requested.emit(self.preset_name)


class PresetsPanel(QWidget):
    preset_selected = Signal(dict)  # Emits preset data when selected
    preset_saved = Signal(str)  # Emits preset name when saved
    default_changed = Signal(str)  # Emits preset name when default is changed

    PRESETS_PER_PAGE = 8

    def __init__(self):
        super().__init__()
        self.presets = {}
        self.current_page = 0
        self.presets_dir = get_resource_path("presets")
        self._filter_resolution = f"{constants.DISPLAY_WIDTH}x{constants.DISPLAY_HEIGHT}"
        self._show_all = False
        self.setup_ui()
        self.load_presets()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title row with New button
        title_row = QHBoxLayout()
        title = QLabel("Presets")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        title_row.addWidget(title)
        title_row.addStretch()

        self.show_all_cb = QCheckBox("All")
        self.show_all_cb.setToolTip("Show presets for all resolutions")
        self.show_all_cb.toggled.connect(self._on_show_all_toggled)
        title_row.addWidget(self.show_all_cb)

        self.new_preset_btn = QPushButton("+ New")
        self.new_preset_btn.setFixedWidth(60)
        self.new_preset_btn.clicked.connect(self.create_new_preset)
        title_row.addWidget(self.new_preset_btn)

        layout.addLayout(title_row)

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

    def set_resolution_filter(self, width, height):
        """Update the resolution filter and reload presets."""
        self._filter_resolution = f"{width}x{height}"
        self.current_page = 0
        self.load_presets()

    def _on_show_all_toggled(self, checked):
        """Handle the 'All' checkbox toggle."""
        self._show_all = checked
        self.current_page = 0
        self.load_presets()

    def ensure_presets_dir(self):
        """Create presets directory if it doesn't exist."""
        if not os.path.exists(self.presets_dir):
            os.makedirs(self.presets_dir)

    def _migrate_flat_presets(self):
        """Migrate legacy flat presets into the new hierarchy.

        Moves presets/{Name}.json + {Name}.png into
        presets/{resolution}/{Name}/preset.json + thumbnail.png.
        Runs once per load — no-op if no flat .json files exist.
        """
        flat_jsons = [f for f in os.listdir(self.presets_dir)
                      if f.endswith(".json") and os.path.isfile(os.path.join(self.presets_dir, f))]
        if not flat_jsons:
            return

        for filename in flat_jsons:
            filepath = os.path.join(self.presets_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                pw = data.get("display_width", 1280)
                ph = data.get("display_height", 480)
                res_key = f"{pw}x{ph}"

                preset_name = sanitize_preset_name(data.get("name", filename[:-5]))

                dest_dir = os.path.join(self.presets_dir, res_key, preset_name)
                os.makedirs(dest_dir, exist_ok=True)

                # Move JSON
                shutil.move(filepath, os.path.join(dest_dir, "preset.json"))

                # Move thumbnail if it exists
                old_thumb = os.path.join(self.presets_dir, filename[:-5] + ".png")
                if os.path.exists(old_thumb):
                    shutil.move(old_thumb, os.path.join(dest_dir, "thumbnail.png"))

                print(f"[Presets] Migrated '{filename}' → {res_key}/{preset_name}/")
            except Exception as e:
                print(f"[Presets] Failed to migrate {filename}: {e}")

    def load_presets(self):
        """Load all presets from the presets folder hierarchy."""
        self.presets = {}

        # Add builtin defaults based on filter state
        if self._show_all:
            for res_key, theme_data in BUILTIN_DEFAULTS.items():
                label = f"Default ({res_key})"
                self.presets[label] = {
                    "data": theme_data,
                    "builtin": True,
                    "thumbnail_path": None,
                    "resolution": res_key,
                }
        else:
            # Only add the builtin for the current filter resolution
            if self._filter_resolution in BUILTIN_DEFAULTS:
                self.presets["Default"] = {
                    "data": BUILTIN_DEFAULTS[self._filter_resolution],
                    "builtin": True,
                    "thumbnail_path": None,
                    "resolution": self._filter_resolution,
                }

        # Load presets from folder hierarchy
        self.ensure_presets_dir()
        self._migrate_flat_presets()

        for res_name in os.listdir(self.presets_dir):
            res_dir = os.path.join(self.presets_dir, res_name)
            if not os.path.isdir(res_dir):
                continue

            for preset_folder in os.listdir(res_dir):
                preset_dir = os.path.join(res_dir, preset_folder)
                if not os.path.isdir(preset_dir):
                    continue

                json_path = os.path.join(preset_dir, "preset.json")
                if not os.path.exists(json_path):
                    continue

                try:
                    with open(json_path, 'r') as f:
                        data = json.load(f)

                    # Validate preset schema before using
                    is_valid, errors = validate_preset_schema(data)
                    if not is_valid:
                        print(f"Invalid preset {res_name}/{preset_folder}: {errors}")
                        continue

                    preset_name = data.get("name", preset_folder)

                    # Determine resolution from preset data
                    pw = data.get("display_width", 1280)
                    ph = data.get("display_height", 480)
                    preset_res = f"{pw}x{ph}"

                    # Check for thumbnail
                    thumbnail_path = os.path.join(preset_dir, "thumbnail.png")
                    if not os.path.exists(thumbnail_path):
                        thumbnail_path = None

                    self.presets[preset_name] = {
                        "data": data,
                        "builtin": False,
                        "filepath": json_path,
                        "thumbnail_path": thumbnail_path,
                        "resolution": preset_res,
                    }
                except Exception as e:
                    print(f"Failed to load preset {res_name}/{preset_folder}: {e}")

        self.refresh_display()

    def refresh_display(self):
        """Refresh the preset thumbnails display."""
        # Clear existing thumbnails properly
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # Get sorted preset names (Default/Default(...) first, then alphabetical)
        all_names = sorted(self.presets.keys(), key=lambda x: (not x.startswith("Default"), x.lower()))

        # Filter by resolution unless showing all
        if self._show_all:
            preset_names = all_names
        else:
            preset_names = [
                n for n in all_names
                if self.presets[n].get("resolution") == self._filter_resolution
            ]

        # Calculate pagination
        total_presets = len(preset_names)
        total_pages = max(1, math.ceil(total_presets / self.PRESETS_PER_PAGE))
        self.current_page = min(self.current_page, total_pages - 1)

        # Get presets for current page
        start_idx = self.current_page * self.PRESETS_PER_PAGE
        end_idx = start_idx + self.PRESETS_PER_PAGE
        page_presets = preset_names[start_idx:end_idx]

        # Get the default preset name — per-resolution first, then legacy fallback
        default_presets = get_setting("default_presets", {})
        default_preset = default_presets.get(self._filter_resolution) or get_setting("default_preset", None)

        # Create thumbnails in a 2-column grid
        for i, name in enumerate(page_presets):
            preset_info = self.presets[name]

            # When showing all resolutions, append resolution to the label
            if self._show_all and not preset_info.get("builtin", False):
                res = preset_info.get("resolution", "")
                label = f"{name} ({res})" if res else name
            else:
                label = name

            thumbnail = PresetThumbnail(
                name,
                preset_info["data"],
                preset_info.get("builtin", False),
                is_default=(name == default_preset),
                thumbnail_path=preset_info.get("thumbnail_path"),
                display_name=label,
            )
            thumbnail.clicked.connect(self.on_preset_clicked)
            thumbnail.delete_requested.connect(self.on_delete_preset)
            thumbnail.set_default_requested.connect(self.on_set_default_preset)
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
                        # Delete the preset's folder (contains preset.json + thumbnail.png)
                        preset_dir = os.path.dirname(filepath)
                        shutil.rmtree(preset_dir)
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to delete preset folder: {e}")
                        return
                del self.presets[preset_name]

                # Clear default if deleted preset was the default
                if get_setting("default_preset") == preset_name:
                    set_setting("default_preset", None)

                # Clean up per-resolution defaults
                default_presets = get_setting("default_presets", {})
                changed = False
                for res_key, def_name in list(default_presets.items()):
                    if def_name == preset_name:
                        del default_presets[res_key]
                        changed = True
                if changed:
                    set_setting("default_presets", default_presets)

                # Delay refresh to allow context menu to close properly
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self.refresh_display)

    def on_set_default_preset(self, preset_name):
        """Handle setting a preset as default for the current resolution."""
        if preset_name in self.presets:
            preset_res = self.presets[preset_name].get("resolution", self._filter_resolution)
            default_presets = get_setting("default_presets", {})
            default_presets[preset_res] = preset_name
            set_setting("default_presets", default_presets)
            self.default_changed.emit(preset_name)
            # Delay refresh to allow context menu to close properly
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self.refresh_display)

    def create_new_preset(self):
        """Create a new empty preset with a black background."""
        name, ok = QInputDialog.getText(
            self, "New Preset",
            "Enter preset name:",
            text="New Theme"
        )

        if not ok or not name.strip():
            return

        name = name.strip()

        # Check if name already exists
        if name in self.presets:
            QMessageBox.warning(
                self, "Name Exists",
                f"A preset named '{name}' already exists. Please choose a different name."
            )
            return

        # Create empty preset data
        new_preset_data = {
            "name": name,
            "background_color": "#000000",
            "display_width": constants.DISPLAY_WIDTH,
            "display_height": constants.DISPLAY_HEIGHT,
            "elements": [],
            "video_background": {
                "video_path": "",
                "fit_mode": "fit_height",
                "enabled": False
            }
        }

        # Save the preset (without thumbnail since it's empty/black)
        if self.save_preset(name, new_preset_data):
            # Emit signal to load the new preset
            self.preset_selected.emit(new_preset_data)

    def get_default_preset_data(self):
        """Get the default preset data for the current resolution filter."""
        # Check per-resolution default first
        default_presets = get_setting("default_presets", {})
        default_name = default_presets.get(self._filter_resolution)
        # Fall back to legacy default_preset
        if not default_name:
            default_name = get_setting("default_preset", None)
        if default_name and default_name in self.presets:
            return self.presets[default_name]["data"]
        return None

    def save_preset(self, name, theme_data, thumbnail_image=None):
        """Save a theme as a preset with optional thumbnail.

        Args:
            name: Preset name
            theme_data: Theme data dict
            thumbnail_image: Optional PIL Image to save as thumbnail
        """
        self.ensure_presets_dir()

        # Sanitize the name for safe folder name
        safe_name = sanitize_preset_name(name)

        # Validate the folder name is safe
        safe, err = is_safe_filename(safe_name)
        if not safe:
            QMessageBox.warning(self, "Error", f"Invalid preset name: {err}")
            return False

        # Determine resolution from theme data
        pw = theme_data.get("display_width", constants.DISPLAY_WIDTH)
        ph = theme_data.get("display_height", constants.DISPLAY_HEIGHT)
        res_key = f"{pw}x{ph}"

        preset_dir = os.path.join(self.presets_dir, res_key, safe_name)
        filepath = os.path.join(preset_dir, "preset.json")
        thumbnail_path = os.path.join(preset_dir, "thumbnail.png")

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
            os.makedirs(preset_dir, exist_ok=True)

            with open(filepath, 'w') as f:
                json.dump(theme_data, f, indent=2)

            # Save thumbnail if provided
            if thumbnail_image is not None:
                try:
                    # Resize to thumbnail dimensions
                    thumbnail = thumbnail_image.copy()
                    thumbnail.thumbnail((THUMBNAIL_WIDTH * 2, get_thumbnail_height() * 2))  # 2x for retina/sharp display
                    thumbnail.save(thumbnail_path, "PNG")
                except Exception as e:
                    print(f"[Presets] Failed to save thumbnail: {e}")
                    thumbnail_path = None
            else:
                thumbnail_path = None

            self.presets[name] = {
                "data": theme_data,
                "builtin": False,
                "filepath": filepath,
                "thumbnail_path": thumbnail_path if thumbnail_path and os.path.exists(thumbnail_path) else None,
                "resolution": res_key,
            }
            self.refresh_display()
            self.preset_saved.emit(name)
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save preset: {e}")
            return False
