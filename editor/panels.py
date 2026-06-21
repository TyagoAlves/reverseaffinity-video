import os
import time
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QRect, QPoint
from PyQt5.QtGui import (
    QColor, QPixmap, QPainter, QIcon, QFont, QFontDatabase,
    QBrush, QPen, QLinearGradient,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QColorDialog, QListWidget,
    QListWidgetItem, QSpinBox, QGridLayout, QComboBox,
    QScrollArea, QFrame, QToolButton, QAbstractItemView,
    QGroupBox, QLineEdit, QSizePolicy, QCheckBox,
    QProgressBar, QMenu, QInputDialog, QApplication, QToolTip,
)

from .layers import BLEND_MODES, AdjustmentLayer, GroupLayer, Layer
from .i18n import _, get_translator
from .brushengine import load_preset, save_preset, list_presets, PRESET_DIR


class ColorSwatch(QPushButton):
    colorPicked = pyqtSignal(QColor)

    def __init__(self, color=QColor(0, 0, 0), parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        self.clicked.connect(self._pick)

    def _update_style(self):
        r, g, b = self._color.red(), self._color.green(), self._color.blue()
        lum = (r * 299 + g * 587 + b * 114) / 1000
        border = "#333" if lum > 128 else "#999"
        self.setStyleSheet(
            f"background-color: {self._color.name()}; "
            f"border: 2px solid {border}; border-radius: 4px;"
        )

    def set_color(self, c):
        self._color = c
        self._update_style()

    def color(self):
        return self._color

    def _pick(self):
        d = QColorDialog(self._color, self)
        d.setWindowTitle(_("Select Color"))
        d.setOptions(QColorDialog.DontUseNativeDialog)
        d.setStyleSheet("""
            QColorDialog { background-color: #1a1a1a; color: #e0e0e0; }
            QColorDialog QLabel { color: #c0c0c0; }
            QColorDialog QSpinBox { background: #222; color: #d0d0d0; border: 1px solid #444; }
            QColorDialog QLineEdit { background: #222; color: #d0d0d0; border: 1px solid #444; }
            QColorDialog QPushButton { background: #333; color: #d0d0d0; border: 1px solid #555; padding: 4px 12px; border-radius: 3px; }
            QColorDialog QPushButton:hover { background: #444; }
            QColorDialog QComboBox { background: #222; color: #d0d0d0; border: 1px solid #444; }
            QColorDialog QComboBox QAbstractItemView { background: #222; color: #d0d0d0; selection-background-color: #3a8ac4; }
        """)
        if d.exec_() == QColorDialog.Accepted:
            c = d.selectedColor()
            self._color = c
            self._update_style()
            self.colorPicked.emit(c)


class ColorPanel(QWidget):
    colorChanged = pyqtSignal(QColor)
    bgColorChanged = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        swatch_row = QHBoxLayout()
        swatch_row.addWidget(QLabel(_("FG:")))
        self.fg = ColorSwatch(QColor(0, 0, 0))
        swatch_row.addWidget(self.fg)
        swatch_row.addWidget(QLabel(_("BG:")))
        self.bg = ColorSwatch(QColor(255, 255, 255))
        swatch_row.addWidget(self.bg)
        swap_btn = QPushButton("↔")
        swap_btn.setFixedSize(24, 24)
        swap_btn.clicked.connect(self._swap)
        swatch_row.addWidget(swap_btn)
        layout.addLayout(swatch_row)

        self.fg.colorPicked.connect(lambda c: self.colorChanged.emit(c))
        self.bg.colorPicked.connect(lambda c: self.bgColorChanged.emit(c))

        grid = QGridLayout()
        grid.setSpacing(2)

        self.r_spin = self._spin(0, 255)
        self.g_spin = self._spin(0, 255)
        self.b_spin = self._spin(0, 255)
        self.h_spin = self._spin(0, 360)
        self.s_spin = self._spin(0, 100)
        self.l_spin = self._spin(0, 100)
        self.hex_edit = QLineEdit("000000")
        self.hex_edit.setMaxLength(6)
        self.hex_edit.textChanged.connect(self._hex_changed)

        grid.addWidget(QLabel("R:"), 0, 0); grid.addWidget(self.r_spin, 0, 1)
        grid.addWidget(QLabel("G:"), 1, 0); grid.addWidget(self.g_spin, 1, 1)
        grid.addWidget(QLabel("B:"), 2, 0); grid.addWidget(self.b_spin, 2, 1)
        grid.addWidget(QLabel("H:"), 3, 0); grid.addWidget(self.h_spin, 3, 1)
        grid.addWidget(QLabel("S:"), 4, 0); grid.addWidget(self.s_spin, 4, 1)
        grid.addWidget(QLabel("L:"), 5, 0); grid.addWidget(self.l_spin, 5, 1)
        grid.addWidget(QLabel("#"), 6, 0); grid.addWidget(self.hex_edit, 6, 1)

        layout.addLayout(grid)

        for s in [self.r_spin, self.g_spin, self.b_spin]:
            s.valueChanged.connect(self._rgb_changed)
        for s in [self.h_spin, self.s_spin, self.l_spin]:
            s.valueChanged.connect(self._hsl_changed)

        self._updating = False

    def _spin(self, lo, hi):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setFixedHeight(20)
        return s

    def _swap(self):
        fg, bg = self.fg.color(), self.bg.color()
        self.fg.set_color(bg)
        self.bg.set_color(fg)
        self.colorChanged.emit(self.fg.color())
        self.bgColorChanged.emit(self.bg.color())

    def _rgb_changed(self):
        if self._updating:
            return
        c = QColor(self.r_spin.value(), self.g_spin.value(), self.b_spin.value())
        self._sync_fg(c)
        self.colorChanged.emit(c)

    def _hsl_changed(self):
        if self._updating:
            return
        c = QColor()
        c.setHsl(self.h_spin.value(), self.s_spin.value(), self.l_spin.value())
        self._sync_fg(c)
        self.colorChanged.emit(c)

    def _hex_changed(self, text):
        if self._updating:
            return
        if len(text) == 6:
            try:
                c = QColor(f"#{text}")
                if c.isValid():
                    self._sync_fg(c)
                    self.colorChanged.emit(c)
            except Exception:
                pass

    def _sync_fg(self, c):
        self._updating = True
        self.r_spin.setValue(c.red())
        self.g_spin.setValue(c.green())
        self.b_spin.setValue(c.blue())
        self.h_spin.setValue(max(0, c.hue()))
        self.s_spin.setValue(c.saturation())
        self.l_spin.setValue(c.lightness())
        self.hex_edit.setText(c.name().lstrip("#"))
        self._updating = False
        self.fg.set_color(c)

    def set_color(self, c):
        self._sync_fg(c)

    def set_bg_color(self, c):
        self.bg.set_color(c)


class SwatchesPanel(QWidget):
    colorSelected = pyqtSignal(QColor)
    bgColorSelected = pyqtSignal(QColor)

    def __init__(self, canvas_getter=None, parent=None):
        super().__init__(parent)
        self.canvas_getter = canvas_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(_("Click: FG  |  Right-click: BG")))
        layout.addLayout(mode_row)

        self._swatches = [
            ["#000000", "Black"], ["#434343", "Dark Gray 3"], ["#666666", "Dark Gray 2"],
            ["#999999", "Dark Gray 1"], ["#b7b7b7", "Gray"], ["#cccccc", "Light Gray 1"],
            ["#d9d9d9", "Light Gray 2"], ["#efefef", "Light Gray 3"], ["#f3f3f3", "Light Gray 4"],
            ["#ffffff", "White"],
            ["#d9d9d9", "Gray 10%"], ["#bfbfbf", "Gray 20%"], ["#a6a6a6", "Gray 30%"],
            ["#8c8c8c", "Gray 40%"], ["#737373", "Gray 50%"], ["#595959", "Gray 60%"],
            ["#404040", "Gray 70%"], ["#262626", "Gray 80%"], ["#0d0d0d", "Gray 90%"],
            ["#ff0000", "Red"], ["#ff6600", "Orange"], ["#ffff00", "Yellow"],
            ["#00ff00", "Green"], ["#00ffff", "Cyan"], ["#0066ff", "Blue"],
            ["#6600ff", "Purple"], ["#ff00ff", "Magenta"], ["#cc0066", "Pink"],
            ["#ffcccc", "Light Red"], ["#ffcc99", "Light Orange"], ["#ffffcc", "Light Yellow"],
            ["#ccffcc", "Light Green"], ["#ccffff", "Light Cyan"], ["#99ccff", "Light Blue"],
            ["#cc99ff", "Light Purple"], ["#ffccff", "Light Magenta"],
            ["#993300", "Brown"], ["#669900", "Olive"], ["#003366", "Dark Blue"],
            ["#330066", "Dark Purple"], ["#660033", "Dark Red"],
        ]

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        layout.addLayout(self.grid_layout)

        self._rebuild_grid()

        btn_row = QHBoxLayout()
        add_btn = QPushButton(_("Add to Swatches"))
        add_btn.clicked.connect(self._add_foreground)
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

        file_row = QHBoxLayout()
        save_btn = QPushButton(_("Save Swatches"))
        save_btn.clicked.connect(self._save_swatches)
        file_row.addWidget(save_btn)
        load_btn = QPushButton(_("Load Swatches"))
        load_btn.clicked.connect(self._load_swatches)
        file_row.addWidget(load_btn)
        layout.addLayout(file_row)

        layout.addStretch()

    def _rebuild_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, (hex_color, name) in enumerate(self._swatches):
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setToolTip(name)
            btn.setStyleSheet(
                f"background-color: {hex_color}; border: 1px solid #333; "
                f"border-radius: 2px;"
            )
            r, c = divmod(i, 9)
            btn.clicked.connect(lambda checked, h=hex_color: self._select_color(h, False))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, btn=btn, h=hex_color: self._show_swatch_menu(btn, pos, h)
            )
            self.grid_layout.addWidget(btn, r, c)

    def _show_swatch_menu(self, btn, pos, hex_color):
        menu = QMenu(self)
        menu.addAction(_("Set as Foreground"), lambda: self._select_color(hex_color, False))
        menu.addAction(_("Set as Background"), lambda: self._select_color(hex_color, True))
        menu.addSeparator()
        menu.addAction(_("Delete Swatch"), lambda: self._delete_swatch(hex_color))
        menu.exec_(btn.mapToGlobal(pos))

    def _delete_swatch(self, hex_color):
        for i, (h, n) in enumerate(self._swatches):
            if h == hex_color:
                del self._swatches[i]
                break
        self._rebuild_grid()

    def _add_foreground(self):
        if self.canvas_getter:
            canvas = self.canvas_getter()
            if canvas:
                c = canvas.tool_color
                hex_color = c.name()
                for h, n in self._swatches:
                    if h == hex_color:
                        return
                self._swatches.append([hex_color, hex_color])
                self._rebuild_grid()

    def _select_color(self, hex_color, is_bg=False):
        c = QColor(hex_color)
        if c.isValid():
            if is_bg:
                self.bgColorSelected.emit(c)
            else:
                self.colorSelected.emit(c)

    def _save_swatches(self):
        import json, os
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "reverseaffinity")
        os.makedirs(config_dir, exist_ok=True)
        path = os.path.join(config_dir, "swatches.json")
        with open(path, "w") as f:
            json.dump(self._swatches, f)

    def _load_swatches(self):
        import json, os
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "reverseaffinity")
        path = os.path.join(config_dir, "swatches.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._swatches = data
                    self._rebuild_grid()


class ChannelsPanel(QWidget):
    channelSelectionChanged = pyqtSignal(list)

    def __init__(self, canvas_getter, parent=None):
        super().__init__(parent)
        self.get_canvas = canvas_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        layout.addWidget(QLabel(_("Channels:")), 0, Qt.AlignLeft)

        self.channels = [
            {"name": "RGB", "color": None, "visible": True, "selected": True},
            {"name": "Red",   "color": "#ff0000", "visible": True, "selected": False},
            {"name": "Green", "color": "#00ff00", "visible": True, "selected": False},
            {"name": "Blue",  "color": "#0000ff", "visible": True, "selected": False},
        ]

        self._rows = []
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setSpacing(1)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.currentRowChanged.connect(self._selection_changed)
        layout.addWidget(self.list_widget, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        self.load_btn = QPushButton(_("Load as Selection"))
        self.load_btn.clicked.connect(self._load_selection)
        btn_row.addWidget(self.load_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    def refresh(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, ch in enumerate(self.channels):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, i)

            widget = QWidget()
            h = QHBoxLayout(widget)
            h.setContentsMargins(2, 1, 2, 1)
            h.setSpacing(4)

            vis_btn = QToolButton()
            vis_btn.setFixedSize(18, 18)
            vis_btn.setText("👁" if ch["visible"] else " ")
            vis_btn.setToolTip(_("Toggle channel visibility"))
            vis_btn.clicked.connect(lambda checked, c=ch: self._toggle_visibility(c))
            h.addWidget(vis_btn)

            color_box = QLabel()
            color_box.setFixedSize(14, 14)
            if ch["color"]:
                color_box.setStyleSheet(
                    f"background-color: {ch['color']}; border: 1px solid #555; border-radius: 2px;"
                )
            else:
                color_box.setStyleSheet(
                    "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                    "stop:0 #ff0000, stop:0.33 #00ff00, stop:0.66 #0000ff, stop:1 #ffffff);"
                    "border: 1px solid #555; border-radius: 2px;"
                )
            h.addWidget(color_box)

            name_label = QLabel(ch["name"])
            h.addWidget(name_label, 1)

            if ch["name"] != "RGB":
                icon_label = QLabel("👁" if ch["visible"] else " ")
                icon_label.setFixedSize(14, 14)
                h.addWidget(icon_label)

            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        self.list_widget.blockSignals(False)

    def _toggle_visibility(self, ch):
        if ch["name"] == "RGB":
            return
        ch["visible"] = not ch["visible"]
        self.refresh()
        canvas = self.get_canvas()
        if canvas:
            canvas._refresh()

    def _selection_changed(self, row):
        for i, ch in enumerate(self.channels):
            ch["selected"] = (i == row)
        self.channelSelectionChanged.emit([c["name"] for c in self.channels if c["selected"]])

    def _load_selection(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        ch = self.channels[row]
        canvas = self.get_canvas()
        if not canvas or not canvas.layer_stack.active:
            return
        from PyQt5.QtGui import QPainterPath
        path = QPainterPath()
        if canvas.selection_path and not canvas.selection_path.isEmpty():
            path = canvas.selection_path
        else:
            w = canvas.layer_stack.active.image.width()
            h = canvas.layer_stack.active.image.height()
            path.addRect(0, 0, w, h)
        canvas.selection_path = path
        canvas.selection_mask = None
        canvas._refresh()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        row = item.data(Qt.UserRole)
        if row < 0:
            return
        ch = self.channels[row]
        menu = QMenu(self)
        if ch["name"] not in ("RGB",):
            vis_action = menu.addAction(
                _("Hide Channel") if ch["visible"] else _("Show Channel")
            )
            del_action = menu.addAction(_("Delete Channel"))
        else:
            menu.addAction(_("Duplicate Channel"))

        action = menu.exec_(self.list_widget.viewport().mapToGlobal(pos))
        if ch["name"] not in ("RGB",):
            if action == vis_action:
                self._toggle_visibility(ch)
            elif action == del_action:
                self._delete_channel(row)

    def _delete_channel(self, row):
        if 0 <= row < len(self.channels):
            ch = self.channels[row]
            if ch["name"] != "RGB":
                del self.channels[row]
                self.refresh()
                canvas = self.get_canvas()
                if canvas:
                    canvas._refresh()

    def visible_channels(self):
        return [c["name"] for c in self.channels if c["visible"]]

    def active_channels(self):
        return [c["name"] for c in self.channels if c["selected"]]


class LayerPanel(QWidget):
    layerChanged = pyqtSignal(int)

    def __init__(self, canvas_getter, parent=None):
        super().__init__(parent)
        self.get_canvas = canvas_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Blend mode combo
        mode_row = QHBoxLayout()
        self.blend_combo = QComboBox()
        self.blend_combo.addItems(BLEND_MODES)
        self.blend_combo.setMinimumWidth(100)
        self.blend_combo.currentTextChanged.connect(self._blend_changed)
        mode_row.addWidget(self.blend_combo, 1)
        layout.addLayout(mode_row)

        # Opacity + Fill row
        props_row = QHBoxLayout()
        props_row.setSpacing(2)

        self.opacity_label = QLabel(_("Opacity:"))
        self.opacity_label.setFixedWidth(42)
        props_row.addWidget(self.opacity_label)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._opacity_changed)
        props_row.addWidget(self.opacity_slider, 1)

        self.opacity_value = QLabel("100%")
        self.opacity_value.setFixedWidth(32)
        self.opacity_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        props_row.addWidget(self.opacity_value)

        layout.addLayout(props_row)

        fill_row = QHBoxLayout()
        fill_row.setSpacing(2)

        self.fill_label = QLabel(_("Fill:"))
        self.fill_label.setFixedWidth(42)
        fill_row.addWidget(self.fill_label)

        self.fill_slider = QSlider(Qt.Horizontal)
        self.fill_slider.setRange(0, 100)
        self.fill_slider.setValue(100)
        self.fill_slider.valueChanged.connect(self._fill_changed)
        fill_row.addWidget(self.fill_slider, 1)

        self.fill_value = QLabel("100%")
        self.fill_value.setFixedWidth(32)
        self.fill_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fill_row.addWidget(self.fill_value)

        layout.addLayout(fill_row)

        # Lock buttons row
        lock_row = QHBoxLayout()
        lock_row.setSpacing(2)

        self.lock_tp_btn = self._lock_button("◻", _("Lock transparent pixels"))
        self.lock_tp_btn.clicked.connect(lambda: self._toggle_lock("transparent"))
        lock_row.addWidget(self.lock_tp_btn)

        self.lock_ip_btn = self._lock_button("✎", _("Lock image pixels"))
        self.lock_ip_btn.clicked.connect(lambda: self._toggle_lock("image"))
        lock_row.addWidget(self.lock_ip_btn)

        self.lock_pos_btn = self._lock_button("⇱", _("Lock position"))
        self.lock_pos_btn.clicked.connect(lambda: self._toggle_lock("position"))
        lock_row.addWidget(self.lock_pos_btn)

        self.lock_all_btn = self._lock_button("🔒", _("Lock all"))
        self.lock_all_btn.clicked.connect(lambda: self._toggle_lock("all"))
        lock_row.addWidget(self.lock_all_btn)

        lock_row.addStretch()
        layout.addLayout(lock_row)

        # Layer list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.currentRowChanged.connect(self._row_changed)
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.setSpacing(1)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, 1)

        # Action buttons row (Photoshop-style)
        action_row = QHBoxLayout()
        action_row.setSpacing(1)

        self.link_btn = self._action_button("🔗", _("Link layers"))
        action_row.addWidget(self.link_btn)

        self.fx_btn = self._action_button("fx", _("Layer styles"))
        self.fx_btn.setStyleSheet("font-weight: bold; font-style: italic;")
        action_row.addWidget(self.fx_btn)

        self.mask_btn = self._action_button("◐", _("Add layer mask"))
        self.mask_btn.clicked.connect(self._add_mask)
        action_row.addWidget(self.mask_btn)

        self.adj_btn = self._action_button("●", _("New fill/adjustment layer"))
        self._setup_adj_menu()
        action_row.addWidget(self.adj_btn)

        self.group_btn = self._action_button("📁", _("New group"))
        self.group_btn.clicked.connect(self._add_group)
        action_row.addWidget(self.group_btn)

        action_row.addStretch()

        self.add_btn = self._action_button("＋", _("New layer"))
        self.add_btn.clicked.connect(self._add_layer)
        action_row.addWidget(self.add_btn)

        self.del_btn = self._action_button("🗑", _("Delete layer"))
        self.del_btn.clicked.connect(self._del_layer)
        action_row.addWidget(self.del_btn)

        layout.addLayout(action_row)

        get_translator().language_changed.connect(self.retranslate)

    def _lock_button(self, text, tooltip):
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(24, 22)
        btn.setStyleSheet(
            "QToolButton { border: 1px solid #333; border-radius: 2px; padding: 1px; }"
            "QToolButton:checked { background-color: #444; border: 1px solid #f97316; }"
        )
        return btn

    def _action_button(self, text, tooltip):
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(24, 22)
        btn.setStyleSheet(
            "QToolButton { border: none; border-radius: 2px; padding: 1px; }"
            "QToolButton:hover { background-color: #333; }"
        )
        return btn

    def _setup_adj_menu(self):
        self.adj_menu = QMenu(self)
        self.adj_menu.addAction(_("Brightness/Contrast"), lambda: self._add_adj("brightness_contrast"))
        self.adj_menu.addAction(_("Hue/Saturation"), lambda: self._add_adj("hsl"))
        self.adj_menu.addAction(_("Levels"), lambda: self._add_adj("levels"))
        self.adj_menu.addSeparator()
        self.adj_menu.addAction(_("Solid Color..."), lambda: self._add_adj("solid_color"))
        self.adj_menu.addAction(_("Gradient..."), lambda: self._add_adj("gradient"))
        self.adj_btn.setMenu(self.adj_menu)
        self.adj_btn.setPopupMode(QToolButton.InstantPopup)

    def retranslate(self):
        self.blend_combo.blockSignals(True)
        self.blend_combo.clear()
        self.blend_combo.addItems([_(m) for m in BLEND_MODES])
        self.blend_combo.blockSignals(False)
        self.opacity_label.setText(_("Opacity:"))
        self.fill_label.setText(_("Fill:"))
        self.lock_tp_btn.setToolTip(_("Lock transparent pixels"))
        self.lock_ip_btn.setToolTip(_("Lock image pixels"))
        self.lock_pos_btn.setToolTip(_("Lock position"))
        self.lock_all_btn.setToolTip(_("Lock all"))
        self.link_btn.setToolTip(_("Link layers"))
        self.fx_btn.setToolTip(_("Layer styles"))
        self.mask_btn.setToolTip(_("Add layer mask"))
        self.adj_btn.setToolTip(_("New fill/adjustment layer"))
        self.group_btn.setToolTip(_("New group"))
        self.add_btn.setToolTip(_("New layer"))
        self.del_btn.setToolTip(_("Delete layer"))

    def _make_layer_item_widget(self, i, layer):
        widget = QWidget()
        h = QHBoxLayout(widget)
        h.setContentsMargins(2, 1, 2, 1)
        h.setSpacing(4)

        thumb = QLabel()
        thumb.setFixedSize(32, 32)
        thumb.setScaledContents(True)
        thumb.setStyleSheet("border: 1px solid #333; border-radius: 1px;")
        try:
            thumb_img = layer.image.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb.setPixmap(QPixmap.fromImage(thumb_img))
        except Exception:
            pass
        h.addWidget(thumb)

        vis_btn = QToolButton()
        vis_btn.setFixedSize(18, 18)
        vis_btn.setText("👁" if layer.visible else " ")
        vis_btn.setToolTip(_("Toggle visibility"))
        vis_btn.clicked.connect(lambda checked, idx=i: self._toggle_visibility(idx))
        h.addWidget(vis_btn)

        name_label = QLabel(layer.name)
        name_label.setFixedHeight(22)
        if isinstance(layer, AdjustmentLayer):
            name_label.setText(f"⚡ {layer.name}")
        elif isinstance(layer, GroupLayer):
            name_label.setText(f"📁 {layer.name}")
        name_label.setStyleSheet("padding: 0px 2px;")
        h.addWidget(name_label, 1)

        return widget

    def refresh(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, layer in enumerate(canvas.layer_stack.layers):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, i)
            widget = self._make_layer_item_widget(i, layer)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        if 0 <= canvas.layer_stack.active_index < self.list_widget.count():
            self.list_widget.setCurrentRow(canvas.layer_stack.active_index)
        self.list_widget.blockSignals(False)

        active = canvas.layer_stack.active
        if active:
            self.blend_combo.blockSignals(True)
            idx = self.blend_combo.findText(active.blend_mode)
            if idx >= 0:
                self.blend_combo.setCurrentIndex(idx)
            self.blend_combo.blockSignals(False)
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(active.opacity * 100))
            self.opacity_value.setText(f"{int(active.opacity * 100)}%")
            self.opacity_slider.blockSignals(False)
            self.fill_slider.blockSignals(True)
            self.fill_slider.setValue(int(active.fill * 100))
            self.fill_value.setText(f"{int(active.fill * 100)}%")
            self.fill_slider.blockSignals(False)

            self.lock_tp_btn.blockSignals(True)
            self.lock_tp_btn.setChecked(active.locked)
            self.lock_ip_btn.blockSignals(True)
            self.lock_ip_btn.setChecked(active.locked)
            self.lock_pos_btn.blockSignals(True)
            self.lock_pos_btn.setChecked(active.locked)
            self.lock_all_btn.blockSignals(True)
            self.lock_all_btn.setChecked(active.locked)
            self.lock_tp_btn.blockSignals(False)
            self.lock_ip_btn.blockSignals(False)
            self.lock_pos_btn.blockSignals(False)
            self.lock_all_btn.blockSignals(False)

    def _toggle_visibility(self, idx):
        canvas = self.get_canvas()
        if canvas and 0 <= idx < len(canvas.layer_stack.layers):
            layer = canvas.layer_stack.layers[idx]
            layer.visible = not layer.visible
            canvas._refresh()
            self.refresh()

    def _toggle_lock(self, lock_type):
        canvas = self.get_canvas()
        if not canvas or not canvas.layer_stack.active:
            return
        active = canvas.layer_stack.active
        if lock_type == "all":
            active.locked = not active.locked
        else:
            active.locked = not active.locked
        self.refresh()

    def _row_changed(self, row):
        canvas = self.get_canvas()
        if canvas and row >= 0:
            canvas.layer_stack.active_index = row
            canvas._refresh()
            self.refresh()

    def _blend_changed(self, mode):
        canvas = self.get_canvas()
        if canvas and canvas.layer_stack.active:
            canvas.layer_stack.active.blend_mode = mode
            canvas._refresh()

    def _opacity_changed(self, val):
        canvas = self.get_canvas()
        if canvas and canvas.layer_stack.active:
            canvas.layer_stack.active.opacity = val / 100.0
            self.opacity_value.setText(f"{val}%")
            canvas._refresh()

    def _fill_changed(self, val):
        canvas = self.get_canvas()
        if canvas and canvas.layer_stack.active:
            canvas.layer_stack.active.fill = val / 100.0
            self.fill_value.setText(f"{val}%")
            canvas._refresh()

    def _add_layer(self):
        canvas = self.get_canvas()
        if canvas:
            canvas._save_state("New layer")
            canvas.layer_stack.add_layer()
            canvas._refresh()
            self.refresh()

    def _del_layer(self):
        canvas = self.get_canvas()
        if canvas:
            idx = self.list_widget.currentRow()
            if idx >= 0:
                canvas._save_state("Delete layer")
                canvas.layer_stack.remove_layer(idx)
                canvas._refresh()
                self.refresh()

    def _add_adj(self, adj_type):
        canvas = self.get_canvas()
        if canvas:
            canvas._save_state("Add adjustment")
            canvas._add_adjustment(adj_type)
            canvas._refresh()
            self.refresh()

    def _add_group(self):
        canvas = self.get_canvas()
        if canvas:
            canvas._save_state("New group")
            canvas.layer_stack.add_group()
            canvas._refresh()
            self.refresh()

    def _add_mask(self):
        canvas = self.get_canvas()
        if canvas and canvas.layer_stack.active:
            layer = canvas.layer_stack.active
            if layer.mask is None:
                layer.reveal_all_mask()
            else:
                layer.delete_mask()
            canvas._refresh()
            self.refresh()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        idx = item.data(Qt.UserRole)
        canvas = self.get_canvas()
        if not canvas:
            return

        menu = QMenu(self)

        rename_action = menu.addAction(_("Rename Layer..."))
        menu.addSeparator()
        dup_action = menu.addAction(_("Duplicate Layer"))
        del_action = menu.addAction(_("Delete Layer"))
        menu.addSeparator()
        merge_down_action = menu.addAction(_("Merge Down"))
        merge_visible_action = menu.addAction(_("Merge Visible"))
        flatten_action = menu.addAction(_("Flatten Image"))

        action = menu.exec_(self.list_widget.viewport().mapToGlobal(pos))

        if action == rename_action:
            current_name = canvas.layer_stack.layers[idx].name
            new_name, ok = QInputDialog.getText(self, _("Rename Layer"), _("Name:"), text=current_name)
            if ok and new_name:
                canvas.layer_stack.layers[idx].name = new_name
                self.refresh()
        elif action == dup_action:
            canvas._save_state("Duplicate layer")
            canvas.layer_stack.duplicate_layer(idx)
            canvas._refresh()
            self.refresh()
        elif action == del_action:
            if len(canvas.layer_stack.layers) > 1:
                canvas._save_state("Delete layer")
                canvas.layer_stack.remove_layer(idx)
                canvas._refresh()
                self.refresh()
        elif action == merge_down_action:
            if idx > 0:
                canvas._save_state("Merge down")
                below = idx - 1
                top_img = canvas.layer_stack.layers[idx].image
                bot_img = canvas.layer_stack.layers[below].image
                p = QPainter(bot_img)
                p.drawImage(0, 0, top_img)
                p.end()
                canvas.layer_stack.remove_layer(idx)
                canvas._refresh()
                self.refresh()
        elif action == merge_visible_action:
            canvas._save_state("Merge visible")
            canvas.layer_stack.merge_visible()
            canvas._refresh()
            self.refresh()
        elif action == flatten_action:
            canvas._save_state("Flatten")
            canvas.layer_stack.flatten()
            canvas._refresh()
            self.refresh()


class GradientPanel(QWidget):
    gradientChanged = pyqtSignal()

    def __init__(self, canvas_getter, parent=None):
        super().__init__(parent)
        self.get_canvas = canvas_getter
        from .gradient_editor import GradientEditorWidget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.editor = GradientEditorWidget()
        self.editor.gradientChanged.connect(self._on_gradient_changed)
        layout.addWidget(self.editor)

    def _on_gradient_changed(self):
        canvas = self.get_canvas()
        if canvas:
            canvas.gradient_obj = self.editor.get_gradient()
        self.gradientChanged.emit()

    def refresh(self):
        canvas = self.get_canvas()
        if canvas and hasattr(canvas, 'gradient_obj'):
            self.editor.set_gradient(canvas.gradient_obj)


class HistoryPanel(QWidget):
    def __init__(self, canvas_getter, parent=None):
        super().__init__(parent)
        self.get_canvas = canvas_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.count_label = QLabel(_("History: ") + "0" + _(" entries"))
        layout.addWidget(self.count_label)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.currentRowChanged.connect(self._row_changed)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget)

    def refresh(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        history = canvas.history
        self.list_widget.blockSignals(True)
        cur_row = self.list_widget.currentRow()
        self.list_widget.clear()
        for i, entry in enumerate(history.stack):
            item = QListWidgetItem(entry.description)
            item.setData(Qt.UserRole, i)
            thumb = entry.get_thumbnail()
            if thumb:
                item.setIcon(QIcon(thumb))
            self.list_widget.addItem(item)
        if 0 <= history.index < self.list_widget.count():
            self.list_widget.setCurrentRow(history.index)
        self.list_widget.blockSignals(False)
        self.count_label.setText(_("History: ") + str(len(history.stack)) + _(" entries"))

    def _row_changed(self, row):
        if row < 0:
            return
        canvas = self.get_canvas()
        if not canvas:
            return
        history = canvas.history
        if row != history.index:
            history.jump_to(canvas.layer_stack, row)
            canvas._refresh()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        idx = item.data(Qt.UserRole)
        canvas = self.get_canvas()
        if not canvas or not canvas.history:
            return
        menu = QMenu(self)
        del_action = menu.addAction(_("Delete Entry"))
        clear_action = menu.addAction(_("Clear History"))
        action = menu.exec_(self.list_widget.viewport().mapToGlobal(pos))
        if action == del_action:
            canvas.history.delete_entry(idx)
            self.refresh()
        elif action == clear_action:
            canvas.history.clear()
            self.refresh()

    def set_canvas(self, canvas_getter):
        self.get_canvas = canvas_getter


class ToolOptionsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        layout.addWidget(QLabel(_("Size:")))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 5000)
        self.size_spin.setValue(3)
        self.size_spin.setFixedWidth(60)
        layout.addWidget(self.size_spin)

        layout.addWidget(QLabel(_("Opacity:")))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(80)
        layout.addWidget(self.opacity_slider)

        layout.addWidget(QLabel(_("Flow:")))
        self.flow_slider = QSlider(Qt.Horizontal)
        self.flow_slider.setRange(1, 100)
        self.flow_slider.setValue(100)
        self.flow_slider.setFixedWidth(80)
        layout.addWidget(self.flow_slider)

        layout.addWidget(QLabel(_("Font:")))
        self.font_combo = QComboBox()
        self.font_combo.addItems(QFontDatabase().families())
        self.font_combo.setCurrentText("Arial")
        self.font_combo.setFixedWidth(120)
        layout.addWidget(self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(1, 999)
        self.font_size_spin.setValue(32)
        self.font_size_spin.setFixedWidth(50)
        layout.addWidget(self.font_size_spin)

        self.bold_btn = QToolButton()
        self.bold_btn.setText(_("B"))
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(24, 24)
        layout.addWidget(self.bold_btn)

        self.italic_btn = QToolButton()
        self.italic_btn.setText(_("I"))
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(24, 24)
        layout.addWidget(self.italic_btn)

        self.underline_btn = QToolButton()
        self.underline_btn.setText(_("U"))
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(24, 24)
        layout.addWidget(self.underline_btn)

        layout.addStretch()


class BrushPanel(QWidget):
    brushSettingsChanged = pyqtSignal()

    def __init__(self, canvas_getter=None, parent=None):
        super().__init__(parent)
        self.canvas_getter = canvas_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        tip_row = QHBoxLayout()
        tip_row.addWidget(QLabel("Tip:"))
        self.tip_combo = QComboBox()
        self.tip_combo.addItems(["Circle", "Square", "Texture"])
        self.tip_combo.currentTextChanged.connect(self._on_change)
        tip_row.addWidget(self.tip_combo)
        layout.addLayout(tip_row)

        hard_row = QHBoxLayout()
        hard_row.addWidget(QLabel("Hardness:"))
        self.hardness_slider = QSlider(Qt.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(100)
        self.hardness_slider.valueChanged.connect(self._on_change)
        hard_row.addWidget(self.hardness_slider)
        self.hardness_label = QLabel("100%")
        self.hardness_label.setFixedWidth(32)
        hard_row.addWidget(self.hardness_label)
        layout.addLayout(hard_row)
        self.hardness_slider.valueChanged.connect(
            lambda v: self.hardness_label.setText(f"{v}%")
        )

        space_row = QHBoxLayout()
        space_row.addWidget(QLabel("Spacing:"))
        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setRange(1, 100)
        self.spacing_slider.setValue(25)
        self.spacing_slider.valueChanged.connect(self._on_change)
        space_row.addWidget(self.spacing_slider)
        self.spacing_label = QLabel("25%")
        self.spacing_label.setFixedWidth(32)
        space_row.addWidget(self.spacing_label)
        layout.addLayout(space_row)
        self.spacing_slider.valueChanged.connect(
            lambda v: self.spacing_label.setText(f"{v}%")
        )

        flow_row = QHBoxLayout()
        flow_row.addWidget(QLabel("Flow:"))
        self.flow_slider = QSlider(Qt.Horizontal)
        self.flow_slider.setRange(1, 100)
        self.flow_slider.setValue(100)
        self.flow_slider.valueChanged.connect(self._on_change)
        flow_row.addWidget(self.flow_slider)
        self.flow_label = QLabel("100%")
        self.flow_label.setFixedWidth(32)
        flow_row.addWidget(self.flow_label)
        layout.addLayout(flow_row)
        self.flow_slider.valueChanged.connect(
            lambda v: self.flow_label.setText(f"{v}%")
        )

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(80, 80)
        self.preview_label.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        layout.addWidget(self.preview_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #333;")
        layout.addWidget(sep)

        preset_header = QLabel("Presets:")
        preset_header.setStyleSheet("font-weight: bold; color: #aaa;")
        layout.addWidget(preset_header)

        self.preset_list = QListWidget()
        self.preset_list.setFixedHeight(80)
        self.preset_list.currentRowChanged.connect(self._preset_selected)
        layout.addWidget(self.preset_list)

        preset_btn_row = QHBoxLayout()
        self.save_preset_btn = QPushButton("Save")
        self.save_preset_btn.clicked.connect(self._save_preset)
        preset_btn_row.addWidget(self.save_preset_btn)
        self.delete_preset_btn = QPushButton("Delete")
        self.delete_preset_btn.clicked.connect(self._delete_preset)
        preset_btn_row.addWidget(self.delete_preset_btn)
        layout.addLayout(preset_btn_row)

        self._brush_engine = None
        self._refresh_preset_list()

    def set_brush_engine(self, engine):
        self._brush_engine = engine
        self._sync_from_engine()

    def _sync_from_engine(self):
        if not self._brush_engine:
            return

    def _on_change(self):
        if self._brush_engine:
            tip_name = self.tip_combo.currentText()
            hardness = self.hardness_slider.value() / 100.0
            if tip_name == "Circle":
                self._brush_engine.set_circle_tip(hardness)
            elif tip_name == "Square":
                self._brush_engine.set_square_tip(hardness)
            self._brush_engine.spacing = self.spacing_slider.value() / 100.0
            self._brush_engine.flow = self.flow_slider.value() / 100.0
            self._update_preview()
        self.brushSettingsChanged.emit()

    def _update_preview(self):
        if not self._brush_engine:
            return
        pix = self._brush_engine.make_preview(60)
        self.preview_label.setPixmap(pix)

    def _current_settings(self):
        return {
            "tip": self.tip_combo.currentText(),
            "hardness": self.hardness_slider.value() / 100.0,
            "spacing": self.spacing_slider.value() / 100.0,
            "flow": self.flow_slider.value() / 100.0,
        }

    def _apply_settings(self, data):
        self.tip_combo.blockSignals(True)
        self.hardness_slider.blockSignals(True)
        self.spacing_slider.blockSignals(True)
        self.flow_slider.blockSignals(True)
        idx = self.tip_combo.findText(data.get("tip", "Circle"))
        if idx >= 0:
            self.tip_combo.setCurrentIndex(idx)
        self.hardness_slider.setValue(int(data.get("hardness", 1.0) * 100))
        self.spacing_slider.setValue(int(data.get("spacing", 0.25) * 100))
        self.flow_slider.setValue(int(data.get("flow", 1.0) * 100))
        self.tip_combo.blockSignals(False)
        self.hardness_slider.blockSignals(False)
        self.spacing_slider.blockSignals(False)
        self.flow_slider.blockSignals(False)
        self._on_change()

    def _refresh_preset_list(self):
        self.preset_list.blockSignals(True)
        self.preset_list.clear()
        for name in list_presets():
            self.preset_list.addItem(name)
        self.preset_list.blockSignals(False)

    def _preset_selected(self, row):
        if row < 0:
            return
        name = self.preset_list.item(row).text()
        data = load_preset(name)
        if data:
            self._apply_settings(data)

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name:
            data = self._current_settings()
            data["name"] = name
            save_preset(name, data)
            self._refresh_preset_list()
            for i in range(self.preset_list.count()):
                if self.preset_list.item(i).text() == name:
                    self.preset_list.setCurrentRow(i)
                    break

    def _delete_preset(self):
        row = self.preset_list.currentRow()
        if row < 0:
            return
        name = self.preset_list.item(row).text()
        preset_path = os.path.join(PRESET_DIR, name + ".json")
        if os.path.exists(preset_path):
            os.remove(preset_path)
        self._refresh_preset_list()


class PathPanel(QWidget):
    def __init__(self, canvas_getter, parent=None):
        super().__init__(parent)
        self.get_canvas = canvas_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        layout.addWidget(QLabel("Paths:"))
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._row_changed)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self._delete_path)
        btn_row.addWidget(self.del_btn)

        self.fill_cb = QCheckBox("Fill")
        self.fill_cb.setChecked(True)
        self.fill_cb.stateChanged.connect(self._toggle_fill)
        btn_row.addWidget(self.fill_cb)

        self.stroke_cb = QCheckBox("Stroke")
        self.stroke_cb.stateChanged.connect(self._toggle_stroke)
        btn_row.addWidget(self.stroke_cb)

        self.vis_btn = QPushButton("Hide")
        self.vis_btn.clicked.connect(self._toggle_visible)
        btn_row.addWidget(self.vis_btn)

        layout.addLayout(btn_row)

        action_row = QHBoxLayout()
        self.to_sel_btn = QPushButton("To Selection")
        self.to_sel_btn.clicked.connect(self._to_selection)
        action_row.addWidget(self.to_sel_btn)

        self.stroke_btn = QPushButton("Stroke Path")
        self.stroke_btn.clicked.connect(self._stroke_path)
        action_row.addWidget(self.stroke_btn)

        layout.addLayout(action_row)

    def refresh(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        paths = canvas.get_active_paths()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, path in enumerate(paths):
            vis = "V" if path.visible else "H"
            fill = "F" if path.fill else "NF"
            stroke = "S" if path.stroke else "NS"
            item = QListWidgetItem(f"Path {i+1} [{vis}|{fill}|{stroke}]")
            item.setData(Qt.UserRole, i)
            self.list_widget.addItem(item)
        lid = id(canvas.layer_stack.active) if canvas.layer_stack.active else -1
        idx = canvas.active_path_index.get(lid, 0)
        if 0 <= idx < self.list_widget.count():
            self.list_widget.setCurrentRow(idx)
        self.list_widget.blockSignals(False)
        self._update_controls()

    def _update_controls(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        path = canvas.get_active_path()
        if path:
            self.fill_cb.blockSignals(True)
            self.fill_cb.setChecked(path.fill)
            self.fill_cb.blockSignals(False)
            self.stroke_cb.blockSignals(True)
            self.stroke_cb.setChecked(path.stroke)
            self.stroke_cb.blockSignals(False)
            self.vis_btn.setText("Hide" if path.visible else "Show")

    def _row_changed(self, row):
        canvas = self.get_canvas()
        if canvas and row >= 0:
            lid = id(canvas.layer_stack.active)
            canvas.active_path_index[lid] = row
            canvas.update()
            self._update_controls()

    def _delete_path(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        paths = canvas.get_active_paths()
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(paths):
            del paths[idx]
            canvas.update()
            self.refresh()

    def _toggle_fill(self, state):
        canvas = self.get_canvas()
        if not canvas:
            return
        path = canvas.get_active_path()
        if path:
            path.fill = bool(state)
            canvas.update()
            self.refresh()

    def _toggle_stroke(self, state):
        canvas = self.get_canvas()
        if not canvas:
            return
        path = canvas.get_active_path()
        if path:
            path.stroke = bool(state)
            canvas.update()
            self.refresh()

    def _toggle_visible(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        path = canvas.get_active_path()
        if path:
            path.visible = not path.visible
            canvas.update()
            self.refresh()

    def _to_selection(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        path = canvas.get_active_path()
        if path:
            qp = path.to_qpainterpath()
            canvas.selection_path = qp
            canvas.selection_mask = canvas._selection_mask_from_path(qp)
            canvas.selection_phase = 0
            canvas.viewport().update()

    def _stroke_path(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        layer = canvas.layer_stack.active
        if not layer or layer.locked:
            return
        path = canvas.get_active_path()
        if not path:
            return
        qp = path.to_qpainterpath()
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(canvas.tool_color)
        c.setAlpha(int(255 * canvas.tool_opacity))
        pen = QPen(c, canvas.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.strokePath(qp, pen)
        p.end()
        canvas._refresh()


class NavigatorPanel(QWidget):
    def __init__(self, canvas_getter, parent=None):
        super().__init__(parent)
        self.get_canvas = canvas_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(120, 90)
        self.preview_label.setStyleSheet("""
            QLabel {
                background: #0a0a0a;
                border: 1px solid #222;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.preview_label)

        zoom_row = QHBoxLayout()
        zoom_out_btn = QPushButton("\u2212")
        zoom_out_btn.setFixedSize(24, 24)
        zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_row.addWidget(zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        zoom_row.addWidget(self.zoom_label)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(24, 24)
        zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_row.addWidget(zoom_in_btn)

        fit_btn = QPushButton(_("Fit"))
        fit_btn.setFixedSize(36, 24)
        fit_btn.clicked.connect(self._zoom_fit)
        zoom_row.addWidget(fit_btn)

        layout.addLayout(zoom_row)

    def refresh(self):
        canvas = self.get_canvas()
        if not canvas:
            return
        composite = canvas.layer_stack.composite()
        if composite and not composite.isNull():
            preview = composite.scaled(160, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(QPixmap.fromImage(preview))
        self.zoom_label.setText(f"{canvas.zoom_level * 100:.0f}%")

    def set_zoom(self, zoom):
        self.zoom_label.setText(f"{zoom * 100:.0f}%")

    def _zoom_in(self):
        canvas = self.get_canvas()
        if canvas:
            canvas.zoom_in()

    def _zoom_out(self):
        canvas = self.get_canvas()
        if canvas:
            canvas.zoom_out()

    def _zoom_fit(self):
        canvas = self.get_canvas()
        if canvas:
            canvas.zoom_fit()
