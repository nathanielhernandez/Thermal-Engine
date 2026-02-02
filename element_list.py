"""
ElementListPanel - Element list management widget with group support.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QInputDialog, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPixmap, QIcon

from constants import ELEMENT_TYPES, DEFAULT_ELEMENT_PROPS
from element import ThemeElement
from elements import get_custom_element


class ElementTreeWidget(QTreeWidget):
    """QTreeWidget with drag-drop reordering support."""
    items_reordered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setExpandsOnDoubleClick(False)

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
        self.groups = {}  # group_name -> list of element indices
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

        self.tree_widget = ElementTreeWidget()
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree_widget.items_reordered.connect(self.on_items_reordered)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree_widget)

        btn_layout = QHBoxLayout()

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self.duplicate_element)
        btn_layout.addWidget(self.duplicate_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_element)
        btn_layout.addWidget(self.remove_btn)

        layout.addLayout(btn_layout)

        group_layout = QHBoxLayout()

        self.group_btn = QPushButton("Group")
        self.group_btn.clicked.connect(self.group_selected)
        self.group_btn.setToolTip("Group selected elements (Ctrl+G)")
        group_layout.addWidget(self.group_btn)

        self.ungroup_btn = QPushButton("Ungroup")
        self.ungroup_btn.clicked.connect(self.ungroup_selected)
        self.ungroup_btn.setToolTip("Ungroup selected elements (Ctrl+Shift+G)")
        group_layout.addWidget(self.ungroup_btn)

        layout.addLayout(group_layout)

        move_layout = QHBoxLayout()

        self.up_btn = QPushButton("Move Up")
        self.up_btn.clicked.connect(self.move_up)
        move_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("Move Down")
        self.down_btn.clicked.connect(self.move_down)
        move_layout.addWidget(self.down_btn)

        layout.addLayout(move_layout)

    def show_context_menu(self, position):
        """Show context menu for tree items."""
        menu = QMenu(self)

        selected = self.tree_widget.selectedItems()
        if selected:
            # Check if any selected item is a group
            has_group = any(item.data(0, Qt.ItemDataRole.UserRole + 1) == "group" for item in selected)
            has_elements = any(item.data(0, Qt.ItemDataRole.UserRole + 1) == "element" for item in selected)

            if has_elements and len(selected) > 1:
                group_action = menu.addAction("Group Selected")
                group_action.triggered.connect(self.group_selected)

            if has_group:
                ungroup_action = menu.addAction("Ungroup")
                ungroup_action.triggered.connect(self.ungroup_selected)

            menu.addSeparator()

            if has_elements or has_group:
                rename_action = menu.addAction("Rename...")
                rename_action.triggered.connect(self.rename_selected)

            menu.addSeparator()

            duplicate_action = menu.addAction("Duplicate")
            duplicate_action.triggered.connect(self.duplicate_element)

            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(self.remove_element)

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def set_elements(self, elements):
        self.elements = elements
        self.refresh_list()

    def get_element_icon(self, element_type):
        """Create a colored icon based on element type."""
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

    def get_group_icon(self):
        """Create a folder icon for groups."""
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffa500"), 2))
        painter.setBrush(QBrush(QColor("#ffa500").darker(150)))
        # Draw folder shape
        painter.drawRect(2, 6, 16, 12)
        painter.drawRect(2, 4, 8, 4)
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

        if hasattr(element, 'source') and element.source and element.source != "static":
            source_label = element.source.replace("_", " ").upper()
            return f"{type_label} - {source_label}"
        elif hasattr(element, 'text') and element.text:
            return f"{type_label} - {element.text}"
        else:
            return f"{type_label} - {element.name}"

    def refresh_list(self):
        """Refresh the tree widget to reflect current elements and groups."""
        self.tree_widget.blockSignals(True)
        self.tree_widget.clear()

        # Collect groups and ungrouped elements
        groups = {}  # group_name -> [(index, element), ...]
        ungrouped = []  # [(index, element), ...]

        for i, element in enumerate(self.elements):
            if element.group:
                if element.group not in groups:
                    groups[element.group] = []
                groups[element.group].append((i, element))
            else:
                ungrouped.append((i, element))

        # Add groups first
        for group_name in sorted(groups.keys()):
            group_item = QTreeWidgetItem([group_name])
            group_item.setIcon(0, self.get_group_icon())
            group_item.setData(0, Qt.ItemDataRole.UserRole, group_name)  # Store group name
            group_item.setData(0, Qt.ItemDataRole.UserRole + 1, "group")  # Mark as group
            group_item.setExpanded(True)
            self.tree_widget.addTopLevelItem(group_item)

            # Add elements in this group
            for idx, element in groups[group_name]:
                icon = self.get_element_icon(element.type)
                label = self.get_friendly_label(element)
                child_item = QTreeWidgetItem([label])
                child_item.setIcon(0, icon)
                child_item.setData(0, Qt.ItemDataRole.UserRole, idx)  # Store element index
                child_item.setData(0, Qt.ItemDataRole.UserRole + 1, "element")  # Mark as element
                group_item.addChild(child_item)

        # Add ungrouped elements
        for idx, element in ungrouped:
            icon = self.get_element_icon(element.type)
            label = self.get_friendly_label(element)
            item = QTreeWidgetItem([label])
            item.setIcon(0, icon)
            item.setData(0, Qt.ItemDataRole.UserRole, idx)  # Store element index
            item.setData(0, Qt.ItemDataRole.UserRole + 1, "element")  # Mark as element
            self.tree_widget.addTopLevelItem(item)

        self.tree_widget.blockSignals(False)

    def get_selected_element_indices(self):
        """Get indices of all selected elements (including those in selected groups)."""
        indices = []
        for item in self.tree_widget.selectedItems():
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "element":
                idx = item.data(0, Qt.ItemDataRole.UserRole)
                if idx not in indices:
                    indices.append(idx)
            elif item_type == "group":
                # Add all children of the group
                for i in range(item.childCount()):
                    child = item.child(i)
                    idx = child.data(0, Qt.ItemDataRole.UserRole)
                    if idx not in indices:
                        indices.append(idx)
        return sorted(indices)

    def on_items_reordered(self):
        """Handle drag-and-drop reordering."""
        self.elements_will_change.emit()
        # Rebuild elements list and group assignments based on tree structure
        new_elements = []

        def process_item(item, group_name=None):
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "group":
                grp_name = item.data(0, Qt.ItemDataRole.UserRole)
                for i in range(item.childCount()):
                    process_item(item.child(i), grp_name)
            elif item_type == "element":
                idx = item.data(0, Qt.ItemDataRole.UserRole)
                element = self.elements[idx]
                element.group = group_name
                new_elements.append(element)

        for i in range(self.tree_widget.topLevelItemCount()):
            process_item(self.tree_widget.topLevelItem(i))

        self.elements[:] = new_elements
        self.refresh_list()
        self.elements_changed.emit()

    def add_element(self):
        self.elements_will_change.emit()
        element_type = self.add_combo.currentText()

        custom = get_custom_element(element_type)
        if custom:
            props = custom.get('defaults', {}).copy()
        else:
            props = DEFAULT_ELEMENT_PROPS.get(element_type, {}).copy()
        props["name"] = f"{element_type}_{len(self.elements) + 1}"

        element = ThemeElement(element_type, **props)
        self.elements.append(element)
        self.refresh_list()
        self.elements_changed.emit()

    def remove_element(self):
        indices = self.get_selected_element_indices()
        if indices:
            self.elements_will_change.emit()
            # Remove in reverse order to maintain indices
            for idx in sorted(indices, reverse=True):
                del self.elements[idx]
            self.refresh_list()
            self.elements_changed.emit()

    def duplicate_element(self):
        indices = self.get_selected_element_indices()
        if indices:
            self.elements_will_change.emit()
            for idx in indices:
                original = self.elements[idx]
                new_element = ThemeElement.from_dict(original.to_dict())
                new_element.name = f"{original.name}_copy"
                new_element.x += 20
                new_element.y += 20
                self.elements.append(new_element)
            self.refresh_list()
            self.elements_changed.emit()

    def group_selected(self):
        """Group selected elements together."""
        indices = self.get_selected_element_indices()
        if len(indices) < 2:
            return

        # Ask for group name
        name, ok = QInputDialog.getText(self, "Create Group", "Group name:")
        if not ok or not name.strip():
            return

        name = name.strip()
        self.elements_will_change.emit()

        # Assign group to selected elements
        for idx in indices:
            self.elements[idx].group = name

        self.refresh_list()
        self.elements_changed.emit()

    def ungroup_selected(self):
        """Ungroup selected elements or groups."""
        self.elements_will_change.emit()

        for item in self.tree_widget.selectedItems():
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "group":
                # Ungroup all children
                group_name = item.data(0, Qt.ItemDataRole.UserRole)
                for element in self.elements:
                    if element.group == group_name:
                        element.group = None
            elif item_type == "element":
                idx = item.data(0, Qt.ItemDataRole.UserRole)
                self.elements[idx].group = None

        self.refresh_list()
        self.elements_changed.emit()

    def rename_selected(self):
        """Rename selected group or element."""
        selected = self.tree_widget.selectedItems()
        if not selected:
            return

        item = selected[0]
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == "group":
            old_name = item.data(0, Qt.ItemDataRole.UserRole)
            new_name, ok = QInputDialog.getText(self, "Rename Group", "New name:", text=old_name)
            if ok and new_name.strip() and new_name.strip() != old_name:
                self.elements_will_change.emit()
                new_name = new_name.strip()
                for element in self.elements:
                    if element.group == old_name:
                        element.group = new_name
                self.refresh_list()
                self.elements_changed.emit()
        elif item_type == "element":
            idx = item.data(0, Qt.ItemDataRole.UserRole)
            element = self.elements[idx]
            new_name, ok = QInputDialog.getText(self, "Rename Element", "New name:", text=element.name)
            if ok and new_name.strip():
                self.elements_will_change.emit()
                element.name = new_name.strip()
                self.refresh_list()
                self.elements_changed.emit()

    def move_up(self):
        indices = self.get_selected_element_indices()
        if not indices or min(indices) == 0:
            return

        self.elements_will_change.emit()
        for idx in indices:
            self.elements[idx], self.elements[idx - 1] = self.elements[idx - 1], self.elements[idx]
        self.refresh_list()
        self.elements_changed.emit()

    def move_down(self):
        indices = self.get_selected_element_indices()
        if not indices or max(indices) >= len(self.elements) - 1:
            return

        self.elements_will_change.emit()
        for idx in reversed(indices):
            self.elements[idx], self.elements[idx + 1] = self.elements[idx + 1], self.elements[idx]
        self.refresh_list()
        self.elements_changed.emit()

    def on_selection_changed(self):
        indices = self.get_selected_element_indices()

        # Emit both signals for compatibility
        if len(indices) == 1:
            self.element_selected.emit(indices[0])
        else:
            self.element_selected.emit(-1)  # -1 indicates multi-select or none
        self.elements_selected.emit(indices)

    def select_element(self, idx):
        """Select a single element by index."""
        self.tree_widget.blockSignals(True)
        self.tree_widget.clearSelection()

        def find_and_select(parent_item=None):
            if parent_item is None:
                count = self.tree_widget.topLevelItemCount()
                for i in range(count):
                    item = self.tree_widget.topLevelItem(i)
                    if find_and_select(item):
                        return True
            else:
                item_type = parent_item.data(0, Qt.ItemDataRole.UserRole + 1)
                if item_type == "element":
                    if parent_item.data(0, Qt.ItemDataRole.UserRole) == idx:
                        parent_item.setSelected(True)
                        return True
                elif item_type == "group":
                    for i in range(parent_item.childCount()):
                        if find_and_select(parent_item.child(i)):
                            return True
            return False

        find_and_select()
        self.tree_widget.blockSignals(False)

    def select_elements(self, indices):
        """Select multiple elements by their indices."""
        self.tree_widget.blockSignals(True)
        self.tree_widget.clearSelection()

        def select_matching(parent_item=None):
            if parent_item is None:
                count = self.tree_widget.topLevelItemCount()
                for i in range(count):
                    select_matching(self.tree_widget.topLevelItem(i))
            else:
                item_type = parent_item.data(0, Qt.ItemDataRole.UserRole + 1)
                if item_type == "element":
                    if parent_item.data(0, Qt.ItemDataRole.UserRole) in indices:
                        parent_item.setSelected(True)
                elif item_type == "group":
                    for i in range(parent_item.childCount()):
                        select_matching(parent_item.child(i))

        select_matching()
        self.tree_widget.blockSignals(False)

    # Keep old list_widget reference for compatibility
    @property
    def list_widget(self):
        return self.tree_widget
