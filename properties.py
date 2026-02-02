"""
PropertiesPanel - Element property editing widget.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QColorDialog, QFileDialog, QComboBox,
    QFormLayout, QScrollArea, QFrame, QCheckBox, QPushButton,
    QStyledItemDelegate, QStyle, QSlider
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPixmap, QFontDatabase

from constants import DISPLAY_WIDTH, DISPLAY_HEIGHT, DATA_SOURCES, DATA_SOURCES_CATEGORIZED


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
        self.setup_ui()

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
        self.scroll_area = scroll

        self.props_widget = QWidget()
        self.props_layout = QFormLayout(self.props_widget)
        self.props_layout.setSpacing(8)
        self.props_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_property_changed)
        self.name_label = QLabel("Name:")
        self.props_layout.addRow(self.name_label, self.name_edit)

        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, DISPLAY_WIDTH)
        self.x_spin.valueChanged.connect(self.on_property_changed)
        self.x_label = QLabel("X:")
        self.props_layout.addRow(self.x_label, self.x_spin)

        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, DISPLAY_HEIGHT)
        self.y_spin.valueChanged.connect(self.on_property_changed)
        self.y_label = QLabel("Y:")
        self.props_layout.addRow(self.y_label, self.y_spin)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, DISPLAY_WIDTH)
        self.width_spin.valueChanged.connect(self.on_property_changed)
        self.width_label = QLabel("Width:")
        self.props_layout.addRow(self.width_label, self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, DISPLAY_HEIGHT)
        self.height_spin.valueChanged.connect(self.on_property_changed)
        self.height_label = QLabel("Height:")
        self.props_layout.addRow(self.height_label, self.height_spin)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(20, 300)
        self.radius_spin.valueChanged.connect(self.on_property_changed)
        self.radius_label = QLabel("Radius:")
        self.props_layout.addRow(self.radius_label, self.radius_spin)

        # Color with opacity
        color_layout = QHBoxLayout()
        color_layout.setSpacing(5)
        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(40)
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)

        self.color_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.color_opacity_slider.setRange(0, 100)
        self.color_opacity_slider.setValue(100)
        self.color_opacity_slider.valueChanged.connect(self.on_color_opacity_changed)
        color_layout.addWidget(self.color_opacity_slider)

        self.color_opacity_label = QLabel("100%")
        self.color_opacity_label.setFixedWidth(35)
        color_layout.addWidget(self.color_opacity_label)

        self.color_widget = QWidget()
        self.color_widget.setLayout(color_layout)
        self.color_label = QLabel("Color:")
        self.props_layout.addRow(self.color_label, self.color_widget)

        # Background color with opacity
        bg_color_layout = QHBoxLayout()
        bg_color_layout.setSpacing(5)
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedWidth(40)
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        bg_color_layout.addWidget(self.bg_color_btn)

        self.bg_color_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_color_opacity_slider.setRange(0, 100)
        self.bg_color_opacity_slider.setValue(100)
        self.bg_color_opacity_slider.valueChanged.connect(self.on_bg_color_opacity_changed)
        bg_color_layout.addWidget(self.bg_color_opacity_slider)

        self.bg_color_opacity_label = QLabel("100%")
        self.bg_color_opacity_label.setFixedWidth(35)
        bg_color_layout.addWidget(self.bg_color_opacity_label)

        self.bg_color_widget = QWidget()
        self.bg_color_widget.setLayout(bg_color_layout)
        self.bg_color_label = QLabel("BG Color:")
        self.props_layout.addRow(self.bg_color_label, self.bg_color_widget)

        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.on_property_changed)
        self.text_label = QLabel("Text:")
        self.props_layout.addRow(self.text_label, self.text_edit)

        self.font_family_combo = QComboBox()
        self.font_family_combo.setItemDelegate(FontPreviewDelegate(self.font_family_combo))
        self.font_family_combo.setMaxVisibleItems(15)
        self.load_system_fonts()
        self.font_family_combo.currentTextChanged.connect(self.on_property_changed)
        self.font_family_label = QLabel("Font:")
        self.props_layout.addRow(self.font_family_label, self.font_family_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.valueChanged.connect(self.on_property_changed)
        self.font_size_label = QLabel("Font Size:")
        self.props_layout.addRow(self.font_size_label, self.font_size_spin)

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
        self.font_style_label = QLabel("Style:")
        self.props_layout.addRow(self.font_style_label, self.font_style_widget)

        align_layout = QHBoxLayout()
        self.align_left_btn = QPushButton("L")
        self.align_left_btn.setCheckable(True)
        self.align_left_btn.setFixedWidth(30)
        self.align_left_btn.clicked.connect(lambda: self.set_alignment("left"))
        align_layout.addWidget(self.align_left_btn)

        self.align_center_btn = QPushButton("C")
        self.align_center_btn.setCheckable(True)
        self.align_center_btn.setFixedWidth(30)
        self.align_center_btn.clicked.connect(lambda: self.set_alignment("center"))
        align_layout.addWidget(self.align_center_btn)

        self.align_right_btn = QPushButton("R")
        self.align_right_btn.setCheckable(True)
        self.align_right_btn.setFixedWidth(30)
        self.align_right_btn.clicked.connect(lambda: self.set_alignment("right"))
        align_layout.addWidget(self.align_right_btn)
        align_layout.addStretch()

        self.align_widget = QWidget()
        self.align_widget.setLayout(align_layout)
        self.align_label = QLabel("Align:")
        self.props_layout.addRow(self.align_label, self.align_widget)

        self.clip_checkbox = QCheckBox("Clip content to boundary")
        self.clip_checkbox.stateChanged.connect(self.on_property_changed)
        self.clip_label = QLabel("Clip:")
        self.props_layout.addRow(self.clip_label, self.clip_checkbox)

        self.source_combo = QComboBox()
        self.setup_source_combo()
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        self.source_label = QLabel("Source:")
        self.props_layout.addRow(self.source_label, self.source_combo)

        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0, 100)
        self.value_spin.valueChanged.connect(self.on_property_changed)
        self.value_label = QLabel("Preview Value:")
        self.props_layout.addRow(self.value_label, self.value_spin)

        self.image_path_edit = QLineEdit()
        self.image_path_edit.textChanged.connect(self.on_property_changed)
        self.image_browse_btn = QPushButton("Browse...")
        self.image_browse_btn.clicked.connect(self.browse_image)

        image_layout = QHBoxLayout()
        image_layout.addWidget(self.image_path_edit)
        image_layout.addWidget(self.image_browse_btn)

        self.image_widget = QWidget()
        self.image_widget.setLayout(image_layout)
        self.image_label = QLabel("Image:")
        self.props_layout.addRow(self.image_label, self.image_widget)

        self.scale_proportionally_check = QCheckBox("Scale Proportionally")
        self.scale_proportionally_check.setToolTip("When enabled, resizing maintains aspect ratio")
        self.scale_proportionally_check.stateChanged.connect(self.on_property_changed)
        self.scale_proportionally_label = QLabel("")
        self.props_layout.addRow(self.scale_proportionally_label, self.scale_proportionally_check)

        # Line chart options
        self.show_background_check = QCheckBox("Show Background")
        self.show_background_check.stateChanged.connect(self.on_property_changed)
        self.show_background_label = QLabel("")
        self.props_layout.addRow(self.show_background_label, self.show_background_check)

        self.show_label_check = QCheckBox("Show Label")
        self.show_label_check.stateChanged.connect(self.on_property_changed)
        self.show_label_label = QLabel("")
        self.props_layout.addRow(self.show_label_label, self.show_label_check)

        self.show_gradient_check = QCheckBox("Show Gradient Fill")
        self.show_gradient_check.stateChanged.connect(self.on_property_changed)
        self.show_gradient_label = QLabel("")
        self.props_layout.addRow(self.show_gradient_label, self.show_gradient_check)

        # Bar gauge options
        self.rounded_corners_check = QCheckBox("Rounded Corners")
        self.rounded_corners_check.stateChanged.connect(self.on_property_changed)
        self.rounded_corners_label = QLabel("")
        self.props_layout.addRow(self.rounded_corners_label, self.rounded_corners_check)

        self.gradient_fill_check = QCheckBox("Gradient Fill")
        self.gradient_fill_check.stateChanged.connect(self.on_property_changed)
        self.gradient_fill_label = QLabel("")
        self.props_layout.addRow(self.gradient_fill_label, self.gradient_fill_check)

        # Bar gauge text options
        self.bar_text_mode_combo = QComboBox()
        self.bar_text_mode_combo.addItem("Label + Value", "full")
        self.bar_text_mode_combo.addItem("Value Only", "value_only")
        self.bar_text_mode_combo.addItem("Hidden", "none")
        self.bar_text_mode_combo.currentIndexChanged.connect(self.on_property_changed)
        self.bar_text_mode_label = QLabel("Text:")
        self.props_layout.addRow(self.bar_text_mode_label, self.bar_text_mode_combo)

        self.bar_text_position_combo = QComboBox()
        self.bar_text_position_combo.addItem("Inside Bar", "inside")
        self.bar_text_position_combo.addItem("Left of Bar", "left")
        self.bar_text_position_combo.currentIndexChanged.connect(self.on_property_changed)
        self.bar_text_position_label = QLabel("Position:")
        self.props_layout.addRow(self.bar_text_position_label, self.bar_text_position_combo)

        # Gauge options
        self.auto_color_change_check = QCheckBox("Auto Color (warn/critical)")
        self.auto_color_change_check.setToolTip("Automatically change color at warning (70%) and critical (90%) thresholds")
        self.auto_color_change_check.stateChanged.connect(self.on_property_changed)
        self.auto_color_change_label = QLabel("")
        self.props_layout.addRow(self.auto_color_change_label, self.auto_color_change_check)

        # GIF options
        self.gif_path_edit = QLineEdit()
        self.gif_path_edit.textChanged.connect(self.on_property_changed)
        self.gif_browse_btn = QPushButton("Browse...")
        self.gif_browse_btn.clicked.connect(self.browse_gif)

        gif_layout = QHBoxLayout()
        gif_layout.addWidget(self.gif_path_edit)
        gif_layout.addWidget(self.gif_browse_btn)

        self.gif_widget = QWidget()
        self.gif_widget.setLayout(gif_layout)
        self.gif_label = QLabel("GIF:")
        self.props_layout.addRow(self.gif_label, self.gif_widget)

        self.scale_mode_combo = QComboBox()
        self.scale_mode_combo.addItem("Fit (maintain ratio)", "fit")
        self.scale_mode_combo.addItem("Fill (crop excess)", "fill")
        self.scale_mode_combo.addItem("Stretch", "stretch")
        self.scale_mode_combo.currentIndexChanged.connect(self.on_property_changed)
        self.scale_mode_label = QLabel("Scale:")
        self.props_layout.addRow(self.scale_mode_label, self.scale_mode_combo)

        # Digital clock time format options
        self.time_format_combo = QComboBox()
        self.time_format_combo.addItem("24-Hour (Military)", "24h")
        self.time_format_combo.addItem("12-Hour (Standard)", "12h")
        self.time_format_combo.currentIndexChanged.connect(self.on_property_changed)
        self.time_format_label = QLabel("Time Format:")
        self.props_layout.addRow(self.time_format_label, self.time_format_combo)

        self.show_am_pm_check = QCheckBox("Show AM/PM")
        self.show_am_pm_check.stateChanged.connect(self.on_property_changed)
        self.show_am_pm_label = QLabel("")
        self.props_layout.addRow(self.show_am_pm_label, self.show_am_pm_check)

        self.show_seconds_check = QCheckBox("Show Seconds")
        self.show_seconds_check.stateChanged.connect(self.on_property_changed)
        self.show_seconds_label = QLabel("")
        self.props_layout.addRow(self.show_seconds_label, self.show_seconds_check)

        self.show_leading_zero_check = QCheckBox("Show Leading Zero (09 vs 9)")
        self.show_leading_zero_check.stateChanged.connect(self.on_property_changed)
        self.show_leading_zero_label = QLabel("")
        self.props_layout.addRow(self.show_leading_zero_label, self.show_leading_zero_check)

        # Analog clock options
        self.show_seconds_hand_check = QCheckBox("Show Seconds Hand")
        self.show_seconds_hand_check.stateChanged.connect(self.on_property_changed)
        self.show_seconds_hand_label = QLabel("")
        self.props_layout.addRow(self.show_seconds_hand_label, self.show_seconds_hand_check)

        self.show_clock_border_check = QCheckBox("Show Clock Border")
        self.show_clock_border_check.stateChanged.connect(self.on_property_changed)
        self.show_clock_border_label = QLabel("")
        self.props_layout.addRow(self.show_clock_border_label, self.show_clock_border_check)

        self.clock_face_style_combo = QComboBox()
        self.clock_face_style_combo.addItem("Numbers (1-12)", "numbers")
        self.clock_face_style_combo.addItem("Tick Marks", "ticks")
        self.clock_face_style_combo.addItem("None", "none")
        self.clock_face_style_combo.currentIndexChanged.connect(self.on_property_changed)
        self.clock_face_style_label = QLabel("Face Style:")
        self.props_layout.addRow(self.clock_face_style_label, self.clock_face_style_combo)

        self.smooth_animation_check = QCheckBox("Smooth Animation")
        self.smooth_animation_check.stateChanged.connect(self.on_property_changed)
        self.smooth_animation_label = QLabel("")
        self.props_layout.addRow(self.smooth_animation_label, self.smooth_animation_check)

        scroll.setWidget(self.props_widget)
        layout.addWidget(scroll)

        # Multi-selection alignment panel
        self.alignment_widget = QWidget()
        alignment_layout = QVBoxLayout(self.alignment_widget)
        alignment_layout.setContentsMargins(10, 10, 10, 10)

        self.multi_select_label = QLabel("Multiple Elements Selected")
        self.multi_select_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #0096ff;")
        alignment_layout.addWidget(self.multi_select_label)

        self.selection_count_label = QLabel("0 elements")
        self.selection_count_label.setStyleSheet("color: #888; margin-bottom: 15px;")
        alignment_layout.addWidget(self.selection_count_label)

        # Horizontal alignment section
        h_align_label = QLabel("Horizontal Alignment")
        h_align_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        alignment_layout.addWidget(h_align_label)

        h_align_buttons = QHBoxLayout()
        self.align_h_left_btn = QPushButton("Left")
        self.align_h_left_btn.clicked.connect(self.align_left)
        h_align_buttons.addWidget(self.align_h_left_btn)

        self.align_h_center_btn = QPushButton("Center")
        self.align_h_center_btn.clicked.connect(self.align_h_center)
        h_align_buttons.addWidget(self.align_h_center_btn)

        self.align_h_right_btn = QPushButton("Right")
        self.align_h_right_btn.clicked.connect(self.align_right)
        h_align_buttons.addWidget(self.align_h_right_btn)
        alignment_layout.addLayout(h_align_buttons)

        # Vertical alignment section
        v_align_label = QLabel("Vertical Alignment")
        v_align_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        alignment_layout.addWidget(v_align_label)

        v_align_buttons = QHBoxLayout()
        self.align_v_top_btn = QPushButton("Top")
        self.align_v_top_btn.clicked.connect(self.align_top)
        v_align_buttons.addWidget(self.align_v_top_btn)

        self.align_v_middle_btn = QPushButton("Middle")
        self.align_v_middle_btn.clicked.connect(self.align_v_middle)
        v_align_buttons.addWidget(self.align_v_middle_btn)

        self.align_v_bottom_btn = QPushButton("Bottom")
        self.align_v_bottom_btn.clicked.connect(self.align_bottom)
        v_align_buttons.addWidget(self.align_v_bottom_btn)
        alignment_layout.addLayout(v_align_buttons)

        # Distribution section
        dist_label = QLabel("Distribute")
        dist_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        alignment_layout.addWidget(dist_label)

        dist_buttons = QHBoxLayout()
        self.dist_h_btn = QPushButton("Horizontal")
        self.dist_h_btn.clicked.connect(self.distribute_horizontal)
        dist_buttons.addWidget(self.dist_h_btn)

        self.dist_v_btn = QPushButton("Vertical")
        self.dist_v_btn.clicked.connect(self.distribute_vertical)
        dist_buttons.addWidget(self.dist_v_btn)
        alignment_layout.addLayout(dist_buttons)

        alignment_layout.addStretch()
        layout.addWidget(self.alignment_widget)
        self.alignment_widget.setVisible(False)

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
                added.add(font)

        self.font_family_combo.insertSeparator(len(added))

        for family in sorted(families):
            if family not in added and not family.startswith("@"):
                self.font_family_combo.addItem(family)

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

        if self.current_element:
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
                "color": True, "bg_color": True, "text": True,
                "font": True, "font_size": True, "font_style": True,
                "align": False, "clip": False, "source": True, "value": True, "image": False,
                "auto_color_change": True
            },
            "text": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": False, "text": True,
                "font": True, "font_size": True, "font_style": True,
                "align": True, "clip": True, "source": True, "value": True, "image": False
            },
            "clock": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": False, "text": False,
                "font": True, "font_size": True, "font_style": True,
                "align": True, "clip": True, "source": False, "value": False, "image": False,
                "time_format": True, "show_am_pm": True, "show_seconds": True, "show_leading_zero": True
            },
            "rectangle": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": False, "text": False,
                "font": False, "font_size": False, "font_style": False,
                "align": False, "clip": False, "source": False, "value": False, "image": False
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
                "font": False, "font_size": True, "font_style": False,
                "align": False, "clip": False, "source": True, "value": True, "image": False,
                "show_background": True, "show_label": True, "show_gradient": True,
                "rounded_corners": False, "gradient_fill": False
            },
            "bar_gauge": {
                "width": True, "height": True, "radius": False,
                "color": True, "bg_color": True, "text": True,
                "font": True, "font_size": True, "font_style": True,
                "align": False, "clip": False, "source": True, "value": True, "image": False,
                "show_background": False, "show_label": False, "show_gradient": False,
                "rounded_corners": True, "gradient_fill": True,
                "auto_color_change": True,
                "bar_text_mode": True, "bar_text_position": True
            },
            "analog_clock": {
                "width": False, "height": False, "radius": True,
                "color": True, "bg_color": True, "text": False,
                "font": True, "font_size": True, "font_style": False,
                "align": False, "clip": False, "source": False, "value": False, "image": False,
                "show_seconds_hand": True, "show_clock_border": True,
                "clock_face_style": True, "smooth_animation": True
            }
        }

        visibility = field_visibility.get(element_type, {})

        self.width_label.setVisible(visibility.get("width", True))
        self.width_spin.setVisible(visibility.get("width", True))

        self.height_label.setVisible(visibility.get("height", True))
        self.height_spin.setVisible(visibility.get("height", True))

        self.radius_label.setVisible(visibility.get("radius", False))
        self.radius_spin.setVisible(visibility.get("radius", False))

        self.color_label.setVisible(visibility.get("color", True))
        self.color_widget.setVisible(visibility.get("color", True))

        self.bg_color_label.setVisible(visibility.get("bg_color", False))
        self.bg_color_widget.setVisible(visibility.get("bg_color", False))

        self.text_label.setVisible(visibility.get("text", True))
        self.text_edit.setVisible(visibility.get("text", True))

        self.font_family_label.setVisible(visibility.get("font", True))
        self.font_family_combo.setVisible(visibility.get("font", True))

        self.font_size_label.setVisible(visibility.get("font_size", True))
        self.font_size_spin.setVisible(visibility.get("font_size", True))

        self.font_style_label.setVisible(visibility.get("font_style", True))
        self.font_style_widget.setVisible(visibility.get("font_style", True))

        self.align_label.setVisible(visibility.get("align", False))
        self.align_widget.setVisible(visibility.get("align", False))

        self.clip_label.setVisible(visibility.get("clip", False))
        self.clip_checkbox.setVisible(visibility.get("clip", False))

        self.source_label.setVisible(visibility.get("source", False))
        self.source_combo.setVisible(visibility.get("source", False))

        self.value_label.setVisible(visibility.get("value", False))
        self.value_spin.setVisible(visibility.get("value", False))

        self.image_label.setVisible(visibility.get("image", False))
        self.image_widget.setVisible(visibility.get("image", False))

        self.scale_proportionally_label.setVisible(visibility.get("image", False))
        self.scale_proportionally_check.setVisible(visibility.get("image", False))

        # Line chart options
        self.show_background_label.setVisible(visibility.get("show_background", False))
        self.show_background_check.setVisible(visibility.get("show_background", False))

        self.show_label_label.setVisible(visibility.get("show_label", False))
        self.show_label_check.setVisible(visibility.get("show_label", False))

        self.show_gradient_label.setVisible(visibility.get("show_gradient", False))
        self.show_gradient_check.setVisible(visibility.get("show_gradient", False))

        # Bar gauge options
        self.rounded_corners_label.setVisible(visibility.get("rounded_corners", False))
        self.rounded_corners_check.setVisible(visibility.get("rounded_corners", False))

        self.gradient_fill_label.setVisible(visibility.get("gradient_fill", False))
        self.gradient_fill_check.setVisible(visibility.get("gradient_fill", False))

        self.auto_color_change_label.setVisible(visibility.get("auto_color_change", False))
        self.auto_color_change_check.setVisible(visibility.get("auto_color_change", False))

        # GIF options
        self.gif_label.setVisible(visibility.get("gif", False))
        self.gif_widget.setVisible(visibility.get("gif", False))
        self.scale_mode_label.setVisible(visibility.get("scale_mode", False))
        self.scale_mode_combo.setVisible(visibility.get("scale_mode", False))

        # Bar gauge text options
        self.bar_text_mode_label.setVisible(visibility.get("bar_text_mode", False))
        self.bar_text_mode_combo.setVisible(visibility.get("bar_text_mode", False))
        self.bar_text_position_label.setVisible(visibility.get("bar_text_position", False))
        self.bar_text_position_combo.setVisible(visibility.get("bar_text_position", False))

        # Digital clock time format options
        self.time_format_label.setVisible(visibility.get("time_format", False))
        self.time_format_combo.setVisible(visibility.get("time_format", False))
        self.show_am_pm_label.setVisible(visibility.get("show_am_pm", False))
        self.show_am_pm_check.setVisible(visibility.get("show_am_pm", False))
        self.show_seconds_label.setVisible(visibility.get("show_seconds", False))
        self.show_seconds_check.setVisible(visibility.get("show_seconds", False))
        self.show_leading_zero_label.setVisible(visibility.get("show_leading_zero", False))
        self.show_leading_zero_check.setVisible(visibility.get("show_leading_zero", False))

        # Analog clock options
        self.show_seconds_hand_label.setVisible(visibility.get("show_seconds_hand", False))
        self.show_seconds_hand_check.setVisible(visibility.get("show_seconds_hand", False))
        self.show_clock_border_label.setVisible(visibility.get("show_clock_border", False))
        self.show_clock_border_check.setVisible(visibility.get("show_clock_border", False))
        self.clock_face_style_label.setVisible(visibility.get("clock_face_style", False))
        self.clock_face_style_combo.setVisible(visibility.get("clock_face_style", False))
        self.smooth_animation_label.setVisible(visibility.get("smooth_animation", False))
        self.smooth_animation_check.setVisible(visibility.get("smooth_animation", False))

    def set_element(self, element):
        self.current_element = None
        self.multi_selection_elements = []
        self.multi_selection_indices = []

        if element is None:
            self.no_selection_container.setVisible(True)
            self.scroll_area.setVisible(False)
            self.alignment_widget.setVisible(False)
            return

        self.no_selection_container.setVisible(False)
        self.scroll_area.setVisible(True)
        self.alignment_widget.setVisible(False)

        self.update_visible_fields(element.type)

        self.name_edit.blockSignals(True)
        self.x_spin.blockSignals(True)
        self.y_spin.blockSignals(True)
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.radius_spin.blockSignals(True)
        self.text_edit.blockSignals(True)
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
        self.rounded_corners_check.blockSignals(True)
        self.gradient_fill_check.blockSignals(True)
        self.auto_color_change_check.blockSignals(True)
        self.gif_path_edit.blockSignals(True)
        self.scale_mode_combo.blockSignals(True)
        self.color_opacity_slider.blockSignals(True)
        self.bg_color_opacity_slider.blockSignals(True)
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
        self.radius_spin.setValue(element.radius)
        self.text_edit.setText(element.text)
        self.font_size_spin.setValue(element.font_size)
        self.value_spin.setValue(element.value)
        self.image_path_edit.setText(element.image_path)
        self.clip_checkbox.setChecked(element.clip)
        self.scale_proportionally_check.setChecked(element.scale_proportionally)
        self.show_background_check.setChecked(element.show_background)
        self.show_label_check.setChecked(element.show_label)
        self.show_gradient_check.setChecked(element.show_gradient)
        self.rounded_corners_check.setChecked(element.rounded_corners)
        self.gradient_fill_check.setChecked(element.gradient_fill)
        self.auto_color_change_check.setChecked(getattr(element, 'auto_color_change', True))

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

        # Set opacity values
        color_opacity = getattr(element, 'color_opacity', 100)
        bg_color_opacity = getattr(element, 'background_color_opacity', 100)
        self.color_opacity_slider.setValue(color_opacity)
        self.color_opacity_label.setText(f"{color_opacity}%")
        self.bg_color_opacity_slider.setValue(bg_color_opacity)
        self.bg_color_opacity_label.setText(f"{bg_color_opacity}%")

        self.set_source_by_id(element.source)

        self.name_edit.blockSignals(False)
        self.x_spin.blockSignals(False)
        self.y_spin.blockSignals(False)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self.radius_spin.blockSignals(False)
        self.text_edit.blockSignals(False)
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
        self.rounded_corners_check.blockSignals(False)
        self.gradient_fill_check.blockSignals(False)
        self.auto_color_change_check.blockSignals(False)
        self.gif_path_edit.blockSignals(False)
        self.scale_mode_combo.blockSignals(False)
        self.color_opacity_slider.blockSignals(False)
        self.bg_color_opacity_slider.blockSignals(False)
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

    def on_property_changed(self):
        if self.current_element is None:
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
        self.current_element.radius = self.radius_spin.value()
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

        # Bar gauge options
        self.current_element.rounded_corners = self.rounded_corners_check.isChecked()
        self.current_element.gradient_fill = self.gradient_fill_check.isChecked()
        self.current_element.bar_text_mode = self.bar_text_mode_combo.currentData() or 'full'
        self.current_element.bar_text_position = self.bar_text_position_combo.currentData() or 'inside'

        # Gauge options
        self.current_element.auto_color_change = self.auto_color_change_check.isChecked()

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
        color = QColorDialog.getColor(QColor(self.current_element.color), self)
        if color.isValid():
            self.current_element.color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.property_changed.emit()

    def choose_bg_color(self):
        if self.current_element is None:
            return
        color = QColorDialog.getColor(QColor(self.current_element.background_color), self)
        if color.isValid():
            self.current_element.background_color = color.name()
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.property_changed.emit()

    def on_color_opacity_changed(self, value):
        if self.current_element is None:
            return
        if not self._undo_state_saved:
            self.property_will_change.emit()
            self._undo_state_saved = True
        self.current_element.color_opacity = value
        self.color_opacity_label.setText(f"{value}%")
        self.property_changed.emit()

    def on_bg_color_opacity_changed(self, value):
        if self.current_element is None:
            return
        if not self._undo_state_saved:
            self.property_will_change.emit()
            self._undo_state_saved = True
        self.current_element.background_color_opacity = value
        self.bg_color_opacity_label.setText(f"{value}%")
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
                    max_width = min(img_width, DISPLAY_WIDTH)
                    max_height = min(img_height, DISPLAY_HEIGHT)

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
                    max_width = min(img_width, DISPLAY_WIDTH)
                    max_height = min(img_height, DISPLAY_HEIGHT)

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

        self.no_selection_container.setVisible(False)
        self.scroll_area.setVisible(False)
        self.alignment_widget.setVisible(True)

        self.selection_count_label.setText(f"{len(elements)} elements selected")

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
        Returns list of dicts: {'elements': [elements], 'bounds': (x, y, w, h)}
        """
        units = []
        grouped = {}  # group_name -> [elements]

        for el in self.multi_selection_elements:
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
