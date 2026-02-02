"""
ElementListPanel - Element list management widget.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPixmap, QIcon

from constants import ELEMENT_TYPES, DEFAULT_ELEMENT_PROPS
from element import ThemeElement
from elements import get_custom_element


class ReorderableListWidget(QListWidget):
    """QListWidget that properly handles drag-and-drop reordering and multi-select."""
    items_reordered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.items_reordered.emit()


class ElementListPanel(QWidget):
    element_selected = Signal(int)  # Single selection (backwards compat)
    elements_selected = Signal(list)  # Multi-selection
    elements_will_change = Signal()  # Emitted before any modification (for undo)
    elements_changed = Signal()

    def __init__(self):
        super().__init__()
        self.elements = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Elements")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title)

        add_layout = QHBoxLayout()

        self.add_combo = QComboBox()
        self.add_combo.addItems(ELEMENT_TYPES)
        add_layout.addWidget(self.add_combo)

        self.add_btn = QPushButton("+ Add")
        self.add_btn.clicked.connect(self.add_element)
        add_layout.addWidget(self.add_btn)

        layout.addLayout(add_layout)

        self.list_widget = ReorderableListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.list_widget.items_reordered.connect(self.on_items_reordered)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self.duplicate_element)
        btn_layout.addWidget(self.duplicate_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_element)
        btn_layout.addWidget(self.remove_btn)

        layout.addLayout(btn_layout)

        move_layout = QHBoxLayout()

        self.up_btn = QPushButton("Move Up")
        self.up_btn.clicked.connect(self.move_up)
        move_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("Move Down")
        self.down_btn.clicked.connect(self.move_down)
        move_layout.addWidget(self.down_btn)

        layout.addLayout(move_layout)

    def set_elements(self, elements):
        self.elements = elements
        self.refresh_list()

    def get_element_icon(self, element_type):
        """Create a colored icon based on element type."""
        # Color and shape mapping for element types
        type_styles = {
            "circle_gauge": ("#00ff96", "circle"),
            "bar_gauge": ("#00aaff", "rect"),
            "text": ("#ffffff", "text"),
            "rectangle": ("#ff9900", "rect"),
            "clock": ("#ffff00", "clock"),
            "analog_clock": ("#ffff00", "clock"),
            "image": ("#ff66ff", "image"),
            "line_chart": ("#00ff96", "chart"),
            "gif": ("#ff66ff", "image"),
        }

        style = type_styles.get(element_type, ("#888888", "rect"))
        color, shape = style

        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(QBrush(QColor(color).darker(150)))

        if shape == "circle":
            painter.drawEllipse(2, 2, 16, 16)
        elif shape == "rect":
            painter.drawRect(2, 4, 16, 12)
        elif shape == "text":
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.drawText(2, 16, "T")
        elif shape == "clock":
            painter.drawEllipse(2, 2, 16, 16)
            painter.drawLine(10, 10, 10, 5)
            painter.drawLine(10, 10, 14, 10)
        elif shape == "image":
            painter.drawRect(2, 4, 16, 12)
            painter.drawLine(2, 12, 8, 8)
            painter.drawLine(8, 8, 12, 11)
            painter.drawLine(12, 11, 18, 6)
        elif shape == "chart":
            painter.drawLine(2, 16, 6, 10)
            painter.drawLine(6, 10, 10, 12)
            painter.drawLine(10, 12, 14, 6)
            painter.drawLine(14, 6, 18, 8)

        painter.end()
        return QIcon(pixmap)

    def get_friendly_label(self, element):
        """Create a user-friendly label for an element."""
        type_names = {
            "circle_gauge": "Gauge",
            "bar_gauge": "Bar",
            "text": "Text",
            "rectangle": "Rectangle",
            "clock": "Clock",
            "analog_clock": "Analog Clock",
            "image": "Image",
            "line_chart": "Chart",
            "gif": "GIF",
        }

        type_label = type_names.get(element.type, element.type.replace("_", " ").title())

        # Get a descriptive part from the element
        if hasattr(element, 'source') and element.source and element.source != "static":
            source_label = element.source.replace("_", " ").upper()
            return f"{type_label} - {source_label}"
        elif hasattr(element, 'text') and element.text:
            return f"{type_label} - {element.text}"
        else:
            return f"{type_label} - {element.name}"

    def refresh_list(self):
        current_row = self.list_widget.currentRow()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, element in enumerate(self.elements):
            icon = self.get_element_icon(element.type)
            label = self.get_friendly_label(element)
            item = QListWidgetItem(icon, label)
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store original index
            self.list_widget.addItem(item)
        if current_row >= 0 and current_row < len(self.elements):
            self.list_widget.setCurrentRow(current_row)
        self.list_widget.blockSignals(False)

    def on_items_reordered(self):
        """Handle drag-and-drop reordering of elements."""
        self.elements_will_change.emit()
        # Rebuild elements list based on visual order
        new_order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            original_idx = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(self.elements[original_idx])

        self.elements[:] = new_order

        # Update stored indices to match new order
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setData(Qt.ItemDataRole.UserRole, i)

        self.elements_changed.emit()

    def add_element(self):
        self.elements_will_change.emit()
        element_type = self.add_combo.currentText()

        # Check for custom element defaults
        custom = get_custom_element(element_type)
        if custom:
            props = custom.get('defaults', {}).copy()
        else:
            props = DEFAULT_ELEMENT_PROPS.get(element_type, {}).copy()
        props["name"] = f"{element_type}_{len(self.elements) + 1}"

        element = ThemeElement(element_type, **props)
        self.elements.append(element)
        self.refresh_list()

        self.list_widget.setCurrentRow(len(self.elements) - 1)
        self.elements_changed.emit()

    def remove_element(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.elements_will_change.emit()
            del self.elements[idx]
            self.refresh_list()
            self.elements_changed.emit()

    def duplicate_element(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            self.elements_will_change.emit()
            original = self.elements[idx]
            new_element = ThemeElement.from_dict(original.to_dict())
            new_element.name = f"{original.name}_copy"
            new_element.x += 20
            new_element.y += 20
            self.elements.append(new_element)
            self.refresh_list()
            self.list_widget.setCurrentRow(len(self.elements) - 1)
            self.elements_changed.emit()

    def move_up(self):
        idx = self.list_widget.currentRow()
        if idx > 0:
            self.elements_will_change.emit()
            self.elements[idx], self.elements[idx - 1] = self.elements[idx - 1], self.elements[idx]
            self.refresh_list()
            self.list_widget.setCurrentRow(idx - 1)
            self.elements_changed.emit()

    def move_down(self):
        idx = self.list_widget.currentRow()
        if idx >= 0 and idx < len(self.elements) - 1:
            self.elements_will_change.emit()
            self.elements[idx], self.elements[idx + 1] = self.elements[idx + 1], self.elements[idx]
            self.refresh_list()
            self.list_widget.setCurrentRow(idx + 1)
            self.elements_changed.emit()

    def on_selection_changed(self):
        selected_indices = [self.list_widget.row(item) for item in self.list_widget.selectedItems()]
        selected_indices.sort()

        # Emit both signals for compatibility
        if len(selected_indices) == 1:
            self.element_selected.emit(selected_indices[0])
        else:
            self.element_selected.emit(-1)  # -1 indicates multi-select or none
        self.elements_selected.emit(selected_indices)

    def select_element(self, idx):
        """Select a single element (backwards compatible)."""
        self.list_widget.blockSignals(True)
        self.list_widget.clearSelection()
        if idx >= 0 and idx < self.list_widget.count():
            self.list_widget.setCurrentRow(idx)
        self.list_widget.blockSignals(False)

    def select_elements(self, indices):
        """Select multiple elements by their indices."""
        self.list_widget.blockSignals(True)
        self.list_widget.clearSelection()
        for idx in indices:
            if 0 <= idx < self.list_widget.count():
                item = self.list_widget.item(idx)
                item.setSelected(True)
        self.list_widget.blockSignals(False)
