import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QGroupBox, QGridLayout, QColorDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage
from editor.i18n import _


class ChromaKeyWidget(QWidget):
    paramsChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_color = QColor(0, 255, 0)
        self._params = {
            "hue_tolerance": 30,
            "sat_tolerance": 40,
            "val_tolerance": 40,
            "softness": 10,
            "edge_feather": 2,
            "spill_suppress": 30,
        }
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel(_("Chroma Key"))
        tf = title.font()
        tf.setBold(True)
        tf.setPointSize(11)
        title.setFont(tf)
        layout.addWidget(title)

        color_btn = QPushButton(_("Pick Key Color"))
        color_btn.clicked.connect(self._pick_color)
        self._color_indicator = QLabel()
        self._color_indicator.setFixedSize(40, 24)
        self._color_indicator.setStyleSheet(
            f"background-color: {self._key_color.name()}; border: 1px solid #555; border-radius: 3px;"
        )
        color_row = QHBoxLayout()
        color_row.addWidget(self._color_indicator)
        color_row.addWidget(color_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        key_name = QLabel(_("Key: Green") + f"  RGB({self._key_color.red()}, {self._key_color.green()}, {self._key_color.blue()})")
        key_name.setStyleSheet("color: #888; font-size: 10px;")
        self._key_label = key_name
        layout.addWidget(key_name)

        sliders = [
            ("hue_tolerance", _("Hue Tolerance"), 1, 180, 30),
            ("sat_tolerance", _("Sat Tolerance"), 1, 255, 40),
            ("val_tolerance", _("Val Tolerance"), 1, 255, 40),
            ("softness", _("Softness"), 0, 100, 10),
            ("edge_feather", _("Edge Feather"), 0, 20, 2),
            ("spill_suppress", _("Spill Suppress"), 0, 100, 30),
        ]
        for key, label, vmin, vmax, default in sliders:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            s = QSlider(Qt.Horizontal)
            s.setRange(vmin, vmax)
            s.setValue(default)
            val_lbl = QLabel(str(default))
            val_lbl.setFixedWidth(30)
            val_lbl.setAlignment(Qt.AlignRight)
            s.valueChanged.connect(
                lambda val, k=key, l=val_lbl: self._on_value(k, val, l)
            )
            row.addWidget(s, 1)
            row.addWidget(val_lbl)
            layout.addLayout(row)

    def _pick_color(self):
        color = QColorDialog.getColor(self._key_color, self, _("Select Chroma Key Color"))
        if color.isValid():
            self._key_color = color
            self._color_indicator.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #555; border-radius: 3px;"
            )
            self._key_label.setText(
                _("Key: ") + color.name() +
                f"  RGB({color.red()}, {color.green()}, {color.blue()})"
            )
            self._emit_params()

    def _on_value(self, key, val, label):
        self._params[key] = val
        label.setText(str(val))
        self._emit_params()

    def _emit_params(self):
        p = dict(self._params)
        p["key_r"] = self._key_color.red()
        p["key_g"] = self._key_color.green()
        p["key_b"] = self._key_color.blue()
        self.paramsChanged.emit(p)

    def apply_to_image(self, image, bg_image=None):
        image = image.convertToFormat(QImage.Format_ARGB32)
        w, h = image.width(), image.height()

        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = bytearray(ptr.asstring())

        kr = self._key_color.red()
        kg = self._key_color.green()
        kb = self._key_color.blue()
        ht = self._params["hue_tolerance"]
        st = self._params["sat_tolerance"]
        vt = self._params["val_tolerance"]
        soft = self._params["softness"] / 100.0
        feather = self._params["edge_feather"]
        spill = self._params["spill_suppress"] / 100.0

        key_qcolor = QColor(kr, kg, kb)
        key_hue = key_qcolor.hue() if key_qcolor.hue() >= 0 else 0
        key_sat = key_qcolor.saturation()
        key_val = key_qcolor.value()

        bg = None
        if bg_image:
            bg = bg_image.convertToFormat(QImage.Format_ARGB32)
            bg_ptr = bg.bits()
            if bg_ptr:
                bg_ptr.setsize(bg.byteCount())
                bg_arr = bytearray(bg_ptr.asstring())

        for i in range(0, len(arr), 4):
            b, g, r, a = arr[i], arr[i+1], arr[i+2], arr[i+3]

            pixel = QColor(r, g, b)
            ph_hue = pixel.hue() if pixel.hue() >= 0 else 0
            ph_sat = pixel.saturation()
            ph_val = pixel.value()

            dh = abs(ph_hue - key_hue)
            dh = min(dh, 360 - dh)
            ds = abs(ph_sat - key_sat)
            dv = abs(ph_val - key_val)

            if dh <= ht and ds <= st and dv <= vt:
                key_amount = 1.0
                if dh > ht * (1 - soft):
                    key_amount *= max(0, (ht - dh) / (ht * soft + 0.01))
                if ds > st * (1 - soft):
                    key_amount *= max(0, (st - ds) / (st * soft + 0.01))
                if dv > vt * (1 - soft):
                    key_amount *= max(0, (vt - dv) / (vt * soft + 0.01))
                key_amount = max(0, min(1, key_amount))

                new_a = int(a * (1 - key_amount))

                if spill > 0 and key_amount > 0.5:
                    r_adj = int(r * (1 - spill * key_amount * 0.3))
                    g_adj = int(g * (1 - spill * key_amount * 0.5))
                    b_adj = int(b * (1 - spill * key_amount * 0.3))
                    arr[i] = max(0, min(255, b_adj))
                    arr[i+1] = max(0, min(255, g_adj))
                    arr[i+2] = max(0, min(255, r_adj))

                arr[i+3] = max(0, new_a)

                if bg and bg_arr and new_a < 255:
                    bi = i
                    if bi < len(bg_arr):
                        bb, bg_, br, ba = bg_arr[bi], bg_arr[bi+1], bg_arr[bi+2], bg_arr[bi+3]
                        alpha = (255 - new_a) / 255.0
                        arr[i] = int(arr[i] * (1 - alpha) + bb * alpha)
                        arr[i+1] = int(arr[i+1] * (1 - alpha) + bg_ * alpha)
                        arr[i+2] = int(arr[i+2] * (1 - alpha) + br * alpha)
                        arr[i+3] = 255

        return QImage(arr, w, h, image.bytesPerLine(), QImage.Format_ARGB32)

    def params(self):
        return dict(self._params)
