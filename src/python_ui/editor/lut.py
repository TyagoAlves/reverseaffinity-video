import os
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QColor
from editor.i18n import _


def parse_cube_file(path):
    title = os.path.basename(path)
    lut_3d = None
    size = 32
    domain_min = [0.0, 0.0, 0.0]
    domain_max = [1.0, 1.0, 1.0]

    with open(path, "r") as f:
        lines = f.readlines()

    data_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("!"):
            continue
        if stripped.lower().startswith("title"):
            title = stripped.split(None, 1)[1].strip('"').strip("'") if len(stripped.split(None, 1)) > 1 else title
        elif stripped.lower().startswith("lut_1d_size"):
            return _parse_1d(lines, i + 1, int(stripped.split()[-1]))
        elif stripped.lower().startswith("lut_3d_size"):
            size = int(stripped.split()[-1])
        elif stripped.lower().startswith("domain_min"):
            parts = stripped.split()
            if len(parts) >= 4:
                domain_min = [float(parts[1]), float(parts[2]), float(parts[3])]
        elif stripped.lower().startswith("domain_max"):
            parts = stripped.split()
            if len(parts) >= 4:
                domain_max = [float(parts[1]), float(parts[2]), float(parts[3])]
        elif stripped and (stripped[0].isdigit() or stripped[0] in "+-"):
            if data_start is None:
                data_start = i

    if data_start is None:
        return None

    data = []
    for line in lines[data_start:]:
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                data.append([float(parts[0]), float(parts[1]), float(parts[2])])
            except ValueError:
                continue

    if len(data) == size ** 3:
        lut_3d = data
    else:
        idx = 0
        lut_3d = []
        for b in range(size):
            for g in range(size):
                for r in range(size):
                    if idx < len(data):
                        lut_3d.append(data[idx])
                    else:
                        lut_3d.append([r / (size - 1), g / (size - 1), b / (size - 1)])
                    idx += 1

    return {
        "title": title,
        "type": "3d",
        "size": size,
        "domain_min": domain_min,
        "domain_max": domain_max,
        "data": lut_3d,
    }


def _parse_1d(lines, start, size):
    data = []
    for line in lines[start:start + size]:
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                data.append([float(parts[0]), float(parts[1]), float(parts[2])])
            except ValueError:
                continue
    if len(data) != size:
        return None
    return {
        "title": "1D LUT",
        "type": "1d",
        "size": size,
        "data": data,
    }


def apply_lut(image, lut_data):
    if lut_data is None:
        return image
    image = image.convertToFormat(QImage.Format_ARGB32)
    w, h = image.width(), image.height()
    ptr = image.bits()
    if ptr is None:
        return image
    ptr.setsize(image.byteCount())
    arr = bytearray(ptr.asstring())

    if lut_data["type"] == "3d":
        size = lut_data["size"]
        data = lut_data["data"]
        domain_min = lut_data.get("domain_min", [0, 0, 0])
        domain_max = lut_data.get("domain_max", [1, 1, 1])
        domain_range = [domain_max[i] - domain_min[i] for i in range(3)]

        for i in range(0, len(arr), 4):
            b, g, r, a = arr[i], arr[i+1], arr[i+2], arr[i+3]
            nr = r / 255.0
            ng = g / 255.0
            nb = b / 255.0

            nr = max(0, min(1, (nr - domain_min[0]) / domain_range[0])) if domain_range[0] != 0 else nr
            ng = max(0, min(1, (ng - domain_min[1]) / domain_range[1])) if domain_range[1] != 0 else ng
            nb = max(0, min(1, (nb - domain_min[2]) / domain_range[2])) if domain_range[2] != 0 else nb

            ri = int(nr * (size - 1))
            gi = int(ng * (size - 1))
            bi = int(nb * (size - 1))
            ri = max(0, min(size - 1, ri))
            gi = max(0, min(size - 1, gi))
            bi = max(0, min(size - 1, bi))

            idx = (bi * size * size) + (gi * size) + ri
            if idx < len(data):
                arr[i] = max(0, min(255, int(data[idx][2] * 255)))
                arr[i+1] = max(0, min(255, int(data[idx][1] * 255)))
                arr[i+2] = max(0, min(255, int(data[idx][0] * 255)))

    elif lut_data["type"] == "1d":
        size = lut_data["size"]
        data = lut_data["data"]
        for i in range(0, len(arr), 4):
            b, g, r, a = arr[i], arr[i+1], arr[i+2], arr[i+3]
            ri = int((r / 255.0) * (size - 1))
            gi = int((g / 255.0) * (size - 1))
            bi = int((b / 255.0) * (size - 1))
            ri = max(0, min(size - 1, ri))
            gi = max(0, min(size - 1, gi))
            bi = max(0, min(size - 1, bi))
            arr[i] = max(0, min(255, int(data[bi][2] * 255))) if bi < len(data) else arr[i]
            arr[i+1] = max(0, min(255, int(data[gi][1] * 255))) if gi < len(data) else arr[i+1]
            arr[i+2] = max(0, min(255, int(data[ri][0] * 255))) if ri < len(data) else arr[i+2]

    return QImage(arr, w, h, image.bytesPerLine(), QImage.Format_ARGB32)


class LutPanel(QWidget):
    lutChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_lut = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        gb = QGroupBox(_("3D LUT"))
        gl = QVBoxLayout(gb)
        gl.setSpacing(4)

        gl.addWidget(QLabel(_("Load a .cube LUT file to apply color grading:")))

        btn_row = QHBoxLayout()
        load_btn = QPushButton(_("Load LUT..."))
        load_btn.clicked.connect(self._load_lut)
        self._clear_btn = QPushButton(_("Clear"))
        self._clear_btn.clicked.connect(self._clear_lut)
        self._clear_btn.setEnabled(False)
        btn_row.addWidget(load_btn)
        btn_row.addWidget(self._clear_btn)
        gl.addLayout(btn_row)

        self._lut_label = QLabel(_("No LUT loaded"))
        self._lut_label.setStyleSheet("color: #888; font-size: 11px;")
        gl.addWidget(self._lut_label)

        layout.addWidget(gb)
        layout.addStretch()

    def _load_lut(self):
        path, _filter = QFileDialog.getOpenFileName(
            self, _("Load LUT"), "", _("LUT Files (*.cube);;All Files (*)")
        )
        if path:
            lut_data = parse_cube_file(path)
            if lut_data is None:
                QMessageBox.warning(self, _("Error"), _("Could not parse LUT file: ") + os.path.basename(path))
                return
            self._current_lut = lut_data
            self._lut_label.setText(
                f"{lut_data['title']} ({lut_data['type'].upper()}, {lut_data['size']} pts)"
            )
            self._lut_label.setStyleSheet("color: #4f4; font-size: 11px;")
            self._clear_btn.setEnabled(True)
            self.lutChanged.emit(self._current_lut)

    def _clear_lut(self):
        self._current_lut = None
        self._lut_label.setText(_("No LUT loaded"))
        self._lut_label.setStyleSheet("color: #888; font-size: 11px;")
        self._clear_btn.setEnabled(False)
        self.lutChanged.emit(None)

    def current_lut(self):
        return self._current_lut
