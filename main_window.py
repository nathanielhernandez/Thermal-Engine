"""
ThemeEditorWindow - Main application window.
"""

import sys
import os
import json
import time
import io
import threading
import psutil

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QColorDialog, QFileDialog,
    QComboBox, QSplitter, QMessageBox, QStatusBar, QTabWidget,
    QDialog, QCheckBox, QDialogButtonBox, QGroupBox, QFormLayout, QSystemTrayIcon
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QAction, QKeySequence, QIcon

from PIL import Image, ImageDraw, ImageFont

from security import validate_preset_schema, is_safe_path


# Global font cache for PIL fonts (shared across instances)
_pil_font_cache = {}
_pil_font_cache_lock = threading.Lock()


# Background psutil data collection
_psutil_data = {
    'cpu_percent': 0,
    'ram_percent': 0,
    'ram_used': 0,
    'ram_available': 0,
    'net_upload': 0,
    'net_download': 0,
}
_psutil_data_lock = threading.Lock()
_psutil_thread = None
_psutil_thread_running = False
_cpu_percent_history = []
_last_net_io = None
_last_net_time = 0


def _psutil_polling_thread():
    """Background thread that continuously polls psutil data."""
    global _psutil_data, _psutil_thread_running, _cpu_percent_history, _last_net_io, _last_net_time

    # Initialize CPU percent
    psutil.cpu_percent(interval=None)

    while _psutil_thread_running:
        try:
            # CPU (smoothed)
            raw_cpu = psutil.cpu_percent(interval=None)
            _cpu_percent_history.append(raw_cpu)
            if len(_cpu_percent_history) > 5:
                _cpu_percent_history.pop(0)
            smoothed_cpu = sum(_cpu_percent_history) / len(_cpu_percent_history)

            # RAM
            ram = psutil.virtual_memory()

            # Network
            net_upload = 0
            net_download = 0
            try:
                net_io = psutil.net_io_counters()
                current_time = time.time()
                if _last_net_io and _last_net_time:
                    time_delta = current_time - _last_net_time
                    if time_delta > 0:
                        bytes_sent = net_io.bytes_sent - _last_net_io.bytes_sent
                        bytes_recv = net_io.bytes_recv - _last_net_io.bytes_recv
                        net_upload = (bytes_sent / time_delta) / (1024 * 1024)
                        net_download = (bytes_recv / time_delta) / (1024 * 1024)
                _last_net_io = net_io
                _last_net_time = current_time
            except:
                pass

            # Update shared data
            with _psutil_data_lock:
                _psutil_data['cpu_percent'] = round(smoothed_cpu, 1)
                _psutil_data['ram_percent'] = ram.percent
                _psutil_data['ram_used'] = round(ram.used / (1024**3), 1)
                _psutil_data['ram_available'] = round(ram.available / (1024**3), 1)
                _psutil_data['net_upload'] = round(net_upload, 2)
                _psutil_data['net_download'] = round(net_download, 2)

        except Exception as e:
            print(f"[Psutil] Background poll error: {e}")

        # Poll every 200ms for responsive CPU readings
        time.sleep(0.2)


def start_psutil_thread():
    """Start the background psutil polling thread."""
    global _psutil_thread, _psutil_thread_running
    if _psutil_thread is None or not _psutil_thread.is_alive():
        _psutil_thread_running = True
        _psutil_thread = threading.Thread(target=_psutil_polling_thread, daemon=True)
        _psutil_thread.start()
        print("[Psutil] Background polling thread started")


def stop_psutil_thread():
    """Stop the background psutil polling thread."""
    global _psutil_thread_running, _psutil_thread
    _psutil_thread_running = False
    if _psutil_thread and _psutil_thread.is_alive():
        _psutil_thread.join(timeout=1.0)
    _psutil_thread = None


def get_psutil_data():
    """Get psutil data from background thread cache (non-blocking)."""
    with _psutil_data_lock:
        return _psutil_data.copy()

try:
    import hid
    HAS_HID = True
except ImportError:
    HAS_HID = False

from constants import DISPLAY_WIDTH, DISPLAY_HEIGHT, SOURCE_UNITS


def get_value_with_unit(value, source):
    """Format a value with its appropriate unit symbol."""
    unit_info = SOURCE_UNITS.get(source, {"symbol": "%", "type": "percent"})
    symbol = unit_info["symbol"]
    unit_type = unit_info["type"]

    if unit_type == "clock":
        return f"{value:.0f}{symbol}"
    elif unit_type == "temp":
        return f"{value:.0f}{symbol}"
    elif unit_type == "power":
        return f"{value:.0f}{symbol}"
    elif unit_type == "size":
        return f"{value:.1f}{symbol}"
    elif unit_type == "speed":
        return f"{value:.1f}{symbol}"
    else:  # percent
        return f"{value:.0f}{symbol}"
from element import ThemeElement
import sensors
from sensors import init_sensors, get_lhm_sensors, get_lhm_sensors_sync, stop_sensors
import settings
from app_path import get_resource_path


def hex_to_rgba(hex_color, opacity=100):
    """Convert hex color and opacity (0-100) to RGBA tuple."""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(255 * opacity / 100)
    return (r, g, b, a)
from canvas import CanvasPreview
from properties import PropertiesPanel
from element_list import ElementListPanel
from presets import PresetsPanel
from elements import get_custom_element
from video_background import video_background, HAS_CV2


class ThemeEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_path = None
        self.theme_name = "Untitled Theme"
        self.background_color = "#0f0f19"
        self.elements = []
        self.device = None
        self.live_preview_timer = None
        self.target_fps = 10

        # Performance monitoring
        self.frame_times = []
        self.last_frame_time = 0
        self.perf_update_timer = None
        self.process = psutil.Process()

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_levels = 50

        # Canvas update throttling (skip canvas updates during high-speed rendering)
        self._canvas_update_counter = 0
        self._canvas_update_interval = 3  # Update canvas every N frames when connected

        # Start background threads for sensor data
        start_psutil_thread()

        self.setup_ui()
        self.setup_menu()
        self.connect_signals()

        self.add_default_elements()
        self.setup_performance_monitor()

        # Load default preset if one is set
        self.load_default_preset_on_startup()

        # Auto-connect to display after window is shown
        QTimer.singleShot(500, self.auto_connect)

    def auto_connect(self):
        """Attempt to connect to display automatically on startup."""
        if self.connect_display(show_error=False):
            self.status_bar.showMessage("Auto-connected to display")
        else:
            self.status_bar.showMessage("Display not found - click Connect when ready")

    def load_default_preset_on_startup(self):
        """Load the default preset if one is configured."""
        default_preset_data = self.presets_panel.get_default_preset_data()
        if default_preset_data:
            # Load without saving undo state (it's startup)
            self.theme_name = default_preset_data.get("name", "Untitled")
            self.theme_name_edit.setText(self.theme_name)
            self.background_color = default_preset_data.get("background_color", "#0f0f19")
            self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color};")
            self.canvas.set_background_color(self.background_color)

            self.elements = [
                ThemeElement.from_dict(e) for e in default_preset_data.get("elements", [])
            ]
            self.element_list.set_elements(self.elements)
            self.canvas.set_elements(self.elements)

            # Load video background settings if present
            video_data = default_preset_data.get("video_background", {})
            if video_data:
                video_background.from_dict(video_data)
            else:
                video_background.clear_video()
            self._update_video_ui()

            print(f"[Startup] Loaded default preset: {self.theme_name}")

    def setup_ui(self):
        self.setWindowTitle("Thermal Engine")
        self.setMinimumSize(1200, 700)

        # Set window icon
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel with tabs for Elements and Presets
        left_panel = QTabWidget()
        left_panel.setMaximumWidth(340)

        self.element_list = ElementListPanel()
        left_panel.addTab(self.element_list, "Elements")

        self.presets_panel = PresetsPanel()
        left_panel.addTab(self.presets_panel, "Presets")

        splitter.addWidget(left_panel)

        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Theme Name:"))
        self.theme_name_edit = QLineEdit(self.theme_name)
        self.theme_name_edit.textChanged.connect(self.on_theme_name_changed)
        name_layout.addWidget(self.theme_name_edit)

        name_layout.addWidget(QLabel("Background:"))
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(30, 25)
        self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color};")
        self.bg_color_btn.clicked.connect(self.choose_background_color)
        name_layout.addWidget(self.bg_color_btn)

        name_layout.addWidget(QLabel("Video:"))
        self.video_btn = QPushButton("None")
        self.video_btn.setFixedWidth(80)
        self.video_btn.clicked.connect(self.choose_video_background)
        name_layout.addWidget(self.video_btn)

        self.video_fit_combo = QComboBox()
        self.video_fit_combo.addItem("Fit Height", "fit_height")
        self.video_fit_combo.addItem("Fit Width", "fit_width")
        self.video_fit_combo.setFixedWidth(90)
        self.video_fit_combo.currentIndexChanged.connect(self.on_video_fit_changed)
        self.video_fit_combo.setEnabled(False)
        name_layout.addWidget(self.video_fit_combo)

        self.clear_video_btn = QPushButton("Clear")
        self.clear_video_btn.setFixedWidth(50)
        self.clear_video_btn.clicked.connect(self.clear_video_background)
        self.clear_video_btn.setEnabled(False)
        name_layout.addWidget(self.clear_video_btn)

        name_layout.addStretch()

        canvas_layout.addLayout(name_layout)

        self.canvas = CanvasPreview()

        canvas_wrapper = QHBoxLayout()
        canvas_wrapper.addStretch()
        canvas_wrapper.addWidget(self.canvas)
        canvas_wrapper.addStretch()

        canvas_layout.addLayout(canvas_wrapper)
        canvas_layout.addStretch()

        splitter.addWidget(canvas_container)

        self.properties_panel = PropertiesPanel()
        self.properties_panel.setMinimumWidth(280)
        self.properties_panel.setMaximumWidth(320)
        splitter.addWidget(self.properties_panel)

        splitter.setSizes([200, 650, 300])

        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Performance indicator widgets
        self.perf_indicator = QLabel()
        self.perf_indicator.setFixedWidth(20)
        self.perf_indicator.setStyleSheet("background-color: #444; border-radius: 4px;")

        self.perf_label = QLabel("FPS: -- | CPU: --%")
        self.perf_label.setStyleSheet("padding: 2px 8px;")

        self.status_bar.addPermanentWidget(self.perf_indicator)
        self.status_bar.addPermanentWidget(self.perf_label)

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        new_action = QAction("New Theme", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_theme)
        file_menu.addAction(new_action)

        open_action = QAction("Open Theme...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_theme)
        file_menu.addAction(open_action)

        save_action = QAction("Save Theme", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_theme)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save Theme As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_theme_as)
        file_menu.addAction(save_as_action)

        save_preset_action = QAction("Save as Preset", self)
        save_preset_action.setShortcut("Ctrl+Shift+S")
        save_preset_action.triggered.connect(self.save_as_preset)
        file_menu.addAction(save_preset_action)

        file_menu.addSeparator()

        export_action = QAction("Export as Image...", self)
        export_action.triggered.connect(self.export_image)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo)
        self.undo_action.setEnabled(False)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.redo)
        self.redo_action.setEnabled(False)
        edit_menu.addAction(self.redo_action)

        display_menu = menubar.addMenu("Display")

        self.connect_action = QAction("Connect", self)
        self.connect_action.triggered.connect(self.toggle_connection)
        display_menu.addAction(self.connect_action)

        display_menu.addSeparator()

        self.send_action = QAction("Send to Display", self)
        self.send_action.setShortcut("F5")
        self.send_action.triggered.connect(self.send_to_display)
        self.send_action.setEnabled(False)
        display_menu.addAction(self.send_action)

        display_menu.addSeparator()

        fps_menu = display_menu.addMenu("Frame Rate")
        self.fps_actions = []
        for fps in [10, 20, 30]:
            action = QAction(f"{fps} FPS", self)
            action.setCheckable(True)
            action.setChecked(fps == self.target_fps)
            action.triggered.connect(lambda checked, f=fps: self.set_target_fps(f))
            fps_menu.addAction(action)
            self.fps_actions.append(action)

        display_menu.addSeparator()

        diagnose_action = QAction("Diagnose Sensors...", self)
        diagnose_action.triggered.connect(self.diagnose_sensors)
        display_menu.addAction(diagnose_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        settings_action = QAction("Preferences...", self)
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)

    def connect_signals(self):
        self.element_list.element_selected.connect(self.on_element_selected)
        self.element_list.elements_selected.connect(self.on_elements_selected)
        self.element_list.elements_will_change.connect(self.save_undo_state)
        self.element_list.elements_changed.connect(self.refresh_canvas)

        self.canvas.element_selected.connect(self.on_canvas_element_selected)
        self.canvas.elements_selected.connect(self.on_canvas_elements_selected)
        self.canvas.element_moved.connect(self.on_element_moved)
        self.canvas.element_resized.connect(self.on_element_resized)
        self.canvas.drag_started.connect(self.save_undo_state)

        self.properties_panel.property_will_change.connect(self.save_undo_state)
        self.properties_panel.property_changed.connect(self.refresh_canvas)
        self.properties_panel.property_changed.connect(self.update_element_list_name)
        self.properties_panel.alignment_will_change.connect(self.save_undo_state)
        self.properties_panel.alignment_changed.connect(self.refresh_canvas)

        self.presets_panel.preset_selected.connect(self.load_preset)
        self.presets_panel.preset_saved.connect(self.on_preset_saved)

    def setup_performance_monitor(self):
        """Setup timer to update performance stats."""
        self.perf_update_timer = QTimer(self)
        self.perf_update_timer.timeout.connect(self.update_performance_stats)
        self.perf_update_timer.start(500)  # Update every 500ms

    def update_performance_stats(self):
        """Update the performance indicator in the status bar."""
        # Calculate actual FPS from frame times
        if len(self.frame_times) >= 2:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            actual_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        else:
            actual_fps = 0

        # Get CPU usage of this process
        try:
            cpu_percent = self.process.cpu_percent(interval=None)
        except:
            cpu_percent = 0

        # Determine status color based on performance
        if not self.device:
            color = "#444"
            status = "Idle"
        elif actual_fps >= self.target_fps * 0.9:
            color = "#4CAF50"
            status = "Good"
        elif actual_fps >= self.target_fps * 0.7:
            color = "#FFC107"
            status = "Moderate"
        else:
            color = "#F44336"
            status = "High Load"

        self.perf_indicator.setStyleSheet(
            f"background-color: {color}; border-radius: 4px; min-height: 16px;"
        )

        if self.device:
            self.perf_label.setText(
                f"FPS: {actual_fps:.1f}/{self.target_fps} | CPU: {cpu_percent:.1f}% | {status}"
            )
        else:
            self.perf_label.setText("FPS: -- | CPU: --%")

        if self.device and actual_fps < self.target_fps * 0.7 and actual_fps > 0:
            self.status_bar.showMessage(
                f"Performance warning: Only achieving {actual_fps:.1f} FPS. "
                f"Consider reducing target FPS or simplifying theme.", 3000
            )

    def record_frame_time(self):
        """Record the time taken for a frame."""
        current_time = time.time()
        if self.last_frame_time > 0:
            frame_time = current_time - self.last_frame_time
            self.frame_times.append(frame_time)
            if len(self.frame_times) > 30:
                self.frame_times.pop(0)
        self.last_frame_time = current_time

    def add_default_elements(self):
        defaults = [
            ThemeElement("circle_gauge", name="cpu_temp_gauge", x=200, y=240, radius=120,
                         text="CPU TEMP", source="cpu_temp", color="#00ff96", value=45),
            ThemeElement("circle_gauge", name="cpu_load_gauge", x=480, y=240, radius=120,
                         text="CPU LOAD", source="cpu_percent", color="#00c8ff", value=30),
            ThemeElement("circle_gauge", name="gpu_load_gauge", x=760, y=240, radius=120,
                         text="GPU LOAD", source="gpu_percent", color="#c864ff", value=55),
            ThemeElement("circle_gauge", name="gpu_temp_gauge", x=1040, y=240, radius=120,
                         text="GPU TEMP", source="gpu_temp", color="#ff9632", value=62),
            ThemeElement("text", name="title", x=490, y=20, text="SYSTEM MONITOR",
                         font_size=36, color="#666680", width=300, height=50),
        ]

        self.elements = defaults
        self.element_list.set_elements(self.elements)
        self.canvas.set_elements(self.elements)

    def on_element_selected(self, idx):
        self.canvas.set_selected(idx)
        if idx >= 0 and idx < len(self.elements):
            self.properties_panel.set_element(self.elements[idx])
        else:
            self.properties_panel.set_element(None)

    def on_canvas_element_selected(self, idx):
        self.element_list.select_element(idx)
        if idx >= 0 and idx < len(self.elements):
            self.properties_panel.set_element(self.elements[idx])
        else:
            self.properties_panel.set_element(None)

    def on_elements_selected(self, indices):
        """Handle multi-selection from element list."""
        self.canvas.set_selected_indices(indices)
        if len(indices) == 1:
            self.properties_panel.set_element(self.elements[indices[0]])
        elif len(indices) > 1:
            # Show alignment panel for multiple selection
            self.properties_panel.set_multi_selection([self.elements[i] for i in indices], indices)
        else:
            self.properties_panel.set_element(None)

    def on_canvas_elements_selected(self, indices):
        """Handle multi-selection from canvas."""
        self.element_list.select_elements(indices)
        if len(indices) == 1:
            self.properties_panel.set_element(self.elements[indices[0]])
        elif len(indices) > 1:
            # Show alignment panel for multiple selection
            self.properties_panel.set_multi_selection([self.elements[i] for i in indices], indices)
        else:
            self.properties_panel.set_element(None)

    def on_element_moved(self, idx, x, y):
        if idx >= 0 and idx < len(self.elements):
            self.properties_panel.set_element(self.elements[idx])

    def on_element_resized(self, idx):
        if idx >= 0 and idx < len(self.elements):
            self.properties_panel.set_element(self.elements[idx])

    def refresh_canvas(self):
        self.canvas.set_elements(self.elements)
        self.canvas.update()

    def save_undo_state(self):
        """Save current state to undo stack."""
        state = {
            'elements': [e.to_dict() for e in self.elements],
            'background_color': self.background_color
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo_levels:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.update_undo_actions()

    def undo(self):
        """Undo the last action."""
        if not self.undo_stack:
            return

        # Save current state to redo stack
        current_state = {
            'elements': [e.to_dict() for e in self.elements],
            'background_color': self.background_color
        }
        self.redo_stack.append(current_state)

        # Restore previous state
        state = self.undo_stack.pop()
        self.elements = [ThemeElement.from_dict(e) for e in state['elements']]
        self.background_color = state['background_color']

        self.element_list.set_elements(self.elements)
        self.canvas.set_elements(self.elements)
        self.canvas.set_background_color(self.background_color)
        self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color};")
        self.properties_panel.set_element(None)
        self.canvas.set_selected_indices([])

        self.update_undo_actions()
        self.status_bar.showMessage("Undo", 1500)

    def redo(self):
        """Redo the last undone action."""
        if not self.redo_stack:
            return

        # Save current state to undo stack
        current_state = {
            'elements': [e.to_dict() for e in self.elements],
            'background_color': self.background_color
        }
        self.undo_stack.append(current_state)

        # Restore redo state
        state = self.redo_stack.pop()
        self.elements = [ThemeElement.from_dict(e) for e in state['elements']]
        self.background_color = state['background_color']

        self.element_list.set_elements(self.elements)
        self.canvas.set_elements(self.elements)
        self.canvas.set_background_color(self.background_color)
        self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color};")
        self.properties_panel.set_element(None)
        self.canvas.set_selected_indices([])

        self.update_undo_actions()
        self.status_bar.showMessage("Redo", 1500)

    def update_undo_actions(self):
        """Update enabled state of undo/redo actions."""
        self.undo_action.setEnabled(len(self.undo_stack) > 0)
        self.redo_action.setEnabled(len(self.redo_stack) > 0)

    def load_preset(self, preset_data):
        """Load a preset into the editor."""
        self.save_undo_state()

        self.theme_name = preset_data.get("name", "Untitled")
        self.theme_name_edit.setText(self.theme_name)
        self.background_color = preset_data.get("background_color", "#0f0f19")
        self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color};")
        self.canvas.set_background_color(self.background_color)

        self.elements = [
            ThemeElement.from_dict(e) for e in preset_data.get("elements", [])
        ]
        self.element_list.set_elements(self.elements)
        self.canvas.set_elements(self.elements)
        self.properties_panel.set_element(None)
        self.canvas.set_selected_indices([])

        # Load video background settings if present
        video_data = preset_data.get("video_background", {})
        if video_data:
            video_background.from_dict(video_data)
        else:
            video_background.clear_video()
        self._update_video_ui()

        self.status_bar.showMessage(f"Loaded preset: {self.theme_name}")

    def on_preset_saved(self, preset_name):
        """Called when a preset is saved."""
        self.status_bar.showMessage(f"Preset saved: {preset_name}")

    def save_as_preset(self):
        """Save current theme as a preset."""
        theme_data = {
            "name": self.theme_name,
            "background_color": self.background_color,
            "display_width": DISPLAY_WIDTH,
            "display_height": DISPLAY_HEIGHT,
            "elements": [e.to_dict() for e in self.elements],
            "video_background": video_background.to_dict()
        }
        self.presets_panel.save_preset(self.theme_name, theme_data)

    def update_element_list_name(self):
        self.element_list.refresh_list()

    def on_theme_name_changed(self, name):
        self.theme_name = name
        self.setWindowTitle(f"Thermal Engine - {name}")

    def choose_background_color(self):
        color = QColorDialog.getColor(QColor(self.background_color), self)
        if color.isValid():
            self.background_color = color.name()
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.canvas.set_background_color(color.name())

    def choose_video_background(self):
        """Select a video file for background."""
        if not HAS_CV2:
            QMessageBox.warning(
                self, "OpenCV Required",
                "Video backgrounds require OpenCV.\nRun: pip install opencv-python"
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video Background", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.webm);;All Files (*)"
        )
        if path:
            # Update UI immediately
            filename = os.path.basename(path)
            if len(filename) > 12:
                filename = filename[:10] + "..."
            self.video_btn.setText(filename)
            self.video_btn.setToolTip(path)
            self.video_fit_combo.setEnabled(True)
            self.clear_video_btn.setEnabled(True)

            # Start loading with progress callback
            self.status_bar.showMessage(f"Loading video: {os.path.basename(path)}...")

            # Start a timer to update canvas during loading
            self._video_load_timer = QTimer(self)
            self._video_load_timer.timeout.connect(self._on_video_load_tick)
            self._video_load_timer.start(100)  # Update every 100ms

            if not video_background.load_video(path, callback=self._on_video_load_progress):
                self._video_load_timer.stop()
                QMessageBox.warning(self, "Error", f"Failed to load video:\n{path}")
                self.clear_video_background()

    def _on_video_load_tick(self):
        """Timer callback during video loading."""
        self.canvas.update()
        if not video_background.is_loading:
            self._video_load_timer.stop()

    def _on_video_load_progress(self, progress, done, error):
        """Callback for video loading progress."""
        if error:
            # Use QTimer to show message box from main thread
            QTimer.singleShot(0, lambda: self._show_video_error(error))
            return

        if done and not error:
            mem_mb = video_background.memory_usage_mb
            frames = video_background.frame_count
            fps = video_background.fps
            QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                f"Video loaded: {frames} frames @ {fps:.1f}fps ({mem_mb:.1f} MB in memory)"
            ))

    def _show_video_error(self, error):
        """Show video load error (called from main thread)."""
        QMessageBox.warning(self, "Video Load Error", str(error))
        self.clear_video_background()

    def on_video_fit_changed(self, index):
        """Handle video fit mode change."""
        fit_mode = self.video_fit_combo.currentData()
        if fit_mode and fit_mode != video_background.fit_mode:
            self.status_bar.showMessage("Reloading video with new fit mode...")
            # Start timer to show loading progress
            if not hasattr(self, '_video_load_timer'):
                self._video_load_timer = QTimer(self)
                self._video_load_timer.timeout.connect(self._on_video_load_tick)
            self._video_load_timer.start(100)
            video_background.set_fit_mode(fit_mode)
        self.canvas.update()

    def clear_video_background(self):
        """Clear the video background."""
        # Stop load timer if running
        if hasattr(self, '_video_load_timer') and self._video_load_timer.isActive():
            self._video_load_timer.stop()
        video_background.clear_video()
        self.video_btn.setText("None")
        self.video_btn.setToolTip("")
        self.video_fit_combo.setEnabled(False)
        self.clear_video_btn.setEnabled(False)
        self.canvas.update()
        self.status_bar.showMessage("Video background cleared")

    def _update_video_ui(self):
        """Update video UI controls to match current video_background state."""
        if video_background.enabled:
            filename = os.path.basename(video_background.video_path)
            if len(filename) > 12:
                filename = filename[:10] + "..."
            self.video_btn.setText(filename)
            self.video_btn.setToolTip(video_background.video_path)
            self.video_fit_combo.setEnabled(True)
            self.clear_video_btn.setEnabled(True)
            # Set fit mode in combo
            idx = self.video_fit_combo.findData(video_background.fit_mode)
            if idx >= 0:
                self.video_fit_combo.setCurrentIndex(idx)
        else:
            self.video_btn.setText("None")
            self.video_btn.setToolTip("")
            self.video_fit_combo.setEnabled(False)
            self.clear_video_btn.setEnabled(False)

    def new_theme(self):
        self.theme_path = None
        self.theme_name = "Untitled Theme"
        self.theme_name_edit.setText(self.theme_name)
        self.background_color = "#0f0f19"
        self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color};")
        self.canvas.set_background_color(self.background_color)
        self.elements = []
        self.element_list.set_elements(self.elements)
        self.canvas.set_elements(self.elements)
        self.properties_panel.set_element(None)
        # Clear video background
        video_background.clear_video()
        self._update_video_ui()
        self.status_bar.showMessage("New theme created")

    def open_theme(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Theme", "",
            "Theme Files (*.json);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)

                # Validate theme schema before loading
                is_valid, errors = validate_preset_schema(data)
                if not is_valid:
                    QMessageBox.warning(self, "Invalid Theme",
                        f"Theme file has invalid format:\n{', '.join(errors[:5])}")
                    return

                self.theme_name = data.get("name", "Untitled")
                self.theme_name_edit.setText(self.theme_name)
                self.background_color = data.get("background_color", "#0f0f19")
                self.bg_color_btn.setStyleSheet(f"background-color: {self.background_color};")
                self.canvas.set_background_color(self.background_color)

                self.elements = [
                    ThemeElement.from_dict(e) for e in data.get("elements", [])
                ]
                self.element_list.set_elements(self.elements)
                self.canvas.set_elements(self.elements)

                # Load video background settings
                video_data = data.get("video_background", {})
                if video_data:
                    video_background.from_dict(video_data)
                    self._update_video_ui()
                else:
                    video_background.clear_video()
                    self._update_video_ui()

                self.theme_path = path
                self.status_bar.showMessage(f"Opened: {path}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open theme:\n{e}")

    def save_theme(self):
        if self.theme_path:
            self._save_to_path(self.theme_path)
        else:
            self.save_theme_as()

    def save_theme_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Theme", f"{self.theme_name}.json",
            "Theme Files (*.json);;All Files (*)"
        )
        if path:
            self._save_to_path(path)

    def _save_to_path(self, path):
        try:
            data = {
                "name": self.theme_name,
                "background_color": self.background_color,
                "display_width": DISPLAY_WIDTH,
                "display_height": DISPLAY_HEIGHT,
                "elements": [e.to_dict() for e in self.elements],
                "video_background": video_background.to_dict()
            }

            with open(path, 'w') as f:
                json.dump(data, f, indent=2)

            self.theme_path = path
            self.status_bar.showMessage(f"Saved: {path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save theme:\n{e}")

    def export_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", f"{self.theme_name}.png",
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if path:
            try:
                img = self.render_theme_image()
                img.save(path)
                self.status_bar.showMessage(f"Exported: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export image:\n{e}")

    def get_sensor_data(self):
        """Get sensor data from background threads (non-blocking)."""
        # Get psutil data from background thread
        psutil_data = get_psutil_data()

        data = {
            'static': 50,
            # CPU
            'cpu_percent': psutil_data['cpu_percent'],
            'cpu_temp': 0,
            'cpu_clock': 0,
            'cpu_power': 0,
            # GPU
            'gpu_percent': 0,
            'gpu_temp': 0,
            'gpu_clock': 0,
            'gpu_memory_percent': 0,
            'gpu_memory_clock': 0,
            'gpu_power': 0,
            # RAM
            'ram_percent': psutil_data['ram_percent'],
            'ram_used': psutil_data['ram_used'],
            'ram_available': psutil_data['ram_available'],
            # Network
            'net_upload': psutil_data['net_upload'],
            'net_download': psutil_data['net_download'],
        }

        # Get LHM sensor data from background thread (non-blocking)
        if sensors.HAS_LHM:
            try:
                lhm_data = get_lhm_sensors()
                if lhm_data:
                    # CPU sensors
                    if lhm_data.get('cpu_temp', 0) > 0:
                        data['cpu_temp'] = lhm_data['cpu_temp']
                    if lhm_data.get('cpu_clock', 0) > 0:
                        data['cpu_clock'] = lhm_data['cpu_clock']
                    if lhm_data.get('cpu_power', 0) > 0:
                        data['cpu_power'] = lhm_data['cpu_power']
                    # GPU sensors
                    if lhm_data.get('gpu_temp', 0) > 0:
                        data['gpu_temp'] = lhm_data['gpu_temp']
                    if lhm_data.get('gpu_percent', 0) > 0:
                        data['gpu_percent'] = lhm_data['gpu_percent']
                    if lhm_data.get('gpu_clock', 0) > 0:
                        data['gpu_clock'] = lhm_data['gpu_clock']
                    if lhm_data.get('gpu_memory_percent', 0) > 0:
                        data['gpu_memory_percent'] = lhm_data['gpu_memory_percent']
                    if lhm_data.get('gpu_memory_clock', 0) > 0:
                        data['gpu_memory_clock'] = lhm_data['gpu_memory_clock']
                    if lhm_data.get('gpu_power', 0) > 0:
                        data['gpu_power'] = lhm_data['gpu_power']
            except Exception as e:
                print(f"LHM sensor read error: {e}")

        return data

    def diagnose_sensors(self):
        """Show diagnostic information about available sensors."""
        info = []
        info.append("=== Sensor Diagnostic ===\n")
        info.append(f"LibreHardwareMonitor (subprocess): {sensors.HAS_LHM}")

        dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LibreHardwareMonitorLib.dll")
        info.append(f"DLL path: {dll_path}")
        info.append(f"DLL exists: {os.path.exists(dll_path)}")

        hidsharp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HidSharp.dll")
        info.append(f"HidSharp.dll exists: {os.path.exists(hidsharp_path)}")
        info.append("")

        if sensors.HAS_LHM:
            info.append("Subprocess sensor query (fresh poll):")
            info.append("-" * 40)
            try:
                # Use sync version for diagnostics to get fresh data
                lhm_data = get_lhm_sensors_sync()
                if lhm_data:
                    for key, value in lhm_data.items():
                        info.append(f"  {key}: {value}")
                else:
                    info.append("  (no data returned)")
            except Exception as e:
                info.append(f"  Error: {e}")
        else:
            info.append("\nLibreHardwareMonitor not working!")
            if sensors.LHM_ERROR:
                info.append(f"\nError: {sensors.LHM_ERROR}")
            info.append("\nTo fix this:")
            info.append("1. Install: pip install pythonnet clr-loader")
            info.append("2. Download LibreHardwareMonitor from:")
            info.append("   https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases")
            info.append("3. Extract and copy LibreHardwareMonitorLib.dll to:")
            info.append(f"   {os.path.dirname(os.path.abspath(__file__))}")
            info.append("4. Also copy HidSharp.dll to the same folder")
            info.append("5. Unblock both DLLs (right-click > Properties > Unblock)")
            info.append("6. Restart this application AS ADMINISTRATOR")

        info.append("\n" + "-" * 40)
        info.append("Current sensor values:")
        data = self.get_sensor_data()
        for key, value in data.items():
            info.append(f"  {key}: {value}")

        QMessageBox.information(self, "Sensor Diagnostic", "\n".join(info))

    def toggle_connection(self):
        """Toggle between connected and disconnected states."""
        if self.device:
            self.disconnect_display()
        else:
            self.connect_display()

    def connect_display(self, show_error=True):
        if not HAS_HID:
            if show_error:
                QMessageBox.warning(self, "Error", "HID library not installed.\nRun: pip install hidapi")
            return False

        try:
            self.device = hid.device()
            self.device.open(0x0416, 0x5302)

            init = bytearray(512)
            init[0:4] = bytes([0xDA, 0xDB, 0xDC, 0xDD])
            init[4] = 0x00
            init[12] = 0x01
            self.device.write(bytes([0x00]) + bytes(init))

            # Update button text to "Disconnect"
            self.connect_action.setText("Disconnect")
            self.connect_action.setText("Disconnect")
            self.send_action.setEnabled(True)

            psutil.cpu_percent(interval=None)

            self.frame_times = []
            self.last_frame_time = 0

            self.start_continuous_send()

            self.status_bar.showMessage("Connected to display - sending frames")
            return True

        except Exception as e:
            if show_error:
                QMessageBox.critical(self, "Error", f"Failed to connect:\n{e}\n\nMake sure TRCC is closed.")
            return False

    def disconnect_display(self):
        self.stop_continuous_send()

        if self.device:
            self.device.close()
            self.device = None

        self.frame_times = []
        self.last_frame_time = 0

        # Update button text to "Connect"
        self.connect_action.setText("Connect")
        self.connect_action.setText("Connect")
        self.send_action.setEnabled(False)

        self.status_bar.showMessage("Disconnected")

    def set_target_fps(self, fps):
        self.target_fps = fps
        for action in self.fps_actions:
            action.setChecked(action.text() == f"{fps} FPS")

        if self.live_preview_timer and self.live_preview_timer.isActive():
            interval = 1000 // self.target_fps
            self.live_preview_timer.setInterval(interval)

        self.status_bar.showMessage(f"Frame rate set to {fps} FPS")

    def start_continuous_send(self):
        interval = 1000 // self.target_fps
        if self.live_preview_timer is None:
            self.live_preview_timer = QTimer(self)
            self.live_preview_timer.timeout.connect(self.send_frame_with_sensors)
            self.live_preview_timer.start(interval)
        else:
            self.live_preview_timer.setInterval(interval)
            self.live_preview_timer.start()

    def stop_continuous_send(self):
        if self.live_preview_timer:
            self.live_preview_timer.stop()
            self.live_preview_timer = None

    def send_to_display(self):
        self.send_frame_with_sensors()

    def send_frame_with_sensors(self):
        if not self.device:
            return

        try:
            sensor_data = self.get_sensor_data()

            for element in self.elements:
                # Don't override value for static source - let user control it
                if element.source != "static" and element.source in sensor_data:
                    element.value = sensor_data[element.source]

            img = self.render_theme_image()
            jpeg_data = self.image_to_jpeg(img)
            self.send_jpeg_frame(jpeg_data)

            # Throttle canvas updates to reduce CPU usage
            # Only update Qt canvas every N frames when sending to display
            self._canvas_update_counter += 1
            if self._canvas_update_counter >= self._canvas_update_interval:
                self._canvas_update_counter = 0
                self.canvas.set_elements(self.elements)
                self.canvas.update()

            self.record_frame_time()

        except Exception as e:
            print(f"Send error: {e}")
            self.status_bar.showMessage(f"Error: {e}")

    _font_cache = None

    def _build_font_cache(self):
        """Build a cache of font family names to file paths from Windows Registry."""
        if self._font_cache is not None:
            return self._font_cache

        self._font_cache = {}
        font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')

        try:
            import winreg
            reg_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
            ]

            for hkey, subkey in reg_paths:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                font_name = name.replace(" (TrueType)", "").replace(" (OpenType)", "")

                                if not os.path.isabs(value):
                                    value = os.path.join(font_dir, value)

                                if os.path.exists(value):
                                    self._font_cache[font_name.lower()] = value

                                i += 1
                            except OSError:
                                break
                except OSError:
                    pass
        except ImportError:
            pass

        return self._font_cache

    def get_font_path(self, font_family, bold=False, italic=False):
        font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
        font_cache = self._build_font_cache()

        if bold and italic:
            variants = [
                f"{font_family} Bold Italic",
                f"{font_family} Bold Oblique",
                f"{font_family}",
            ]
        elif bold:
            variants = [
                f"{font_family} Bold",
                f"{font_family}",
            ]
        elif italic:
            variants = [
                f"{font_family} Italic",
                f"{font_family} Oblique",
                f"{font_family}",
            ]
        else:
            variants = [
                f"{font_family}",
                f"{font_family} Regular",
            ]

        for variant in variants:
            if variant.lower() in font_cache:
                return font_cache[variant.lower()]

        font_name_lower = font_family.lower()
        for cached_name, cached_path in font_cache.items():
            if font_name_lower in cached_name or cached_name.startswith(font_name_lower):
                return cached_path

        try:
            font_name_clean = font_family.lower().replace(' ', '')
            for filename in os.listdir(font_dir):
                if filename.lower().endswith(('.ttf', '.otf')):
                    if font_name_clean in filename.lower().replace(' ', ''):
                        return os.path.join(font_dir, filename)
        except:
            pass

        return os.path.join(font_dir, 'arial.ttf')

    def get_pil_font(self, element, size_override=None):
        """Get a PIL font with caching for performance."""
        size = size_override or element.font_size
        cache_key = (element.font_family, element.font_bold, element.font_italic, size)

        with _pil_font_cache_lock:
            if cache_key in _pil_font_cache:
                return _pil_font_cache[cache_key]

        try:
            font_path = self.get_font_path(element.font_family, element.font_bold, element.font_italic)
            font = ImageFont.truetype(font_path, size)
        except:
            font = ImageFont.load_default()

        with _pil_font_cache_lock:
            # Limit cache size to prevent memory bloat
            if len(_pil_font_cache) > 100:
                # Remove oldest entries (simple FIFO)
                keys_to_remove = list(_pil_font_cache.keys())[:20]
                for k in keys_to_remove:
                    del _pil_font_cache[k]
            _pil_font_cache[cache_key] = font

        return font

    def render_theme_image(self):
        # Use video frame as background if enabled, otherwise solid color
        if video_background.enabled:
            video_frame = video_background.get_frame_pil()
            if video_frame:
                img = video_frame.copy().convert('RGBA')
            else:
                img = Image.new('RGBA', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=self.background_color)
        else:
            img = Image.new('RGBA', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=self.background_color)

        # Render in reverse order so elements at top of list appear in front
        for element in reversed(self.elements):
            self.render_element_with_opacity(img, element)

        # Convert back to RGB for output
        return img.convert('RGB')

    def render_element_with_opacity(self, img, element):
        """Render an element with opacity support using alpha compositing."""
        font = self.get_pil_font(element)
        font_small = self.get_pil_font(element, int(element.font_size * 0.6))

        # Get opacity values
        color_opacity = getattr(element, 'color_opacity', 100)
        bg_opacity = getattr(element, 'background_color_opacity', 100)

        if element.type == "circle_gauge":
            self.render_circle_gauge_rgba(img, element, font, font_small, color_opacity, bg_opacity)
        elif element.type == "bar_gauge":
            self.render_bar_gauge_rgba(img, element, font, color_opacity, bg_opacity)
        elif element.type == "text":
            self.render_text_rgba(img, element, font, color_opacity)
        elif element.type == "rectangle":
            self.render_rectangle_rgba(img, element, color_opacity)
        elif element.type == "clock":
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
            temp_element = ThemeElement(
                text=current_time, x=element.x, y=element.y,
                font_family=element.font_family, font_size=element.font_size,
                font_bold=element.font_bold, font_italic=element.font_italic,
                text_align=element.text_align, color=element.color,
                color_opacity=color_opacity,
                width=element.width, height=element.height, clip=element.clip
            )
            self.render_text_rgba(img, temp_element, font, color_opacity)
        elif element.type == "analog_clock":
            self.render_analog_clock_rgba(img, element, color_opacity, bg_opacity)
        elif element.type == "image":
            if element.image_path:
                # Validate image path is safe
                safe, resolved_path, err = is_safe_path(element.image_path, allow_absolute=True)
                if not safe or not os.path.exists(element.image_path):
                    if not safe:
                        print(f"Unsafe image path blocked: {element.image_path} - {err}")
                    return
                try:
                    overlay = Image.open(element.image_path).convert('RGBA')
                    if element.scale_proportionally:
                        overlay.thumbnail((element.width, element.height), Image.Resampling.LANCZOS)
                    else:
                        overlay = overlay.resize((element.width, element.height), Image.Resampling.LANCZOS)
                    # Apply opacity to image
                    if color_opacity < 100:
                        alpha = overlay.split()[3]
                        alpha = alpha.point(lambda x: int(x * color_opacity / 100))
                        overlay.putalpha(alpha)
                    img.paste(overlay, (element.x, element.y), overlay)
                except Exception as e:
                    print(f"Image load error: {e}")
        else:
            custom = get_custom_element(element.type)
            if custom and custom.get('render_image'):
                try:
                    draw = ImageDraw.Draw(img)
                    custom['render_image'](draw, img, element)
                except Exception as e:
                    print(f"Custom element render error: {e}")

    def render_rectangle_rgba(self, img, element, opacity):
        """Render a rectangle with opacity."""
        if opacity >= 100:
            draw = ImageDraw.Draw(img)
            draw.rectangle(
                [element.x, element.y, element.x + element.width, element.y + element.height],
                fill=element.color
            )
        else:
            # Create overlay with alpha
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            rgba = hex_to_rgba(element.color, opacity)
            overlay_draw.rectangle(
                [element.x, element.y, element.x + element.width, element.y + element.height],
                fill=rgba
            )
            img.alpha_composite(overlay)

    def render_text_rgba(self, img, element, font, opacity):
        """Render text with opacity."""
        # Determine text to display based on source
        source = getattr(element, 'source', 'static')
        if source and source != 'static':
            # Display sensor value, optionally with label
            value_text = get_value_with_unit(element.value, source)
            if element.text:
                text = f"{element.text}: {value_text}"
            else:
                text = value_text
        else:
            text = element.text

        # Create a temporary draw to measure text
        temp_draw = ImageDraw.Draw(img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if element.text_align == "left":
            x = element.x
        elif element.text_align == "right":
            x = element.x + element.width - text_width
        else:
            x = element.x + (element.width - text_width) // 2

        y = element.y + (element.height - text_height) // 2

        if opacity >= 100 and not element.clip:
            temp_draw.text((x, y), text, fill=element.color, font=font)
        else:
            # Create overlay with alpha
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            rgba = hex_to_rgba(element.color, opacity)
            overlay_draw.text((x, y), text, fill=rgba, font=font)

            if element.clip:
                # Create mask for clipping
                mask = Image.new('L', img.size, 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rectangle([element.x, element.y, element.x + element.width, element.y + element.height], fill=255)
                # Apply mask to overlay
                overlay_alpha = overlay.split()[3]
                overlay_alpha = Image.composite(overlay_alpha, Image.new('L', img.size, 0), mask)
                overlay.putalpha(overlay_alpha)

            img.alpha_composite(overlay)

    def render_text(self, draw, img, element, font):
        # Determine text to display based on source
        source = getattr(element, 'source', 'static')
        if source and source != 'static':
            # Display sensor value, optionally with label
            value_text = get_value_with_unit(element.value, source)
            if element.text:
                text = f"{element.text}: {value_text}"
            else:
                text = value_text
        else:
            text = element.text

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if element.text_align == "left":
            x = element.x
        elif element.text_align == "right":
            x = element.x + element.width - text_width
        else:
            x = element.x + (element.width - text_width) // 2

        y = element.y + (element.height - text_height) // 2

        if element.clip:
            mask = Image.new('L', img.size, 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rectangle([element.x, element.y, element.x + element.width, element.y + element.height], fill=255)

            temp = Image.new('RGBA', img.size, (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp)
            temp_draw.text((x, y), text, fill=element.color, font=font)

            r, g, b = img.split()
            tr, tg, tb, ta = temp.split()

            r = Image.composite(tr, r, mask)
            g = Image.composite(tg, g, mask)
            b = Image.composite(tb, b, mask)

            img_temp = Image.merge('RGB', (r, g, b))
            img.paste(img_temp)
        else:
            draw.text((x, y), text, fill=element.color, font=font)

    def render_circle_gauge_rgba(self, img, element, font, font_small, color_opacity, bg_opacity):
        """Render circle gauge with opacity support."""
        x, y = element.x, element.y
        radius = element.radius
        value = element.value

        # Determine color based on value thresholds (if enabled)
        auto_color = getattr(element, 'auto_color_change', True)
        if auto_color:
            if "temp" in element.source:
                if value < 60:
                    color = element.color
                elif value < 80:
                    color = "#ffcc00"
                else:
                    color = "#ff3232"
            else:
                if value < 70:
                    color = element.color
                elif value < 90:
                    color = "#ffcc00"
                else:
                    color = "#ff3232"
        else:
            color = element.color

        # Create overlay for drawing with transparency
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw background arc
        bg_rgba = hex_to_rgba(element.background_color, bg_opacity)
        arc_width = 18
        for i in range(arc_width):
            r = radius - i
            draw.arc(
                [x - r, y - r, x + r, y + r],
                start=135, end=405,
                fill=bg_rgba, width=2
            )

        # Draw value arc
        color_rgba = hex_to_rgba(color, color_opacity)
        sweep = int(270 * min(value, 100) / 100)
        end_angle = 135 + sweep

        for i in range(arc_width):
            r = radius - i
            draw.arc(
                [x - r, y - r, x + r, y + r],
                start=135, end=end_angle,
                fill=color_rgba, width=2
            )

        # Draw value text (white, full opacity)
        value_text = get_value_with_unit(value, element.source)
        bbox = draw.textbbox((0, 0), value_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            (x - text_width // 2, y - text_height // 2 - 10),
            value_text, fill=(255, 255, 255, 255), font=font
        )

        # Draw label text
        label_rgba = hex_to_rgba(color, color_opacity)
        bbox = draw.textbbox((0, 0), element.text, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (x - text_width // 2, y + radius // 3),
            element.text, fill=label_rgba, font=font_small
        )

        # Composite onto main image
        img.alpha_composite(overlay)

    def render_bar_gauge_rgba(self, img, element, font, color_opacity, bg_opacity):
        """Render bar gauge with opacity support."""
        x, y = element.x, element.y
        value = element.value
        width, height = element.width, element.height

        # Determine color based on value (if auto color enabled)
        auto_color = getattr(element, 'auto_color_change', True)
        if auto_color:
            if value < 70:
                color = element.color
            elif value < 90:
                color = "#ffcc00"
            else:
                color = "#ff3232"
        else:
            color = element.color

        rounded = getattr(element, 'rounded_corners', False)
        corner_radius = height // 2 if rounded else 0

        # Create overlay for drawing with transparency
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw background
        bg_rgba = hex_to_rgba(element.background_color, bg_opacity)
        if rounded:
            draw.rounded_rectangle(
                [x, y, x + width, y + height],
                radius=corner_radius,
                fill=bg_rgba
            )
        else:
            draw.rectangle(
                [x, y, x + width, y + height],
                fill=bg_rgba
            )

        # Draw fill
        fill_width = int(width * min(value, 100) / 100)
        if fill_width > 0:
            fill_rgba = hex_to_rgba(color, color_opacity)
            if rounded:
                draw.rounded_rectangle(
                    [x, y, x + fill_width, y + height],
                    radius=corner_radius,
                    fill=fill_rgba
                )
            else:
                draw.rectangle(
                    [x, y, x + fill_width, y + height],
                    fill=fill_rgba
                )

        # Draw text based on bar_text_mode and bar_text_position
        bar_text_mode = getattr(element, 'bar_text_mode', 'full')
        bar_text_position = getattr(element, 'bar_text_position', 'inside')

        if bar_text_mode != 'none':
            value_text = get_value_with_unit(value, element.source)
            if bar_text_mode == 'full':
                display_text = f"{element.text}: {value_text}"
            else:  # value_only
                display_text = value_text

            # Use smaller font for bar text
            font_small = self.get_pil_font(element, int(element.font_size * 0.6))
            bbox = draw.textbbox((0, 0), display_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            if bar_text_position == 'inside':
                text_x = x + (width - text_width) // 2
                text_y = y + (height - text_height) // 2
            else:  # left
                text_x = x - text_width - 10  # 10px spacing
                text_y = y + (height - text_height) // 2

            draw.text((text_x, text_y), display_text, fill=(255, 255, 255, 255), font=font_small)

        # Composite onto main image
        img.alpha_composite(overlay)

    def render_analog_clock_rgba(self, img, element, color_opacity, bg_opacity):
        """Render analog clock with opacity support."""
        import math
        import datetime

        x, y = element.x, element.y
        radius = element.radius

        # Get options
        show_seconds = getattr(element, 'show_seconds_hand', True)
        show_border = getattr(element, 'show_clock_border', True)
        face_style = getattr(element, 'clock_face_style', 'numbers')
        smooth = getattr(element, 'smooth_animation', True)

        # Get current time
        now = datetime.datetime.now()
        hours = now.hour % 12
        minutes = now.minute
        seconds = now.second
        microseconds = now.microsecond

        if smooth:
            second_angle = (seconds + microseconds / 1000000) * 6
            minute_angle = (minutes + seconds / 60) * 6
            hour_angle = (hours + minutes / 60) * 30
        else:
            second_angle = seconds * 6
            minute_angle = minutes * 6
            hour_angle = hours * 30 + minutes * 0.5

        # Create overlay for drawing with transparency
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Get colors
        color_rgba = hex_to_rgba(element.color, color_opacity)
        bg_rgba = hex_to_rgba(element.background_color, bg_opacity)

        # Draw clock face background
        if show_border:
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=bg_rgba, outline=color_rgba, width=2
            )
        else:
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=bg_rgba
            )

        # Get font for numbers
        font = self.get_pil_font(element, int(getattr(element, 'font_size', 14) * 0.8))

        # Draw tick marks or numbers
        for i in range(12):
            angle_rad = math.radians(i * 30 - 90)

            if face_style == 'numbers':
                num = i if i > 0 else 12
                text = str(num)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                text_radius = radius * 0.78
                tx = x + text_radius * math.cos(angle_rad) - text_width / 2
                ty = y + text_radius * math.sin(angle_rad) - text_height / 2

                draw.text((tx, ty), text, fill=color_rgba, font=font)

            elif face_style == 'ticks':
                inner_radius = radius * 0.85
                outer_radius = radius * 0.95

                if i % 3 == 0:
                    inner_radius = radius * 0.75
                    tick_width = 3
                else:
                    tick_width = 1

                x1 = x + inner_radius * math.cos(angle_rad)
                y1 = y + inner_radius * math.sin(angle_rad)
                x2 = x + outer_radius * math.cos(angle_rad)
                y2 = y + outer_radius * math.sin(angle_rad)

                draw.line([(x1, y1), (x2, y2)], fill=color_rgba, width=tick_width)

        # Draw hour hand
        hour_length = radius * 0.5
        hour_rad = math.radians(hour_angle - 90)
        hx = x + hour_length * math.cos(hour_rad)
        hy = y + hour_length * math.sin(hour_rad)
        draw.line([(x, y), (hx, hy)], fill=color_rgba, width=4)

        # Draw minute hand
        minute_length = radius * 0.7
        minute_rad = math.radians(minute_angle - 90)
        mx = x + minute_length * math.cos(minute_rad)
        my = y + minute_length * math.sin(minute_rad)
        draw.line([(x, y), (mx, my)], fill=color_rgba, width=3)

        # Draw second hand (optional)
        if show_seconds:
            second_length = radius * 0.85
            second_rad = math.radians(second_angle - 90)
            sx = x + second_length * math.cos(second_rad)
            sy = y + second_length * math.sin(second_rad)
            # Red second hand
            second_rgba = (255, 80, 80, int(255 * color_opacity / 100))
            draw.line([(x, y), (sx, sy)], fill=second_rgba, width=2)

        # Draw center dot
        center_radius = 4
        draw.ellipse(
            [x - center_radius, y - center_radius, x + center_radius, y + center_radius],
            fill=color_rgba
        )

        # Composite onto main image
        img.alpha_composite(overlay)

    def render_circle_gauge(self, draw, element, font, font_small):
        x, y = element.x, element.y
        radius = element.radius
        value = element.value

        auto_color = getattr(element, 'auto_color_change', True)
        if auto_color:
            if "temp" in element.source:
                if value < 60:
                    color = element.color
                elif value < 80:
                    color = "#ffcc00"
                else:
                    color = "#ff3232"
            else:
                if value < 70:
                    color = element.color
                elif value < 90:
                    color = "#ffcc00"
                else:
                    color = "#ff3232"
        else:
            color = element.color

        arc_width = 18
        for i in range(arc_width):
            r = radius - i
            draw.arc(
                [x - r, y - r, x + r, y + r],
                start=135, end=405,
                fill=element.background_color, width=2
            )

        sweep = int(270 * min(value, 100) / 100)
        end_angle = 135 + sweep

        for i in range(arc_width):
            r = radius - i
            draw.arc(
                [x - r, y - r, x + r, y + r],
                start=135, end=end_angle,
                fill=color, width=2
            )

        value_text = get_value_with_unit(value, element.source)
        bbox = draw.textbbox((0, 0), value_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            (x - text_width // 2, y - text_height // 2 - 10),
            value_text, fill="white", font=font
        )

        bbox = draw.textbbox((0, 0), element.text, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (x - text_width // 2, y + radius // 3),
            element.text, fill=color, font=font_small
        )

    def render_bar_gauge(self, draw, element, font):
        x, y = element.x, element.y
        value = element.value
        width, height = element.width, element.height

        auto_color = getattr(element, 'auto_color_change', True)
        if auto_color:
            if value < 70:
                color = element.color
            elif value < 90:
                color = "#ffcc00"
            else:
                color = "#ff3232"
        else:
            color = element.color

        rounded = getattr(element, 'rounded_corners', False)
        gradient = getattr(element, 'gradient_fill', False)
        corner_radius = height // 2 if rounded else 0

        # Draw background
        if rounded:
            draw.rounded_rectangle(
                [x, y, x + width, y + height],
                radius=corner_radius,
                fill=element.background_color
            )
        else:
            draw.rectangle(
                [x, y, x + width, y + height],
                fill=element.background_color
            )

        # Draw fill
        fill_width = int(width * min(value, 100) / 100)
        if fill_width > 0:
            if gradient:
                # Parse color for gradient
                if color.startswith('#'):
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                else:
                    r, g, b = 0, 255, 150

                # Create gradient fill using multiple thin rectangles
                for i in range(fill_width):
                    t = i / fill_width if fill_width > 0 else 0
                    # Lighter at top, darker at bottom
                    gr = min(255, int(r + (255 - r) * 0.3 * (1 - t)))
                    gg = min(255, int(g + (255 - g) * 0.3 * (1 - t)))
                    gb = min(255, int(b + (255 - b) * 0.3 * (1 - t)))
                    draw.line([(x + i, y), (x + i, y + height)], fill=(gr, gg, gb))

            else:
                if rounded:
                    draw.rounded_rectangle(
                        [x, y, x + fill_width, y + height],
                        radius=corner_radius,
                        fill=color
                    )
                else:
                    draw.rectangle(
                        [x, y, x + fill_width, y + height],
                        fill=color
                    )

        # Draw text based on bar_text_mode and bar_text_position
        bar_text_mode = getattr(element, 'bar_text_mode', 'full')
        bar_text_position = getattr(element, 'bar_text_position', 'inside')

        if bar_text_mode != 'none':
            value_text = get_value_with_unit(value, element.source)
            if bar_text_mode == 'full':
                display_text = f"{element.text}: {value_text}"
            else:  # value_only
                display_text = value_text

            # Use smaller font for bar text
            font_small = self.get_pil_font(element, int(element.font_size * 0.6))
            bbox = draw.textbbox((0, 0), display_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            if bar_text_position == 'inside':
                text_x = x + (width - text_width) // 2
                text_y = y + (height - text_height) // 2
            else:  # left
                text_x = x - text_width - 10  # 10px spacing
                text_y = y + (height - text_height) // 2

            draw.text((text_x, text_y), display_text, fill="white", font=font_small)

    def image_to_jpeg(self, img, quality=80):
        """Convert image to JPEG bytes with optimized settings."""
        buffer = io.BytesIO()
        # Use quality=80 and optimize=False for faster encoding
        # The LCD display doesn't need highest quality
        img.save(buffer, format='JPEG', quality=quality, optimize=False, subsampling=2)
        return buffer.getvalue()

    def send_jpeg_frame(self, jpeg_data):
        MAGIC = bytes([0xDA, 0xDB, 0xDC, 0xDD])

        header = bytearray(512)
        header[0:4] = MAGIC
        header[4] = 0x02
        header[8:12] = bytes([0x00, 0x05, 0xE0, 0x01])
        header[12] = 0x02

        jpeg_len = len(jpeg_data)
        header[16] = jpeg_len & 0xFF
        header[17] = (jpeg_len >> 8) & 0xFF
        header[18] = (jpeg_len >> 16) & 0xFF
        header[19] = (jpeg_len >> 24) & 0xFF

        first_chunk = min(len(jpeg_data), 492)
        header[20:20 + first_chunk] = jpeg_data[:first_chunk]

        self.device.write(bytes([0x00]) + bytes(header))

        offset = first_chunk
        while offset < len(jpeg_data):
            chunk = jpeg_data[offset:offset + 512]
            if len(chunk) < 512:
                chunk = chunk + bytes(512 - len(chunk))
            self.device.write(bytes([0x00]) + chunk)
            offset += 512

    def show_settings(self):
        """Show the settings dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Preferences")
        dialog.setMinimumWidth(350)

        layout = QVBoxLayout(dialog)

        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)

        self.launch_at_login_cb = QCheckBox("Launch at Windows startup")
        self.launch_at_login_cb.setChecked(settings.get_setting("launch_at_login", True))
        startup_layout.addWidget(self.launch_at_login_cb)

        self.launch_minimized_cb = QCheckBox("Start minimized to system tray")
        self.launch_minimized_cb.setChecked(settings.get_setting("launch_minimized", True))
        startup_layout.addWidget(self.launch_minimized_cb)

        layout.addWidget(startup_group)

        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)

        self.minimize_to_tray_cb = QCheckBox("Minimize to system tray instead of taskbar")
        self.minimize_to_tray_cb.setChecked(settings.get_setting("minimize_to_tray", True))
        behavior_layout.addWidget(self.minimize_to_tray_cb)

        self.close_to_tray_cb = QCheckBox("Close button minimizes to tray")
        self.close_to_tray_cb.setChecked(settings.get_setting("close_to_tray", True))
        behavior_layout.addWidget(self.close_to_tray_cb)

        layout.addWidget(behavior_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save settings
            settings.set_setting("launch_at_login", self.launch_at_login_cb.isChecked())
            settings.set_setting("launch_minimized", self.launch_minimized_cb.isChecked())
            settings.set_setting("minimize_to_tray", self.minimize_to_tray_cb.isChecked())
            settings.set_setting("close_to_tray", self.close_to_tray_cb.isChecked())

            # Apply autostart setting
            settings.apply_autostart_setting()

            self.status_bar.showMessage("Settings saved", 2000)

    def changeEvent(self, event):
        """Handle window state changes (minimize)."""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                if settings.get_setting("minimize_to_tray", True):
                    # Hide window and show only in tray
                    QTimer.singleShot(0, self.hide)
        super().changeEvent(event)

    def closeEvent(self, event):
        # Check if we should minimize to tray instead of closing
        if settings.get_setting("close_to_tray", True) and hasattr(self, 'tray_icon'):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Thermal Engine",
                "Application minimized to system tray. Right-click tray icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            return

        self.disconnect_display()

        if self.perf_update_timer:
            self.perf_update_timer.stop()

        if hasattr(self, '_video_load_timer') and self._video_load_timer.isActive():
            self._video_load_timer.stop()

        # Stop background threads
        stop_psutil_thread()
        stop_sensors()
        video_background.close()

        event.accept()
