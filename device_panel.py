"""
DevicePanel - Sidebar panel showing connected and available devices.

Cards have three visual states:
  - Disconnected (gray)
  - Connected (green border)
  - Active/Editing (blue accent, highlighted)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer


class DeviceCard(QFrame):
    """A card representing a single device with status and actions."""

    connect_clicked = Signal(int, int)       # vid, pid
    disconnect_clicked = Signal(int, int)    # vid, pid
    card_clicked = Signal(str)               # device_key — session switch

    def __init__(self, device_info, is_connected=False, parent=None):
        super().__init__(parent)
        self._vid = device_info["vid"]
        self._pid = device_info["pid"]
        self._name = device_info["name"]
        self._width = device_info["width"]
        self._height = device_info["height"]
        self._connected = is_connected
        self._active = False  # Whether this is the currently-edited session
        self.device_key = f"{self._vid:04x}:{self._pid:04x}"

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Top row: status dot + device name
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        top_row.addWidget(self._dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet("font-weight: bold; font-size: 12px; border: none; background: transparent;")
        top_row.addWidget(self._name_label)
        top_row.addStretch()

        layout.addLayout(top_row)

        # Resolution (indented to align with name)
        self._res_label = QLabel(f"{self._width} x {self._height}")
        self._res_label.setStyleSheet("font-size: 10px; color: #888; border: none; background: transparent;")
        self._res_label.setContentsMargins(14, 0, 0, 0)
        layout.addWidget(self._res_label)

        # Action button row
        self._btn_row = QHBoxLayout()
        self._btn_row.setSpacing(4)

        self._btn = QPushButton()
        self._btn.setFixedHeight(24)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.clicked.connect(self._on_btn_clicked)
        self._btn_row.addWidget(self._btn)

        # Disconnect button (only visible when connected)
        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setFixedHeight(24)
        self._disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self._disconnect_btn.setVisible(False)
        self._btn_row.addWidget(self._disconnect_btn)

        layout.addLayout(self._btn_row)

    def _apply_style(self):
        if self._connected and self._active:
            # Active/Editing state — blue accent
            self.setStyleSheet(
                "DeviceCard { background-color: #1a2a3a; border: 2px solid #0078d4; border-radius: 6px; }"
            )
            self._dot.setStyleSheet(
                "background-color: #4CAF50; border-radius: 4px; border: none;"
            )
            self._btn.setText("Editing")
            self._btn.setEnabled(False)
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4; color: #fff; border: none; border-radius: 4px;
                    font-size: 10px; padding: 2px 6px;
                }
            """)
            self._disconnect_btn.setVisible(True)
            self._disconnect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #444; color: #ccc; border: none; border-radius: 4px;
                    font-size: 10px; padding: 2px 6px;
                }
                QPushButton:hover { background-color: #F44336; color: #fff; }
            """)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self._connected:
            # Connected but not active — green border, clickable to switch
            self.setStyleSheet(
                "DeviceCard { background-color: #2a2f2a; border: 1px solid #4CAF50; border-radius: 6px; }"
            )
            self._dot.setStyleSheet(
                "background-color: #4CAF50; border-radius: 4px; border: none;"
            )
            self._btn.setText("Switch to")
            self._btn.setEnabled(True)
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: #2a5a2a; color: #ccc; border: none; border-radius: 4px;
                    font-size: 10px; padding: 2px 6px;
                }
                QPushButton:hover { background-color: #3a7a3a; color: #fff; }
            """)
            self._disconnect_btn.setVisible(True)
            self._disconnect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #444; color: #ccc; border: none; border-radius: 4px;
                    font-size: 10px; padding: 2px 6px;
                }
                QPushButton:hover { background-color: #F44336; color: #fff; }
            """)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # Disconnected state
            self.setStyleSheet(
                "DeviceCard { background-color: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 6px; }"
            )
            self._dot.setStyleSheet(
                "background-color: #666; border-radius: 4px; border: none;"
            )
            self._btn.setText("Connect")
            self._btn.setEnabled(True)
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4; color: #fff; border: none; border-radius: 4px;
                    font-size: 10px; padding: 2px 6px;
                }
                QPushButton:hover { background-color: #1a8ae8; }
            """)
            self._disconnect_btn.setVisible(False)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_btn_clicked(self):
        if self._connected and not self._active:
            # Switch to this session
            self.card_clicked.emit(self.device_key)
        elif not self._connected:
            self.connect_clicked.emit(self._vid, self._pid)

    def _on_disconnect_clicked(self):
        self.disconnect_clicked.emit(self._vid, self._pid)

    def mousePressEvent(self, event):
        """Clicking on the card body also switches session if connected."""
        if event.button() == Qt.MouseButton.LeftButton and self._connected and not self._active:
            self.card_clicked.emit(self.device_key)
        else:
            super().mousePressEvent(event)

    def set_connected(self, connected):
        self._connected = connected
        self._apply_style()

    def set_active(self, active):
        self._active = active
        self._apply_style()


class DevicePanel(QWidget):
    """Full-height sidebar showing available/connected devices."""

    connect_requested = Signal(int, int)       # vid, pid
    disconnect_requested = Signal(int, int)    # vid, pid
    device_selected = Signal(str)              # device_key — session switch

    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self._device_manager = device_manager
        self._cards = []
        self._active_device_key = None

        self.setFixedWidth(160)  # default until cards are populated
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._build_ui()

        # Auto-scan shortly after construction (after auto-connect at 500ms)
        QTimer.singleShot(600, self.refresh_devices)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Container with right border
        container = QFrame()
        container.setStyleSheet("QFrame { border-right: 1px solid #3a3a3a; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 10, 8, 8)
        container_layout.setSpacing(8)

        # Header
        header = QLabel("Devices")
        header.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        container_layout.addWidget(header)

        # Scroll area for device cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                width: 6px; background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #555; border-radius: 3px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self._card_container = QWidget()
        self._card_container.setStyleSheet("background: transparent;")
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(0, 0, 0, 0)
        self._card_layout.setSpacing(6)
        self._card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Placeholder label
        self._empty_label = QLabel("No devices found")
        self._empty_label.setStyleSheet("color: #666; font-size: 11px; border: none;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._card_layout.addWidget(self._empty_label)

        self._scroll.setWidget(self._card_container)
        container_layout.addWidget(self._scroll, 1)

        # Scan button
        self._scan_btn = QPushButton("Scan for Devices")
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #333; color: #ccc; border: 1px solid #3a3a3a;
                border-radius: 4px; padding: 6px; font-size: 11px;
            }
            QPushButton:hover { background-color: #3a3a3a; color: #fff; }
        """)
        self._scan_btn.clicked.connect(self.refresh_devices)
        container_layout.addWidget(self._scan_btn)

        outer.addWidget(container)

    def refresh_devices(self):
        """Re-enumerate HID devices and rebuild the card list."""
        devices = self._device_manager.enumerate_devices()
        connected_keys = self._device_manager.connected_keys

        # Clear old cards
        for card in self._cards:
            self._card_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # Show/hide placeholder
        self._empty_label.setVisible(len(devices) == 0)

        for dev_info in devices:
            device_key = f"{dev_info['vid']:04x}:{dev_info['pid']:04x}"
            is_connected = device_key in connected_keys
            card = DeviceCard(dev_info, is_connected=is_connected)
            card.set_active(device_key == self._active_device_key)
            card.connect_clicked.connect(self._on_card_connect)
            card.disconnect_clicked.connect(self._on_card_disconnect)
            card.card_clicked.connect(self._on_card_selected)
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)
            self._cards.append(card)

        self._update_panel_width()

    def update_connection_state(self):
        """Update card visuals to reflect current connection state without re-enumerating."""
        connected_keys = self._device_manager.connected_keys
        for card in self._cards:
            is_connected = card.device_key in connected_keys
            card.set_connected(is_connected)
            card.set_active(card.device_key == self._active_device_key)

    def update_active_device(self, device_key):
        """Set which device card is highlighted as the active editing session."""
        self._active_device_key = device_key
        for card in self._cards:
            card.set_active(card.device_key == device_key)

    def _update_panel_width(self):
        """Set panel width to fit the widest card."""
        if not self._cards:
            self.setFixedWidth(160)
            return
        for card in self._cards:
            card.adjustSize()
        widest = max(card.sizeHint().width() for card in self._cards)
        # Add container margins (8+8) + border (1) + scroll area padding
        self.setFixedWidth(max(widest + 18, 160))

    def _on_card_connect(self, vid, pid):
        self.connect_requested.emit(vid, pid)

    def _on_card_disconnect(self, vid, pid):
        self.disconnect_requested.emit(vid, pid)

    def _on_card_selected(self, device_key):
        self.device_selected.emit(device_key)
