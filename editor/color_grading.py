import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QFrame, QScrollArea, QGridLayout, QSizePolicy,
    QSpinBox, QDoubleSpinBox, QGroupBox, QDial,
)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPixmap, QImage, QLinearGradient,
    QRadialGradient, QConicalGradient, QPen, QBrush, QFont,
    qRgb, qRgba, qAlpha, qRed, qGreen, qBlue,
)
from editor.i18n import _


class ColorWheel(QWidget):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self.setMaximumSize(200, 200)
        self._hue = 0
        self._sat = 0
        self._val = 255
        self._wheel_pixmap = None
        self._dragging = False
        self._drag_target = None

    def set_color(self, color):
        self._hue = color.hue() if color.hue() >= 0 else 0
        self._sat = color.saturation()
        self._val = color.value()
        self._render_wheel()
        self.update()

    def color(self):
        c = QColor()
        c.setHsv(self._hue, self._sat, self._val)
        return c

    def _render_wheel(self):
        s = self.width()
        self._wheel_pixmap = QPixmap(s, s)
        self._wheel_pixmap.fill(Qt.transparent)
        p = QPainter(self._wheel_pixmap)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = s / 2, s / 2
        outer_r = s / 2 - 4
        inner_r = outer_r * 0.65

        for a in range(0, 360, 2):
            hue = a
            c = QColor()
            c.setHsv(hue, 255, 255)
            p.setPen(QPen(c, 3))
            rad1 = math.radians(a)
            rad2 = math.radians(a + 2)
            x1 = cx + outer_r * math.cos(rad1)
            y1 = cy + outer_r * math.sin(rad1)
            x2 = cx + inner_r * math.cos(rad1)
            y2 = cy + inner_r * math.sin(rad1)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        for y in range(int(cy - inner_r), int(cy + inner_r)):
            for x in range(int(cx - inner_r), int(cx + inner_r)):
                dx, dy = x - cx, y - cy
                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= inner_r:
                    hue = self._hue
                    sat = int(255 * dist / inner_r)
                    angle = math.atan2(dy, dx)
                    ang_deg = math.degrees(angle) % 360
                    hue = int(ang_deg)
                    c = QColor()
                    c.setHsv(hue, sat, self._val)
                    p.setPen(c)
                    p.drawPoint(x, y)

        p.end()

    def _pos_to_color(self, pos):
        s = self.width()
        cx, cy = s / 2, s / 2
        dx, dy = pos.x() - cx, pos.y() - cy
        dist = math.sqrt(dx*dx + dy*dy)
        outer_r = s / 2 - 4
        inner_r = outer_r * 0.65

        if dist < 8:
            return

        hue = int(math.degrees(math.atan2(dy, dx))) % 360

        if dist > inner_r and dist <= outer_r:
            self._hue = hue
            self._sat = 255
            self._val = 255
        elif dist <= inner_r:
            self._hue = hue
            self._sat = int(255 * dist / inner_r)
            self._val = 255

        self.update()
        self.colorChanged.emit(self.color())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._pos_to_color(event.pos())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._pos_to_color(event.pos())

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        cx, cy = s / 2, s / 2
        outer_r = s / 2 - 4
        inner_r = outer_r * 0.65

        if self._wheel_pixmap is None or self._wheel_pixmap.size() != self.size():
            self._render_wheel()

        p.drawPixmap(0, 0, self._wheel_pixmap)

        picker_angle = math.radians(self._hue)
        picker_r = (outer_r + inner_r) / 2
        px = cx + picker_r * math.cos(picker_angle)
        py = cy + picker_r * math.sin(picker_angle)
        p.setPen(QPen(Qt.white, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(int(px) - 6, int(py) - 6, 12, 12)

        sv_angle = math.radians(self._hue)
        sv_r = self._sat / 255.0 * inner_r
        sx = cx + sv_r * math.cos(sv_angle)
        sy = cy + sv_r * math.sin(sv_angle)
        p.setPen(QPen(Qt.black, 2))
        p.drawEllipse(int(sx) - 5, int(sy) - 5, 10, 10)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._wheel_pixmap = None
        self.update()


class ColorGradingPanel(QWidget):
    paramsChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = {
            "lift_r": 0, "lift_g": 0, "lift_b": 0,
            "gamma_r": 0, "gamma_g": 0, "gamma_b": 0,
            "gain_r": 0, "gain_g": 0, "gain_b": 0,
            "exposure": 0.0, "contrast": 0.0, "saturation": 0.0, "hue_shift": 0,
        }
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        title = QLabel(_("Color Grading"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title.setFont(title_font)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_w = QWidget()
        scroll_l = QVBoxLayout(scroll_w)
        scroll_l.setContentsMargins(0, 0, 0, 0)
        scroll_l.setSpacing(8)

        for name, label in [
            ("master", _("Master")),
            ("lift", _("Lift (Shadows)")),
            ("gamma", _("Gamma (Midtones)")),
            ("gain", _("Gain (Highlights)")),
        ]:
            gb = self._make_section(name, label)
            scroll_l.addWidget(gb)

        scroll_l.addStretch()
        scroll.setWidget(scroll_w)
        layout.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        reset_btn = QPushButton(_("Reset All"))
        reset_btn.clicked.connect(self._reset_all)
        btn_row.addStretch()
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

    def _make_section(self, name, title):
        gb = QGroupBox(title)
        gb.setCheckable(True)
        gb.setChecked(True)
        gl = QGridLayout(gb)
        gl.setSpacing(4)

        if name == "master":
            sliders = [
                ("exposure", _("Exposure"), -2.0, 2.0, 0.01, 0.0),
                ("contrast", _("Contrast"), -1.0, 1.0, 0.01, 0.0),
                ("saturation", _("Saturation"), -1.0, 1.0, 0.01, 0.0),
                ("hue_shift", _("Hue Shift"), -180, 180, 1, 0),
            ]
            for row, (key, lbl, vmin, vmax, step, default) in enumerate(sliders):
                gl.addWidget(QLabel(lbl), row, 0)
                s = QSlider(Qt.Horizontal)
                s.setRange(int(vmin / step), int(vmax / step))
                s.setValue(0)
                s.valueChanged.connect(
                    lambda val, k=key, st=step: self._on_slider(k, val * st)
                )
                val_label = QLabel(f"{default:.2f}")
                val_label.setFixedWidth(50)
                val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                s.valueChanged.connect(
                    lambda val, lbl=val_label, k=key, st=step: lbl.setText(
                        f"{val * st:.2f}" if isinstance(default, float) else f"{int(val * st)}"
                    )
                )
                gl.addWidget(s, row, 1)
                gl.addWidget(val_label, row, 2)
        else:
            channels = [
                ("_r", _("R"), "red"),
                ("_g", _("G"), "green"),
                ("_b", _("B"), "blue"),
            ]
            for row, (ch_suf, ch_lbl, ch_color) in enumerate(channels):
                gl.addWidget(QLabel(ch_lbl), row, 0)
                s = QSlider(Qt.Horizontal)
                s.setRange(-100, 100)
                s.setValue(0)
                key = name + ch_suf
                s.valueChanged.connect(
                    lambda val, k=key: self._on_slider(k, val / 100.0)
                )
                val_label = QLabel("0.00")
                val_label.setFixedWidth(50)
                val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                s.valueChanged.connect(
                    lambda val, lbl=val_label: lbl.setText(f"{val / 100.0:.2f}")
                )
                color_name = {"red": "#ff4444", "green": "#44ff44", "blue": "#4488ff"}[ch_color]
                s.setStyleSheet(
                    f"QSlider::handle:horizontal {{ background: {color_name}; width: 14px; margin: -3px 0; border-radius: 7px; }}"
                )
                gl.addWidget(s, row, 1)
                gl.addWidget(val_label, row, 2)

        return gb

    def _on_slider(self, key, value):
        self._params[key] = round(value, 4)
        self.paramsChanged.emit(self._params)

    def _reset_all(self):
        for k in self._params:
            self._params[k] = 0
        for gb in self.findChildren(QGroupBox):
            for slider in gb.findChildren(QSlider):
                slider.blockSignals(True)
                slider.setValue(0)
                slider.blockSignals(False)
        self.paramsChanged.emit(self._params)

    def params(self):
        return dict(self._params)

    def apply_to_image(self, image):
        if image.isNull():
            return image
        image = image.convertToFormat(QImage.Format_ARGB32)
        w, h = image.width(), image.height()
        ptr = image.bits()
        if ptr is None:
            return image
        ptr.setsize(image.byteCount())
        arr = bytearray(ptr.asstring())

        exposure = self._params["exposure"]
        contrast = 1.0 + self._params["contrast"]
        saturation = 1.0 + self._params["saturation"]
        hue_shift = self._params["hue_shift"]

        lift_r = self._params["lift_r"]
        lift_g = self._params["lift_g"]
        lift_b = self._params["lift_b"]
        gamma_r = 1.0 + self._params["gamma_r"]
        gamma_g = 1.0 + self._params["gamma_g"]
        gamma_b = 1.0 + self._params["gamma_b"]
        gain_r = 1.0 + self._params["gain_r"]
        gain_g = 1.0 + self._params["gain_g"]
        gain_b = 1.0 + self._params["gain_b"]

        for i in range(0, len(arr), 4):
            b, g, r, a = arr[i], arr[i+1], arr[i+2], arr[i+3]

            flt_r = r / 255.0
            flt_g = g / 255.0
            flt_b = b / 255.0

            flt_r = flt_r * gain_r + lift_r
            flt_g = flt_g * gain_g + lift_g
            flt_b = flt_b * gain_b + lift_b

            if gamma_r != 1.0:
                flt_r = math.pow(max(flt_r, 0.001), 1.0 / gamma_r)
            if gamma_g != 1.0:
                flt_g = math.pow(max(flt_g, 0.001), 1.0 / gamma_g)
            if gamma_b != 1.0:
                flt_b = math.pow(max(flt_b, 0.001), 1.0 / gamma_b)

            flt_r += exposure
            flt_g += exposure
            flt_b += exposure

            flt_r = (flt_r - 0.5) * contrast + 0.5
            flt_g = (flt_g - 0.5) * contrast + 0.5
            flt_b = (flt_b - 0.5) * contrast + 0.5

            if saturation != 1.0 or hue_shift != 0:
                gray = 0.299 * flt_r + 0.587 * flt_g + 0.114 * flt_b
                flt_r = gray + saturation * (flt_r - gray)
                flt_g = gray + saturation * (flt_g - gray)
                flt_b = gray + saturation * (flt_b - gray)

            arr[i] = max(0, min(255, int(flt_b * 255)))
            arr[i+1] = max(0, min(255, int(flt_g * 255)))
            arr[i+2] = max(0, min(255, int(flt_r * 255)))

        return QImage(arr, w, h, image.bytesPerLine(), QImage.Format_ARGB32)
