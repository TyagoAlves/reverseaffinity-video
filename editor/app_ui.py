import os
from PyQt5.QtCore import Qt, QSize, QSettings, QRectF
from PyQt5.QtGui import QColor, QKeySequence, QFont, QIcon, QFontDatabase, QPixmap, QPainter, QBrush, QPen, QPainterPath
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QColorDialog,
    QToolBar, QToolButton, QSpinBox, QLabel, QComboBox,
    QSlider, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QInputDialog, QMenu, QStatusBar, QDockWidget, QTabWidget,
    QButtonGroup, QFrame, QScrollArea,
    QSplitter, QDialog, QGridLayout, QCheckBox, QGroupBox,
    QApplication, QMessageBox, QDialogButtonBox, QFormLayout, QLineEdit, QStackedWidget,
)

from .canvas import CanvasView
from .panels import ColorPanel, SwatchesPanel, ChannelsPanel, LayerPanel, HistoryPanel, ToolOptionsPanel, NavigatorPanel, GradientPanel, BrushPanel, PathPanel
from .tools import TOOL_LIST, ShapeTool
from .file_dialog import get_open_file_name, get_save_file_name
from .settings import SettingsManager
from .preferences_dialog import PreferencesDialog
from .resources import apply_dark_theme
from .tool_icons import get_tool_icon
from .i18n import _, get_translator
from .video_mode import VideoMode
from .resources import get_app_icon


class ToolPalette(QWidget):
    """Vertical tool palette on the left side (like Photoshop)."""

    def __init__(self, canvas_getter, parent=None):
        super().__init__(parent)
        self.get_canvas = canvas_getter
        self.setFixedWidth(42)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)

        self.tool_buttons = {}

        for group_name, tools in TOOL_LIST:
            for i, tool_cls in enumerate(tools):
                btn = QToolButton()
                btn.setCheckable(True)
                btn.setToolTip(f"{tool_cls.name} ({tool_cls.shortcut})")
                icon = get_tool_icon(tool_cls.name)
                if not icon.isNull():
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(20, 20))
                else:
                    btn.setText(tool_cls.shortcut)
                btn.setFixedSize(36, 26)
                btn.setStyleSheet("""
                    QToolButton {
                        border: 1px solid #2a2a2a; border-radius: 3px;
                        background: #1a1a1a;
                    }
                    QToolButton:checked {
                        background: #3a8ac4; border-color: #5a9ad4;
                    }
                    QToolButton:hover:!checked {
                        background: #2a2a2a; border-color: #555;
                    }
                """)
                btn.clicked.connect(lambda checked, t=tool_cls: self._select_tool(t))
                self.button_group.addButton(btn)
                layout.addWidget(btn)
                self.tool_buttons[tool_cls.name] = btn

            if group_name != TOOL_LIST[-1][0]:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet("color: #333; max-height: 1px; margin: 2px 6px;")
                layout.addWidget(sep)

        layout.addStretch()

        # Foreground/Background swatches (Photoshop-style stacked)
        color_frame = QFrame()
        color_frame.setFixedSize(42, 66)
        color_layout = QVBoxLayout(color_frame)
        color_layout.setContentsMargins(4, 4, 4, 4)
        color_layout.setSpacing(1)
        color_layout.setAlignment(Qt.AlignCenter)

        self.fg_btn = QPushButton()
        self.fg_btn.setFixedSize(28, 28)
        self.fg_btn.setToolTip(_("Foreground Color"))
        self.fg_btn.setCursor(Qt.PointingHandCursor)
        self.bg_btn = QPushButton()
        self.bg_btn.setFixedSize(28, 28)
        self.bg_btn.setToolTip(_("Background Color"))
        self.bg_btn.setCursor(Qt.PointingHandCursor)

        self.fg_btn.clicked.connect(lambda: self._pick_color(True))
        self.bg_btn.clicked.connect(lambda: self._pick_color(False))

        self.fg_color = QColor(0, 0, 0)
        self.bg_color = QColor(255, 255, 255)
        self._update_swatches()

        # Stack FG on top, BG slightly offset (Photoshop style)
        fg_container = QWidget()
        fg_l = QHBoxLayout(fg_container)
        fg_l.setContentsMargins(0, 0, 0, 0)
        fg_l.setAlignment(Qt.AlignCenter)
        fg_l.addWidget(self.fg_btn)

        bg_container = QWidget()
        bg_l = QHBoxLayout(bg_container)
        bg_l.setContentsMargins(0, 0, 0, 0)
        bg_l.setAlignment(Qt.AlignCenter)
        bg_l.addWidget(self.bg_btn)

        color_layout.addWidget(fg_container)
        color_layout.addWidget(bg_container)

        # Swap button (double-arrow)
        self.swap_btn = QPushButton("↕")
        self.swap_btn.setFixedSize(16, 14)
        self.swap_btn.setToolTip(_("Swap colors"))
        self.swap_btn.setCursor(Qt.PointingHandCursor)
        self.swap_btn.setStyleSheet(
            "QPushButton { background: #333; border: 1px solid #555; border-radius: 2px; "
            "font-size: 9px; padding: 0px; }"
            "QPushButton:hover { background: #555; }"
        )
        self.swap_btn.clicked.connect(self._swap_colors)

        swap_container = QWidget()
        swap_l = QHBoxLayout(swap_container)
        swap_l.setContentsMargins(0, 0, 0, 0)
        swap_l.setAlignment(Qt.AlignCenter)
        swap_l.addWidget(self.swap_btn)

        color_layout.addWidget(swap_container)

        layout.addWidget(color_frame, 0, Qt.AlignCenter)

        if self.button_group.buttons():
            self.button_group.buttons()[0].setChecked(True)

    def _update_swatches(self):
        fg_border = "#888"  # always visible border
        bg_border = "#888"
        self.fg_btn.setStyleSheet(
            f"background-color: {self.fg_color.name()}; "
            f"border: 2px solid {fg_border}; border-radius: 3px;"
        )
        self.bg_btn.setStyleSheet(
            f"background-color: {self.bg_color.name()}; "
            f"border: 2px solid {bg_border}; border-radius: 3px;"
        )

    def _pick_color(self, fg):
        d = QColorDialog(self.fg_color if fg else self.bg_color, self)
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
            if fg:
                self.fg_color = c
            else:
                self.bg_color = c
            self._update_swatches()
            canvas = self.get_canvas()
            if canvas:
                if fg:
                    canvas.set_foreground_color(c)
                else:
                    canvas.set_background_color(c)

    def _swap_colors(self):
        self.fg_color, self.bg_color = self.bg_color, self.fg_color
        self._update_swatches()
        canvas = self.get_canvas()
        if canvas:
            canvas.tool_color = self.fg_color
            canvas.bg_color = self.bg_color
            canvas.color_picked.emit(self.fg_color)

    def set_colors(self, fg, bg):
        self.fg_color = fg
        self.bg_color = bg
        self._update_swatches()

    def select_tool_by_name(self, tool_name):
        btn = self.tool_buttons.get(tool_name)
        if btn:
            btn.setChecked(True)

    def _select_tool(self, tool_cls):
        canvas = self.get_canvas()
        if canvas:
            canvas.set_tool(tool_cls.name)


class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("New Guide"))
        self.resize(280, 120)
        self.setStyleSheet("QDialog { background: #121212; }")

        layout = QVBoxLayout(self)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems([_("Horizontal"), _("Vertical")])
        layout.addWidget(QLabel(_("Orientation:")))
        layout.addWidget(self.orientation_combo)

        self.position_spin = QSpinBox()
        self.position_spin.setRange(0, 50000)
        self.position_spin.setValue(100)
        layout.addWidget(QLabel(_("Position (px):")))
        layout.addWidget(self.position_spin)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(_("OK"))
        cancel_btn = QPushButton(_("Cancel"))
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.result_data = None
        ok_btn.clicked.connect(self._accept)
        cancel_btn.clicked.connect(self.reject)

    def _accept(self):
        from PyQt5.QtCore import Qt
        orient = Qt.Horizontal if self.orientation_combo.currentIndex() == 0 else Qt.Vertical
        self.result_data = (orient, self.position_spin.value())
        self.accept()


class FilterGalleryDialog(QDialog):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle(_("Filter Gallery"))
        self.resize(800, 500)
        self.setStyleSheet("QDialog { background: #121212; }")

        layout = QHBoxLayout(self)

        left_panel = QWidget()
        left_panel.setStyleSheet("background: #121212;")
        left_layout = QVBoxLayout(left_panel)

        categories = {
            _("Adjustments"): [
                (_("Brightness / Contrast"), self._bc),
                (_("Hue / Saturation"), self._hs),
                (_("Levels"), self._levels),
                (_("Grayscale"), lambda: self._apply_filter("grayscale")),
                (_("Invert"), lambda: self._apply_filter("invert")),
                (_("Sepia"), lambda: self._apply_filter("sepia")),
            ],
            _("Blur"): [
                (_("Gaussian Blur"), self._blur),
            ],
            _("Sharpen"): [
                (_("Sharpen"), self._sharpen),
                (_("Edge Detect"), lambda: self._apply_filter("edge_detect")),
            ],
            _("Stylize"): [
                (_("Pixelate"), self._pixelate),
                (_("Posterize"), self._posterize),
            ],
        }

        for cat_name, items in categories.items():
            grp = QGroupBox(cat_name)
            grp_layout = QVBoxLayout(grp)
            for btn_name, callback in items:
                btn = QPushButton(btn_name)
                btn.clicked.connect(callback)
                grp_layout.addWidget(btn)
            left_layout.addWidget(grp)

        left_layout.addStretch()

        self.preview_label = QLabel(_("Preview"))
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background: #0a0a0a; border: 1px solid #333; color: #666;")

        layout.addWidget(left_panel, 1)
        layout.addWidget(self.preview_label, 2)

    def _apply_filter(self, name):
        from . import filters as f
        func = getattr(f, name, None)
        if func and self.canvas.layer_stack.active:
            self.canvas._save_state(name.replace("_", " ").title())
            self.canvas.layer_stack.active.image = func(self.canvas.layer_stack.active.image)
            self.canvas._refresh()

    def _bc(self):
        self._show_slider_dialog(_("Brightness / Contrast"), [
            (_("Brightness"), -255, 255, 0),
            (_("Contrast"), 0, 300, 100),
        ], lambda vals: self._apply_multi([
            ("brightness", vals[0]),
            ("contrast", vals[1] / 100.0),
        ]))

    def _hs(self):
        self._show_slider_dialog(_("Hue / Saturation"), [
            (_("Hue"), -180, 180, 0),
            (_("Saturation"), 0, 300, 100),
            (_("Lightness"), -100, 100, 0),
        ], lambda vals: self._apply_multi([
            ("hue_saturation", vals[0], vals[1] / 100.0, vals[2]),
        ]))

    def _levels(self):
        self._show_slider_dialog(_("Levels"), [
            (_("Shadow"), 0, 255, 0),
            (_("Mid (gamma)"), 10, 990, 100),
            (_("Highlight"), 0, 255, 255),
        ], lambda vals: self._apply_multi([
            ("levels", vals[0], vals[1] / 100.0, vals[2]),
        ]))

    def _blur(self):
        r, ok = QInputDialog.getInt(self, _("Gaussian Blur"), _("Radius:"), 3, 1, 100)
        if ok:
            self._apply_filter_arg("gaussian_blur", r)

    def _sharpen(self):
        a, ok = QInputDialog.getDouble(self, _("Sharpen"), _("Amount:"), 1.0, 0.1, 10.0)
        if ok:
            self._apply_filter_arg("sharpen", a)

    def _pixelate(self):
        s, ok = QInputDialog.getInt(self, _("Pixelate"), _("Block Size:"), 8, 2, 200)
        if ok:
            self._apply_filter_arg("pixelate", s)

    def _posterize(self):
        l, ok = QInputDialog.getInt(self, _("Posterize"), _("Levels:"), 4, 2, 64)
        if ok:
            self._apply_filter_arg("posterize", l)

    def _apply_filter_arg(self, name, *args):
        from . import filters as f
        func = getattr(f, name, None)
        if func and self.canvas.layer_stack.active:
            self.canvas._save_state(name.replace("_", " ").title())
            self.canvas.layer_stack.active.image = func(self.canvas.layer_stack.active.image, *args)
            self.canvas._refresh()

    def _apply_multi(self, steps):
        from . import filters as f
        layer = self.canvas.layer_stack.active
        if not layer:
            return
        self.canvas._save_state("Filter")
        img = layer.image
        for name, *args in steps:
            func = getattr(f, name, None)
            if func:
                img = func(img, *args)
        layer.image = img
        self.canvas._refresh()

    def _show_slider_dialog(self, title, sliders, on_apply):
        dialog = QDialog(self)
        dialog.setWindowTitle(_(title))
        layout = QVBoxLayout(dialog)

        spinboxes = []
        for label, lo, hi, default in sliders:
            row = QHBoxLayout()
            row.addWidget(QLabel(_(label) + ":"))
            s = QSlider(Qt.Horizontal)
            s.setRange(lo, hi)
            s.setValue(default)
            row.addWidget(s)
            layout.addLayout(row)
            spinboxes.append(s)

        btn = QPushButton(_("Apply"))
        btn.clicked.connect(lambda: (on_apply([s.value() for s in spinboxes]), dialog.close()))
        layout.addWidget(btn)
        dialog.exec_()


class ExportDialog(QDialog):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle(_("Export Image"))
        self.resize(450, 300)
        self.setStyleSheet("QDialog { background: #121212; }")

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.format_combo = QComboBox()
        self.format_combo.addItem(_("PNG (.png)"), '.png')
        self.format_combo.addItem(_("JPEG (.jpg)"), '.jpg')
        self.format_combo.addItem(_("WebP (.webp)"), '.webp')
        self.format_combo.addItem(_("TIFF (.tiff)"), '.tiff')
        self.format_combo.addItem(_("BMP (.bmp)"), '.bmp')
        self.format_combo.addItem(_("Photoshop PSD (.psd)"), '.psd')
        self.format_combo.currentIndexChanged.connect(self._update_options)
        form.addRow(_("Format:"), self.format_combo)

        self.quality_layout = QVBoxLayout()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(95)
        self.quality_label = QLabel("95")
        self.quality_slider.valueChanged.connect(lambda v: self.quality_label.setText(str(v)))
        q_row = QHBoxLayout()
        q_row.addWidget(self.quality_slider)
        q_row.addWidget(self.quality_label)
        self.quality_group = QGroupBox(_("Quality"))
        self.quality_group.setLayout(q_row)
        self.quality_layout.addWidget(self.quality_group)

        self.compression_layout = QVBoxLayout()
        self.compression_slider = QSlider(Qt.Horizontal)
        self.compression_slider.setRange(0, 9)
        self.compression_slider.setValue(6)
        self.compression_label = QLabel("6")
        self.compression_slider.valueChanged.connect(lambda v: self.compression_label.setText(str(v)))
        c_row = QHBoxLayout()
        c_row.addWidget(self.compression_slider)
        c_row.addWidget(self.compression_label)
        self.compression_group = QGroupBox(_("Compression"))
        self.compression_group.setLayout(c_row)
        self.compression_layout.addWidget(self.compression_group)

        self.tiff_comp_combo = QComboBox()
        self.tiff_comp_combo.addItems(['none', 'lzw', 'zip'])
        self.tiff_comp_group = QGroupBox(_("TIFF Compression"))
        t_row = QHBoxLayout()
        t_row.addWidget(self.tiff_comp_combo)
        self.tiff_comp_group.setLayout(t_row)
        self.compression_layout.addWidget(self.tiff_comp_group)

        self.options_widget = QWidget()
        self.options_widget.setStyleSheet("background: transparent;")
        opts_layout = QVBoxLayout(self.options_widget)
        opts_layout.addLayout(self.quality_layout)
        opts_layout.addLayout(self.compression_layout)
        form.addRow("Options:", self.options_widget)

        self.path_edit = QLineEdit()
        browse_btn = QPushButton(_("Browse..."))
        browse_btn.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse_btn)
        form.addRow(_("Output:"), path_row)

        layout.addLayout(form)

        self.size_label = QLabel(_("Estimated size: --"))
        layout.addWidget(self.size_label)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._export)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._update_options()

    def _update_options(self):
        ext = self.format_combo.currentData()
        try:
            from .file_io import get_export_options_for_format, FORMAT_REGISTRY
            opts = get_export_options_for_format(ext)
        except ImportError:
            return

        has_quality = 'quality' in opts
        has_compression = 'compression' in opts
        has_tiff_comp = ext in ('.tiff', '.tif') and 'compression' in opts

        self.quality_group.setVisible(has_quality)
        self.compression_group.setVisible(has_compression and not has_tiff_comp)
        self.tiff_comp_group.setVisible(has_tiff_comp)
        self.options_widget.setVisible(has_quality or has_compression or has_tiff_comp)

        if has_quality:
            lo, hi, default = opts['quality']
            self.quality_slider.setRange(lo, hi)
            self.quality_slider.setValue(default)
            self.quality_label.setText(str(default))

        if has_compression and not has_tiff_comp:
            lo, hi, default = opts['compression']
            self.compression_slider.setRange(lo, hi)
            self.compression_slider.setValue(default)
            self.compression_label.setText(str(default))

        self._update_size_estimate()

    def _update_size_estimate(self):
        composite = self.canvas.layer_stack.composite()
        w, h = composite.width(), composite.height()
        bpp = 4
        ext = self.format_combo.currentData()
        if ext == '.jpg':
            bpp = 3
        raw_size = w * h * bpp
        ratio = 0.3 if ext in ('.jpg', '.webp') else 0.5 if ext == '.png' else 1.0
        if ext == '.psd':
            try:
                from .file_io import FORMAT_REGISTRY
            except ImportError:
                pass
            num_layers = len(self.canvas.layer_stack.layers)
            estimated = raw_size * (1 + 0.3 * num_layers)
        else:
            estimated = raw_size * ratio
        if estimated > 1024 * 1024:
            self.size_label.setText(_("Estimated size: ") + f"{estimated / (1024*1024):.1f} MB")
        else:
            self.size_label.setText(_("Estimated size: ") + f"{estimated / 1024:.0f} KB")

    def _browse(self):
        ext = self.format_combo.currentData()
        try:
            from .file_io import FORMAT_REGISTRY
            info = FORMAT_REGISTRY.get(ext, {})
            name = info.get('name', ext.upper())
        except ImportError:
            name = ext.upper()
        path, _filter = QFileDialog.getSaveFileName(self, _("Export As"), "", f"{_(name)} (*{ext})")
        if path:
            self.path_edit.setText(path)
            self._update_size_estimate()

    def get_options(self):
        ext = self.format_combo.currentData()
        opts = {}
        try:
            from .file_io import FORMAT_REGISTRY
            info = FORMAT_REGISTRY.get(ext, {})
            export_opts = info.get('export_options', {})
        except ImportError:
            export_opts = {}

        if 'quality' in export_opts:
            opts['quality'] = self.quality_slider.value()
        if 'compression' in export_opts:
            if ext in ('.tiff', '.tif'):
                opts['compression'] = self.tiff_comp_combo.currentText()
            else:
                opts['compression'] = self.compression_slider.value()
        return ext, opts

    def _export(self):
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, _("Export"), _("Please select an output path."))
            return
        ext, opts = self.get_options()
        if not path.lower().endswith(ext):
            path += ext
        if self.canvas.save_image(path, opts):
            QMessageBox.information(self, _("Export"), _("Exported successfully to:") + f"\n{path}")
            self.accept()
        else:
            QMessageBox.critical(self, _("Export"), _("Export failed."))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        screen = QApplication.primaryScreen().availableGeometry()
        max_w = min(int(screen.width() * 0.75), screen.width())
        max_h = min(int(screen.height() * 0.8), screen.height())
        self.resize(min(max_w, 1400), min(max_h, 900))
        self.setMaximumSize(screen.width(), screen.height())

        self.canvas = CanvasView(self)

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self.canvas)
        self.video_mode = VideoMode()
        self.mode_stack.addWidget(self.video_mode)
        self.setCentralWidget(self.mode_stack)
        self.current_mode = "photo"

        self.settings = SettingsManager()
        self.settings.load()
        get_translator().language_changed.connect(lambda l: self.retranslate_ui())
        lang = self.settings.get('language', 'pt_BR')
        if lang and lang != 'system':
            get_translator().set_language(lang)

        # Tool palette (left) with embedded fg/bg swatches
        self.tool_palette = ToolPalette(lambda: self.canvas)
        self.addToolBar(Qt.LeftToolBarArea, self._make_toolbar_wrapper(self.tool_palette))

        # Tool options bar (top)
        self.tool_options = QToolBar(_("Tool Options"))
        self.tool_options.setMovable(False)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 5000)
        self.size_spin.setValue(3)
        self.size_spin.setFixedWidth(55)
        self.size_spin.valueChanged.connect(self.canvas.set_tool_size)
        self.tool_options.addWidget(QLabel(_("  Size:")))
        self.tool_options.addWidget(self.size_spin)

        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(1, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setSuffix("%")
        self.opacity_spin.setFixedWidth(50)
        self.opacity_spin.valueChanged.connect(self.canvas.set_tool_opacity)
        self.tool_options.addWidget(QLabel(_("  Opacity:")))
        self.tool_options.addWidget(self.opacity_spin)

        self.flow_spin = QSpinBox()
        self.flow_spin.setRange(1, 100)
        self.flow_spin.setValue(100)
        self.flow_spin.setSuffix("%")
        self.flow_spin.setFixedWidth(50)
        self.flow_spin.valueChanged.connect(self.canvas.set_tool_flow)
        self.tool_options.addWidget(QLabel(_("  Flow:")))
        self.tool_options.addWidget(self.flow_spin)

        self.tool_options.addSeparator()
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(24, 24)
        self.color_btn.setStyleSheet("background-color: #000; border: 1px solid #555; border-radius: 2px;")
        self.color_btn.clicked.connect(self._pick_color)
        self.tool_options.addWidget(QLabel(_("  Color:")))
        self.tool_options.addWidget(self.color_btn)

        self._shape_mode_labels = []
        self.tool_options.addSeparator()
        self.shape_mode_combo = QComboBox()
        self.shape_mode_combo.addItems(["Rectangle", "Ellipse"])
        self.shape_mode_combo.setFixedWidth(90)
        self.shape_mode_combo.currentTextChanged.connect(self._on_shape_mode_changed)
        slbl = QLabel(_("  Shape:"))
        self._shape_mode_labels.append(slbl)
        self.tool_options.addWidget(slbl)
        self.tool_options.addWidget(self.shape_mode_combo)

        self.tool_options.addSeparator()
        self.tool_options.addWidget(QLabel(_("  Font:")))
        self.font_combo = QComboBox()
        self.font_combo.addItems(QFontDatabase().families())
        self.font_combo.setCurrentText("Arial")
        self.font_combo.setFixedWidth(110)
        self.tool_options.addWidget(self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(1, 999)
        self.font_size_spin.setValue(32)
        self.font_size_spin.setFixedWidth(45)
        self.tool_options.addWidget(self.font_size_spin)

        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(22, 22)
        self.tool_options.addWidget(self.bold_btn)

        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(22, 22)
        self.tool_options.addWidget(self.italic_btn)

        self.underline_btn = QToolButton()
        self.underline_btn.setText("U")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(22, 22)
        self.tool_options.addWidget(self.underline_btn)

        self.addToolBar(self.tool_options)

        # Right side: Tabbed panels (like Photoshop)
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.North)
        self.right_tabs.setTabBarAutoHide(False)

        # Layers panel (most important, shown first)
        self.layer_panel = LayerPanel(lambda: self.canvas)
        self.right_tabs.addTab(self.layer_panel, _("Layers"))

        # Color panel
        self.color_panel = ColorPanel()
        self.color_panel.colorChanged.connect(self.canvas.set_foreground_color)
        self.color_panel.bgColorChanged.connect(self.canvas.set_background_color)
        self.right_tabs.addTab(self.color_panel, _("Color"))

        # Swatches panel
        self.swatches_panel = SwatchesPanel(lambda: self.canvas)
        self.swatches_panel.colorSelected.connect(self.canvas.set_foreground_color)
        self.swatches_panel.bgColorSelected.connect(self.canvas.set_background_color)
        self.right_tabs.addTab(self.swatches_panel, _("Swatches"))

        # Channels panel
        self.channels_panel = ChannelsPanel(lambda: self.canvas)
        self.right_tabs.addTab(self.channels_panel, _("Channels"))

        # Navigator panel
        self.nav_panel = NavigatorPanel(lambda: self.canvas)
        self.right_tabs.addTab(self.nav_panel, _("Navigator"))

        # History panel
        self.history_panel = HistoryPanel(lambda: self.canvas)
        self.right_tabs.addTab(self.history_panel, _("History"))

        # Gradient panel
        self.gradient_panel = GradientPanel(lambda: self.canvas)
        self.right_tabs.addTab(self.gradient_panel, _("Gradient"))

        # Brush panel
        self.brush_panel = BrushPanel(lambda: self.canvas)
        self.right_tabs.addTab(self.brush_panel, _("Brush"))

        # Path panel
        self.path_panel = PathPanel(lambda: self.canvas)
        self.right_tabs.addTab(self.path_panel, _("Path"))

        self.right_dock = QDockWidget(_("Panels"), self)
        self.right_dock.setWidget(self.right_tabs)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        # Initialize recent files before creating menus
        self.recent_files = []
        settings = QSettings()
        stored = settings.value('recent_files', [])
        if isinstance(stored, list) and stored:
            self.recent_files = [p for p in stored if os.path.exists(p)][:10]

        self.create_menus()
        self.create_statusbar()

        self.canvas.mouse_moved.connect(self._update_coords)
        self.canvas.status_changed.connect(self.statusBar().showMessage)
        self.canvas.color_picked.connect(self._sync_color_btn)
        self.canvas.color_picked.connect(self._sync_tool_palette_fg)
        self.canvas.color_picked.connect(self.color_panel.set_color)
        self.canvas.bg_color_changed.connect(self._sync_tool_palette_bg)
        self.canvas.bg_color_changed.connect(self.color_panel.set_bg_color)
        self.canvas.history_changed.connect(self.history_panel.refresh)
        self.canvas.zoom_changed.connect(self._update_zoom_label)
        self.canvas.zoom_changed.connect(self.nav_panel.set_zoom)
        self.canvas.tool_changed.connect(self._update_tool_label)
        self.canvas.tool_changed.connect(self.tool_palette.select_tool_by_name)

        self.current_path = None
        self._plugin_manager = self._init_plugins()
        self._update_dim_label()
        self.retranslate_ui()

    def _make_toolbar_wrapper(self, widget):
        tb = QToolBar(_("Tools"))
        tb.setMovable(False)
        tb.addWidget(widget)
        return tb

    def _sync_color_btn(self, color):
        self.color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #555; border-radius: 2px;"
        )

    def _sync_tool_palette_fg(self, color):
        self.tool_palette.fg_color = color
        self.tool_palette._update_swatches()

    def _sync_tool_palette_bg(self, color):
        self.tool_palette.bg_color = color
        self.tool_palette._update_swatches()

    def _pick_color(self):
        d = QColorDialog(self.canvas.tool_color, self)
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
            color = d.selectedColor()
            self.canvas.set_foreground_color(color)
            self._sync_color_btn(color)
            self.color_panel.set_color(color)

    def _show_about(self):
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.svg")
        msg = QMessageBox(self)
        msg.setWindowTitle(_("About reverseaffinity"))
        msg.setIconPixmap(QIcon(icon_path).pixmap(64, 64) if os.path.exists(icon_path) else QPixmap())
        msg.setText(
            _("<h2>reverseaffinity</h2>"
              "<p><b>Version 0.1.0</b></p>"
              "<p>A professional photo editor built with PyQt5.</p>"
              "<hr>"
              "<p><i>Inspired by Affinity Photo, Adobe Photoshop, and DaVinci Resolve.</i></p>"
              "<hr>"
              "<p style='font-size:11px; color:#888;'>"
              "Built with Python, PyQt5, NumPy<br>"
              "© 2026 reverseaffinity"
              "</p>")
        )
        msg.exec_()

    def _update_zoom_label(self, zoom):
        self.zoom_label.setText(f"{zoom * 100:.0f}%")

    def _update_dim_label(self):
        img = self.canvas.layer_stack.composite()
        self.dim_label.setText(f"{img.width()}x{img.height()}")

    def _update_tool_label(self):
        self.tool_label.setText(self.canvas.tool.name)
        is_shape = isinstance(self.canvas.tool, ShapeTool)
        self.shape_mode_combo.setVisible(is_shape)
        for lbl in self._shape_mode_labels:
            lbl.setVisible(is_shape)

    def _on_shape_mode_changed(self, mode):
        tool = self.canvas.tool
        if isinstance(tool, ShapeTool):
            tool.shape_mode = "ellipse" if mode == "Ellipse" else "rect"
            tool.name = f"{mode} Tool"
            self._update_tool_label()

    def _update_coords(self, x, y):
        self.coord_label.setText(_("X: ") + f"{int(x):4d}" + _("  Y: ") + f"{int(y):4d}")
        try:
            c = self.canvas.get_pixel_color(self.canvas.last_point or self.canvas.mapToScene(self.canvas.rect().center()))
            if c:
                self.info_label.setText(_("R:") + f"{c.red():3d}" + _(" G:") + f"{c.green():3d}" + _(" B:") + f"{c.blue():3d}")
        except Exception:
            pass

    def create_menus(self):
        mb = self.menuBar()

        file_m = mb.addMenu(_("&File"))
        file_m.addAction(_("&New..."), self._new_file, QKeySequence.New)
        file_m.addAction(_("&Open..."), self._open_file, QKeySequence.Open)
        file_m.addAction(_("&Place Image..."), self._place_image, QKeySequence("Ctrl+Shift+P"))
        self.open_recent_menu = file_m.addMenu(_("Open &Recent"))
        self._rebuild_recent_menu()
        file_m.addSeparator()
        file_m.addAction(_("&Save"), self._save_file, QKeySequence.Save)
        file_m.addAction(_("Save &As..."), self._save_as_file, QKeySequence("Ctrl+Shift+S"))
        file_m.addSeparator()
        exp_m = file_m.addMenu(_("&Export"))
        exp_m.addAction(_("Export &With Options..."), self._export_dialog)
        exp_m.addSeparator()
        exp_m.addAction(_("Export as &PNG..."), self._export_png)
        exp_m.addAction(_("Export as &JPEG..."), self._export_jpg)
        exp_m.addAction(_("Export as &WebP..."), self._export_webp)
        exp_m.addAction(_("Export as &PSD..."), self._export_psd)
        exp_m.addSeparator()
        exp_m.addAction(_("Batch Export &Layers..."), self._batch_export_layers)
        file_m.addSeparator()
        file_m.addAction(_("&Close"), self.close, QKeySequence("Ctrl+Q"))

        edit_m = mb.addMenu(_("&Edit"))
        edit_m.addAction(_("&Undo"), self._undo, QKeySequence.Undo)
        edit_m.addAction(_("&Redo"), self._redo, QKeySequence("Ctrl+Shift+Z"))
        edit_m.addSeparator()
        edit_m.addAction(_("&Paste"), self._paste_image, QKeySequence.Paste)
        edit_m.addAction(_("&Fill..."), self._fill)
        edit_m.addAction(_("&Clear"), self._clear)
        edit_m.addSeparator()
        edit_m.addAction(_("&Preferences..."), self._open_preferences)

        img_m = mb.addMenu(_("&Image"))
        img_m.addAction(_("&Resize..."), self._resize)
        img_m.addAction(_("&Canvas Size..."), self._canvas_size)
        img_m.addSeparator()
        img_m.addAction(_("&Flatten"), self._flatten)

        layer_m = mb.addMenu(_("&Layer"))
        layer_m.addAction(_("&New Layer"), self._new_layer, QKeySequence("Ctrl+Shift+N"))
        layer_m.addAction(_("&Duplicate Layer"), self._dup_layer)
        layer_m.addAction(_("&Delete Layer"), self._del_layer)
        layer_m.addSeparator()
        adj_m = layer_m.addMenu(_("New Adjustment Layer"))
        adj_m.addAction(_("Brightness / Contrast"), lambda: self._add_adjustment("brightness_contrast"))
        adj_m.addAction(_("Hue / Saturation"), lambda: self._add_adjustment("hsl"))
        adj_m.addAction(_("Levels"), lambda: self._add_adjustment("levels"))
        adj_m.addAction(_("Curves"), lambda: self._add_adjustment("curves"))
        layer_m.addSeparator()
        layer_m.addAction(_("Merge &Visible"), self._merge_visible)
        layer_m.addAction(_("&Flatten Image"), self._flatten)

        filter_m = mb.addMenu(_("F&ilter"))
        filter_m.addAction(_("&Filter Gallery..."), self._show_filter_gallery)

        view_m = mb.addMenu(_("&View"))
        view_m.addAction(_("Zoom &In"), self.canvas.zoom_in, QKeySequence("Ctrl++"))
        view_m.addAction(_("Zoom &Out"), self.canvas.zoom_out, QKeySequence("Ctrl+-"))
        view_m.addAction(_("Zoom to &100%"), self.canvas.zoom_100, QKeySequence("Ctrl+1"))
        view_m.addAction(_("Zoom to &Selection"), self.canvas.zoom_to_selection, QKeySequence("Ctrl+2"))
        view_m.addAction(_("&Fit to Screen"), self.canvas.zoom_fit, QKeySequence("Ctrl+0"))
        view_m.addSeparator()

        snap_m = view_m.addMenu(_("&Snap"))
        self.snap_enable_action = snap_m.addAction(_("Enable &Snap"))
        self.snap_enable_action.setCheckable(True)
        self.snap_enable_action.setChecked(True)
        self.snap_enable_action.setShortcut(QKeySequence("Ctrl+;"))
        self.snap_enable_action.triggered.connect(
            lambda v: setattr(self.canvas.snapping, 'enabled', v)
        )

        self.snap_grid_action = snap_m.addAction(_("Snap to &Grid"))
        self.snap_grid_action.setCheckable(True)
        self.snap_grid_action.setChecked(False)
        self.snap_grid_action.triggered.connect(
            lambda v: setattr(self.canvas.snapping, 'snap_to_grid', v)
        )

        self.snap_guides_action = snap_m.addAction(_("Snap to &Guides"))
        self.snap_guides_action.setCheckable(True)
        self.snap_guides_action.setChecked(True)
        self.snap_guides_action.triggered.connect(
            lambda v: setattr(self.canvas.snapping, 'snap_to_guides', v)
        )

        self.snap_layer_action = snap_m.addAction(_("Snap to &Layer"))
        self.snap_layer_action.setCheckable(True)
        self.snap_layer_action.setChecked(True)
        self.snap_layer_action.triggered.connect(
            lambda v: setattr(self.canvas.snapping, 'snap_to_layer', v)
        )

        self.snap_doc_action = snap_m.addAction(_("Snap to Document &Bounds"))
        self.snap_doc_action.setCheckable(True)
        self.snap_doc_action.setChecked(True)
        self.snap_doc_action.triggered.connect(
            lambda v: setattr(self.canvas.snapping, 'snap_to_document', v)
        )

        guides_m = view_m.addMenu(_("&Guides"))
        self.show_guides_action = guides_m.addAction(_("Show &Guides"))
        self.show_guides_action.setCheckable(True)
        self.show_guides_action.setChecked(True)
        self.show_guides_action.triggered.connect(
            lambda v: setattr(self.canvas.guide_mgr, 'visible', v) or self.canvas.viewport().update()
        )

        self.lock_guides_action = guides_m.addAction(_("&Lock Guides"))
        self.lock_guides_action.setCheckable(True)
        self.lock_guides_action.setChecked(False)
        self.lock_guides_action.triggered.connect(
            lambda v: setattr(self.canvas.guide_mgr, 'locked', v)
        )

        guides_m.addAction(_("&Clear Guides"), lambda: (
            self.canvas.guide_mgr.clear_guides(),
            self.canvas.viewport().update()
        ))

        guides_m.addAction(_("&New Guide..."), self._show_guide_dialog, QKeySequence("Ctrl+Shift+G"))

        view_m.addSeparator()
        ga = view_m.addAction(_("Show &Grid"))
        ga.setCheckable(True)
        ga.setChecked(False)
        ga.triggered.connect(lambda v: setattr(self.canvas, 'show_grid', v) or self.canvas.viewport().update())
        ra = view_m.addAction(_("Show &Rulers"))
        ra.setCheckable(True)
        ra.setChecked(True)
        ra.triggered.connect(lambda v: setattr(self.canvas, 'show_rulers', v) or self.canvas.viewport().update())
        view_m.addSeparator()
        view_m.addAction(_("&Reset View"), self.canvas.zoom_fit)

        view_m.addSeparator()
        self.mode_action = view_m.addAction(_("Switch to &Video Mode"), self._toggle_mode, QKeySequence("F5"))

        help_m = mb.addMenu(_("&Help"))
        help_m.addAction(_("&About reverseaffinity"), self._show_about)

    def create_statusbar(self):
        sb = self.statusBar()
        sb.showMessage(_("Ready"))
        self.tool_label = QLabel(_("Move Tool"))
        self.tool_label.setFixedWidth(150)
        sb.addPermanentWidget(self.tool_label)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(55)
        sb.addPermanentWidget(self.zoom_label)
        self.dim_label = QLabel("800x600")
        self.dim_label.setFixedWidth(75)
        sb.addPermanentWidget(self.dim_label)
        self.coord_label = QLabel(_("X: ") + "0" + _("  Y: ") + "0")
        sb.addPermanentWidget(self.coord_label)
        self.info_label = QLabel("")
        sb.addPermanentWidget(self.info_label)

    def _new_file(self):
        w, ok = QInputDialog.getInt(self, _("New Image"), _("Width:"), 1920, 1, 20000)
        if not ok:
            return
        h, ok = QInputDialog.getInt(self, _("New Image"), _("Height:"), 1080, 1, 20000)
        if not ok:
            return
        self.canvas.new_image(w, h)
        self.current_path = None
        self.setWindowTitle(_("reverseaffinity Photo - [Untitled ") + f"{w}x{h}]")
        self._update_dim_label()
        self.layer_panel.refresh()
        self.nav_panel.refresh()

    def _open_file(self):
        from .file_io import get_open_filter
        path, _filter = get_open_file_name(
            _("Open Image"), "",
            get_open_filter(), self
        )
        if path and self.canvas.open_image(path):
            self.current_path = path
            self._add_recent_file(path)
            self.setWindowTitle(_("reverseaffinity Photo - [") + path + "]")
            self.statusBar().showMessage(_("Opened: ") + path)
            self._update_dim_label()
            self.layer_panel.refresh()
            self.nav_panel.refresh()

    def _place_image(self):
        path, _filter = QFileDialog.getOpenFileName(
            self, _("Place Image"), "",
            _("Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp);;All Files (*)")
        )
        if path:
            layer = self.canvas.import_image_as_layer(path)
            if layer:
                self.statusBar().showMessage(_("Placed: ") + path)
                self.layer_panel.refresh()
                self.nav_panel.refresh()

    def _save_file(self):
        if self.current_path:
            self.canvas.save_image(self.current_path)
            self.statusBar().showMessage(_("Saved: ") + self.current_path)
        else:
            self._save_as_file()

    def _save_as_file(self):
        from .file_io import get_save_filter
        path, _filter = QFileDialog.getSaveFileName(
            self, _("Save Image"), "",
            get_save_filter()
        )
        if path:
            self.canvas.save_image(path)
            self.current_path = path
            self._add_recent_file(path)
            self.setWindowTitle(_("reverseaffinity Photo - [") + path + "]")
            self._update_dim_label()
            self.statusBar().showMessage(_("Saved: ") + path)

    def _export_png(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Export as PNG"), "", _("PNG (*.png)"))
        if path:
            self.canvas.save_image(path, {'compression': 6})

    def _export_jpg(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Export as JPEG"), "", _("JPEG (*.jpg *.jpeg)"))
        if path:
            self.canvas.save_image(path, {'quality': 95})

    def _export_webp(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Export as WebP"), "", _("WebP (*.webp)"))
        if path:
            self.canvas.save_image(path, {'quality': 80})

    def _export_psd(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Export as PSD"), "", _("Photoshop (*.psd)"))
        if path:
            self.canvas.save_image(path)

    def _export_dialog(self):
        dialog = ExportDialog(self.canvas, self)
        dialog.exec_()

    def _add_recent_file(self, path):
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        if len(self.recent_files) > 10:
            self.recent_files = self.recent_files[:10]
        settings = QSettings()
        settings.setValue('recent_files', self.recent_files)
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        self.open_recent_menu.clear()
        for path in self.recent_files:
            act = self.open_recent_menu.addAction(path)
            act.triggered.connect(lambda checked, p=path: self._open_recent(p))
        if not self.recent_files:
            act = self.open_recent_menu.addAction(_("(empty)"))
            act.setEnabled(False)

    def _open_recent(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, _("File Not Found"),
                                _("The file no longer exists:\n") + path)
            self.recent_files.remove(path)
            self._rebuild_recent_menu()
            return
        if self.canvas.open_image(path):
            self.current_path = path
            self._add_recent_file(path)
            self.setWindowTitle(_("reverseaffinity Photo - [") + path + "]")
            self.statusBar().showMessage(_("Opened: ") + path)
            self._update_dim_label()
            self.layer_panel.refresh()
            self.nav_panel.refresh()

    def _show_guide_dialog(self):
        dialog = GuideDialog(self)
        if dialog.exec_() and dialog.result_data:
            orient, pos = dialog.result_data
            if hasattr(self.canvas, 'guide_mgr'):
                self.canvas.guide_mgr.add_guide(orient, pos)
                self.canvas.viewport().update()

    def _batch_export_layers(self):
        from .batch import batch_export_layers
        path, _filter = QFileDialog.getSaveFileName(
            self, _("Batch Export Layers"), "",
            _("PNG (*.png);;JPEG (*.jpg);;WebP (*.webp);;TIFF (*.tiff);;BMP (*.bmp)")
        )
        if not path:
            return
        fmt = path.rsplit('.', 1)[-1] if '.' in path else 'png'
        batch_export_layers(self.canvas.layer_stack, path, fmt, parent=self)

    def _open_preferences(self):
        dialog = PreferencesDialog(self.settings, self)
        if dialog.exec_() == QDialog.Accepted:
            lang = self.settings.get('language', 'pt_BR')
            if lang and lang != 'system':
                get_translator().set_language(lang)
                self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(_("reverseaffinity Photo - [Untitled]"))
        self._rebuild_menus()
        self._rebuild_status_bar()
        self.layer_panel.refresh()
        self.nav_panel.refresh()
        self.history_panel.refresh()

    def _rebuild_menus(self):
        self.menuBar().clear()
        self.create_menus()

    def _rebuild_status_bar(self):
        self.coord_label.setText(_("X: ") + "0" + _("  Y: ") + "0")
        self.info_label.setText(_("R:") + "0" + _(" G:") + "0" + _(" B:") + "0")
        self.tool_label.setText(self.canvas.tool.name)
        self.dim_label.setText("")
        self.statusBar().showMessage(_("Ready"))

    def _toggle_mode(self):
        if self.current_mode == "photo":
            self.current_mode = "video"
            self.mode_stack.setCurrentIndex(1)
            self.mode_action.setText(_("Switch to &Photo Mode"))
            self.tool_palette.parent().hide()
            self.tool_options.hide()
            self.right_dock.hide()
            self.console_dock.hide()
            self.setWindowTitle(_("reverseaffinity Video - [Untitled]"))
        else:
            self.current_mode = "photo"
            self.mode_stack.setCurrentIndex(0)
            self.mode_action.setText(_("Switch to &Video Mode"))
            self.tool_palette.parent().show()
            self.tool_options.show()
            self.right_dock.show()
            self.console_dock.show()
            self.setWindowTitle(_("reverseaffinity Photo - [Untitled]"))

    def _paste_image(self):
        if self.canvas.paste_from_clipboard():
            self.statusBar().showMessage(_("Pasted image from clipboard"))
            self.layer_panel.refresh()
            self.nav_panel.refresh()

    def _undo(self):
        if self.canvas.history.can_undo():
            self.canvas.history.undo(self.canvas.layer_stack)
            self.canvas._refresh()
            self.layer_panel.refresh()

    def _redo(self):
        if self.canvas.history.can_redo():
            self.canvas.history.redo(self.canvas.layer_stack)
            self.canvas._refresh()
            self.layer_panel.refresh()

    def _fill(self):
        layer = self.canvas.layer_stack.active
        if not layer or layer.locked:
            return
        color = QColorDialog.getColor(self.canvas.tool_color, self)
        if color.isValid():
            self.canvas._save_state("Fill")
            layer.image.fill(color)
            self.canvas._refresh()

    def _clear(self):
        layer = self.canvas.layer_stack.active
        if not layer or layer.locked:
            return
        self.canvas._save_state("Clear")
        layer.image.fill(Qt.transparent if layer.name != "Background" else Qt.white)
        self.canvas._refresh()

    def _resize(self):
        img = self.canvas.layer_stack.composite()
        w, ok1 = QInputDialog.getInt(self, _("Resize"), _("Width:"), img.width(), 1, 50000)
        if not ok1:
            return
        h, ok2 = QInputDialog.getInt(self, _("Resize"), _("Height:"), img.height(), 1, 50000)
        if not ok2:
            return
        self.canvas._save_state("Resize")
        for layer in self.canvas.layer_stack.layers:
            layer.image = layer.image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.canvas._refresh()
        self._update_dim_label()

    def _canvas_size(self):
        img = self.canvas.layer_stack.composite()
        w, ok1 = QInputDialog.getInt(self, _("Canvas Size"), _("Width:"), img.width(), 1, 50000)
        if not ok1:
            return
        h, ok2 = QInputDialog.getInt(self, _("Canvas Size"), _("Height:"), img.height(), 1, 50000)
        if not ok2:
            return
        self.canvas._save_state("Canvas Size")
        for layer in self.canvas.layer_stack.layers:
            new_img = QImage(w, h, QImage.Format_ARGB32)
            new_img.fill(Qt.transparent)
            p = __import__('PyQt5.QtGui', fromlist=['QPainter']).QPainter(new_img)
            p.drawImage(0, 0, layer.image)
            p.end()
            layer.image = new_img
        self.canvas._refresh()

    def _new_layer(self):
        self.canvas._save_state("New layer")
        self.canvas.layer_stack.add_layer()
        self.canvas._refresh()
        self.layer_panel.refresh()

    def _dup_layer(self):
        idx = self.canvas.layer_stack.active_index
        self.canvas._save_state("Duplicate layer")
        self.canvas.layer_stack.duplicate_layer(idx)
        self.canvas._refresh()
        self.layer_panel.refresh()

    def _del_layer(self):
        idx = self.canvas.layer_stack.active_index
        if idx >= 0:
            self.canvas._save_state("Delete layer")
            self.canvas.layer_stack.remove_layer(idx)
            self.canvas._refresh()
            self.layer_panel.refresh()

    def _merge_visible(self):
        self.canvas._save_state("Merge visible")
        self.canvas.layer_stack.merge_visible()
        self.canvas._refresh()
        self.layer_panel.refresh()

    def _flatten(self):
        self.canvas._save_state("Flatten")
        self.canvas.layer_stack.flatten()
        self.canvas._refresh()
        self.layer_panel.refresh()

    def _add_adjustment(self, adj_type):
        canvas = self.canvas
        from .layers import AdjustmentLayer
        from .filters import adjustment_brightness_contrast, adjustment_hsl, adjustment_levels, adjustment_curves

        params = {}
        if adj_type == "brightness_contrast":
            dialog = QDialog(self)
            dialog.setWindowTitle(_("Brightness / Contrast"))
            layout = QVBoxLayout(dialog)
            b_slider = QSlider(Qt.Horizontal)
            b_slider.setRange(-255, 255)
            b_slider.setValue(0)
            layout.addWidget(QLabel(_("Brightness:")))
            layout.addWidget(b_slider)
            c_slider = QSlider(Qt.Horizontal)
            c_slider.setRange(0, 300)
            c_slider.setValue(100)
            layout.addWidget(QLabel(_("Contrast:")))
            layout.addWidget(c_slider)
            def on_ok():
                params['brightness'] = b_slider.value()
                params['contrast'] = c_slider.value()
                dialog.accept()
            btn = QPushButton(_("OK"))
            btn.clicked.connect(on_ok)
            layout.addWidget(btn)
            dialog.exec_()
            func = adjustment_brightness_contrast

        elif adj_type == "hsl":
            dialog = QDialog(self)
            dialog.setWindowTitle(_("Hue / Saturation"))
            layout = QVBoxLayout(dialog)
            h_slider = QSlider(Qt.Horizontal)
            h_slider.setRange(-180, 180)
            h_slider.setValue(0)
            layout.addWidget(QLabel(_("Hue:")))
            layout.addWidget(h_slider)
            s_slider = QSlider(Qt.Horizontal)
            s_slider.setRange(0, 300)
            s_slider.setValue(100)
            layout.addWidget(QLabel(_("Saturation:")))
            layout.addWidget(s_slider)
            l_slider = QSlider(Qt.Horizontal)
            l_slider.setRange(-100, 100)
            l_slider.setValue(0)
            layout.addWidget(QLabel(_("Lightness:")))
            layout.addWidget(l_slider)
            def on_ok():
                params['hue'] = h_slider.value()
                params['saturation'] = s_slider.value()
                params['lightness'] = l_slider.value()
                dialog.accept()
            btn = QPushButton(_("OK"))
            btn.clicked.connect(on_ok)
            layout.addWidget(btn)
            dialog.exec_()
            func = adjustment_hsl

        elif adj_type == "levels":
            dialog = QDialog(self)
            dialog.setWindowTitle(_("Levels"))
            layout = QVBoxLayout(dialog)
            sh_slider = QSlider(Qt.Horizontal)
            sh_slider.setRange(0, 255)
            sh_slider.setValue(0)
            layout.addWidget(QLabel(_("Shadow:")))
            layout.addWidget(sh_slider)
            m_slider = QSlider(Qt.Horizontal)
            m_slider.setRange(10, 990)
            m_slider.setValue(100)
            layout.addWidget(QLabel(_("Mid (gamma):")))
            layout.addWidget(m_slider)
            hi_slider = QSlider(Qt.Horizontal)
            hi_slider.setRange(0, 255)
            hi_slider.setValue(255)
            layout.addWidget(QLabel(_("Highlight:")))
            layout.addWidget(hi_slider)
            def on_ok():
                params['shadow'] = sh_slider.value()
                params['mid'] = m_slider.value()
                params['highlight'] = hi_slider.value()
                dialog.accept()
            btn = QPushButton(_("OK"))
            btn.clicked.connect(on_ok)
            layout.addWidget(btn)
            dialog.exec_()
            func = adjustment_levels

        elif adj_type == "curves":
            dialog = QDialog(self)
            dialog.setWindowTitle(_("Curves"))
            layout = QVBoxLayout(dialog)

            class CurveGraph(QWidget):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.setFixedSize(256, 256)
                    self.points = [(0.0, 0.0), (1.0, 1.0)]
                    self.drag_idx = -1

                def paintEvent(self, ev):
                    p = QPainter(self)
                    p.setRenderHint(QPainter.Antialiasing)
                    p.fillRect(self.rect(), QColor(30, 30, 30))
                    p.setPen(QPen(QColor(60, 60, 60), 1))
                    for i in range(5):
                        x = i * 64
                        p.drawLine(x, 0, x, 256)
                        p.drawLine(0, x, 256, x)
                    p.setPen(QPen(QColor(100, 150, 255), 2))
                    pts = sorted(self.points, key=lambda pt: pt[0])
                    path = QPainterPath()
                    path.moveTo(pts[0][0] * 256, 256 - pts[0][1] * 256)
                    for i in range(1, len(pts)):
                        path.lineTo(pts[i][0] * 256, 256 - pts[i][1] * 256)
                    p.drawPath(path)
                    p.setBrush(QColor(200, 200, 200))
                    p.setPen(Qt.NoPen)
                    for px, py in pts:
                        p.drawEllipse(QPointF(px * 256, 256 - py * 256), 4, 4)
                    p.end()

                def mousePressEvent(self, ev):
                    x, y = ev.x() / 256.0, 1.0 - ev.y() / 256.0
                    x = max(0.0, min(1.0, x))
                    y = max(0.0, min(1.0, y))
                    for i, (px, py) in enumerate(self.points):
                        if abs(px - x) < 0.04 and abs(py - y) < 0.04:
                            self.drag_idx = i
                            return
                    self.points.append((x, y))
                    self.drag_idx = len(self.points) - 1
                    self.update()

                def mouseMoveEvent(self, ev):
                    if self.drag_idx < 0:
                        return
                    x, y = ev.x() / 256.0, 1.0 - ev.y() / 256.0
                    x = max(0.0, min(1.0, x))
                    y = max(0.0, min(1.0, y))
                    self.points[self.drag_idx] = (x, y)
                    self.update()

                def mouseReleaseEvent(self, ev):
                    self.drag_idx = -1

            graph = CurveGraph()
            layout.addWidget(graph)
            def on_ok():
                pts = sorted(graph.points, key=lambda pt: pt[0])
                params['points'] = pts
                dialog.accept()
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton(_("OK"))
            ok_btn.clicked.connect(on_ok)
            reset_btn = QPushButton(_("Reset"))
            def on_reset():
                graph.points = [(0.0, 0.0), (1.0, 1.0)]
                graph.update()
            reset_btn.clicked.connect(on_reset)
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(reset_btn)
            layout.addLayout(btn_layout)
            dialog.exec_()
            func = adjustment_curves

        if not params:
            return
        canvas._save_state(f"Add {adj_type} adjustment")
        w = canvas.layer_stack.layers[0].image.width()
        h = canvas.layer_stack.layers[0].image.height()
        adj = AdjustmentLayer(w, h, f"{adj_type.replace('_', ' ').title()}", func, params)
        canvas.layer_stack.layers.append(adj)
        canvas.layer_stack.active_index = len(canvas.layer_stack.layers) - 1
        canvas._refresh()
        self.layer_panel.refresh()

    def _show_filter_gallery(self):
        dialog = FilterGalleryDialog(self.canvas, self)
        dialog.exec_()
        self.canvas._refresh()

    def _init_plugins(self):
        try:
            from plugins import PluginManager
            mgr = PluginManager(plugin_dir=os.path.join(os.path.dirname(__file__), "..", "plugins"))
            mgr.discover()
            ctx = {
                "canvas": self.canvas,
                "main_window": self,
                "menu_bar": self.menuBar(),
                "tab_widget": self.right_tabs,
            }
            for plugin in mgr.plugins:
                try:
                    plugin.on_load(ctx)
                    for filt_name, filt_func in plugin.register_filters():
                        self.canvas._plugin_filters[filt_name] = filt_func
                    plugin.register_menu_items(self.menuBar())
                    plugin.register_panels(self.right_tabs)
                except Exception:
                    pass
            if mgr.plugins:
                self.statusBar().showMessage(
                    _("Plugins loaded: %d") % len(mgr.plugins), 3000
                )
            return mgr
        except Exception:
            pass


def main():
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("reverseaffinity")
        app.setOrganizationName("reverseaffinity")
    app.setApplicationDisplayName("reverseaffinity Photo")

    from editor.resources import apply_dark_theme
    apply_dark_theme(app)

    icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.setWindowTitle("reverseaffinity Photo - [Untitled]")
    window.show()

    if QApplication.instance() is app:
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
