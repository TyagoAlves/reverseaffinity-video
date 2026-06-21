"""
Gradient editor widget with interactive gradient bar, stop editing, and presets.
"""

import os
import json

from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QMouseEvent,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QPushButton, QColorDialog, QListWidget, QListWidgetItem,
    QMenu, QAction, QInputDialog, QSizePolicy,
)

from .gradient import Gradient, GradientStop, DEFAULT_PRESETS

PRESETS_PATH = os.path.join(os.path.dirname(__file__), "..", "presets", "gradients.json")


class GradientBar(QWidget):
    gradientChanged = pyqtSignal()

    STOP_SIZE = 10
    BAR_HEIGHT = 24
    MARKER_AREA = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gradient = Gradient("linear")
        self.gradient.add_stop(0.0, QColor(0, 0, 0))
        self.gradient.add_stop(1.0, QColor(255, 255, 255))
        self.selected_stop = 0
        self._dragging = False
        self._drag_index = -1
        self._context_stop = -1
        self.setMouseTracking(True)
        self.setMinimumHeight(self.BAR_HEIGHT + self.MARKER_AREA + 6)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def bar_rect(self):
        m = self.MARKER_AREA // 2
        return QRectF(m, self.MARKER_AREA, self.width() - self.MARKER_AREA, self.BAR_HEIGHT)

    def pos_to_stop_x(self, pos):
        br = self.bar_rect()
        clamped = max(0.0, min(1.0, (pos.x() - br.x()) / br.width()))
        return br.x() + clamped * br.width()

    def pos_to_stop_pos(self, pos):
        br = self.bar_rect()
        return max(0.0, min(1.0, (pos.x() - br.x()) / br.width()))

    def stop_x_pos(self, stop):
        br = self.bar_rect()
        return br.x() + stop.position * br.width()

    def hit_test_stop(self, pos):
        for i, stop in enumerate(self.gradient.stops):
            sx = self.stop_x_pos(stop)
            if abs(pos.x() - sx) < self.STOP_SIZE and \
               self.MARKER_AREA - 4 <= pos.y() <= self.MARKER_AREA + self.BAR_HEIGHT + 4:
                return i
        return -1

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        br = self.bar_rect()

        g = self.gradient.to_qgradient(
            QPointF(br.left(), br.top()),
            QPointF(br.right(), br.top()),
        )
        p.fillRect(br, QBrush(g))

        p.setPen(QPen(QColor(80, 80, 80), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(br)

        for i, stop in enumerate(self.gradient.stops):
            sx = self.stop_x_pos(stop)
            is_selected = (i == self.selected_stop)
            color = stop.color

            w = self.STOP_SIZE
            h = self.STOP_SIZE
            x = sx - w / 2
            y = br.top() - h - 2

            p.setPen(QPen(Qt.white if is_selected else QColor(60, 60, 60), 1.5 if is_selected else 1))
            p.setBrush(QBrush(color))
            p.drawRect(QRectF(x, y, w, h))

            p.setPen(QPen(Qt.white if is_selected else QColor(100, 100, 100), 1))
            p.drawLine(int(sx), int(br.bottom()), int(sx), int(br.bottom() + 4))

        if self.gradient.stops:
            sel = self.gradient.stops[self.selected_stop]
            sx = self.stop_x_pos(sel)
            p.setPen(QPen(QColor(200, 200, 200), 1))
            p.drawText(int(sx - 30), int(self.height() - 2), 60, 14,
                       Qt.AlignCenter, f"{sel.position:.2f}")

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        idx = self.hit_test_stop(event.pos())
        if idx >= 0:
            self.selected_stop = idx
            self._dragging = True
            self._drag_index = idx
            self.gradientChanged.emit()
            self.update()
        else:
            br = self.bar_rect()
            if br.contains(event.pos()):
                pos = self.pos_to_stop_pos(event.pos())
                color = QColor(128, 128, 128)
                self.gradient.add_stop(pos, color)
                self.selected_stop = len(self.gradient.stops) - 1
                self.gradientChanged.emit()
                self.update()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_index >= 0:
            pos = self.pos_to_stop_pos(event.pos())
            self.gradient.stops[self._drag_index].position = max(0.0, min(1.0, pos))
            self.gradient.sort_stops()
            new_idx = self.gradient.stops.index(self.gradient.stops[self._drag_index])
            self.selected_stop = new_idx
            self.gradientChanged.emit()
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._drag_index = -1

    def mouseDoubleClickEvent(self, event):
        idx = self.hit_test_stop(event.pos())
        if idx >= 0:
            stop = self.gradient.stops[idx]
            c = QColorDialog.getColor(stop.color, self, "Choose Stop Color")
            if c.isValid():
                self.gradient.stops[idx].color = c
                self.gradientChanged.emit()
                self.update()

    def contextMenuEvent(self, event):
        idx = self.hit_test_stop(event.pos())
        if idx < 0:
            return
        menu = QMenu(self)
        del_action = QAction("Delete Stop", self)
        del_action.triggered.connect(lambda: self._delete_stop(idx))
        menu.addAction(del_action)
        if idx > 0:
            menu.addSeparator()
            edit_action = QAction("Edit Color...", self)
            edit_action.triggered.connect(lambda: self._edit_stop(idx))
            menu.addAction(edit_action)
        menu.exec_(event.globalPos())

    def _delete_stop(self, idx):
        if len(self.gradient.stops) <= 1:
            return
        self.gradient.remove_stop(idx)
        if self.selected_stop >= len(self.gradient.stops):
            self.selected_stop = len(self.gradient.stops) - 1
        self.gradientChanged.emit()
        self.update()

    def _edit_stop(self, idx):
        stop = self.gradient.stops[idx]
        c = QColorDialog.getColor(stop.color, self, "Edit Stop Color")
        if c.isValid():
            self.gradient.stops[idx].color = c
            self.gradientChanged.emit()
            self.update()

    def set_gradient(self, gradient):
        self.gradient = gradient
        if self.selected_stop >= len(self.gradient.stops):
            self.selected_stop = len(self.gradient.stops) - 1 if self.gradient.stops else 0
        self.gradientChanged.emit()
        self.update()

    def get_gradient(self):
        return self.gradient


class GradientEditorWidget(QWidget):
    gradientChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Linear", "Radial", "Conical", "Diamond"])
        self.type_combo.currentTextChanged.connect(self._type_changed)
        type_row.addWidget(self.type_combo)

        type_row.addWidget(QLabel("Repeat:"))
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(["None", "Repeat", "Reflect"])
        self.repeat_combo.currentTextChanged.connect(self._repeat_changed)
        type_row.addWidget(self.repeat_combo)
        layout.addLayout(type_row)

        self.bar = GradientBar()
        self.bar.gradientChanged.connect(self._on_bar_changed)
        layout.addWidget(self.bar)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Stop")
        self.add_btn.clicked.connect(self._add_stop)
        btn_row.addWidget(self.add_btn)

        self.del_btn = QPushButton("Delete Stop")
        self.del_btn.clicked.connect(self._del_stop)
        btn_row.addWidget(self.del_btn)

        self.color_btn = QPushButton("Stop Color")
        self.color_btn.clicked.connect(self._edit_color)
        btn_row.addWidget(self.color_btn)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Presets:"))
        self.preset_list = QListWidget()
        self.preset_list.setMaximumHeight(120)
        self.preset_list.itemDoubleClicked.connect(self._load_preset)
        layout.addWidget(self.preset_list)

        preset_btn_row = QHBoxLayout()
        self.save_preset_btn = QPushButton("Add to Presets")
        self.save_preset_btn.clicked.connect(self._save_preset)
        preset_btn_row.addWidget(self.save_preset_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._reset_gradient)
        preset_btn_row.addWidget(self.reset_btn)
        layout.addLayout(preset_btn_row)

        self._load_presets_list()

    def set_gradient(self, gradient):
        self.bar.set_gradient(gradient)
        type_map = {"linear": 0, "radial": 1, "conical": 2, "diamond": 3}
        self.type_combo.setCurrentIndex(type_map.get(gradient.type, 0))
        repeat_map = {"none": 0, "repeat": 1, "reflect": 2}
        self.repeat_combo.setCurrentIndex(repeat_map.get(gradient.repeat, 0))

    def get_gradient(self):
        return self.bar.get_gradient()

    def _type_changed(self, text):
        type_map = {"Linear": "linear", "Radial": "radial", "Conical": "conical", "Diamond": "diamond"}
        self.bar.gradient.type = type_map.get(text, "linear")
        self.bar.update()
        self.gradientChanged.emit()

    def _repeat_changed(self, text):
        repeat_map = {"None": "none", "Repeat": "repeat", "Reflect": "reflect"}
        self.bar.gradient.repeat = repeat_map.get(text, "none")
        self.bar.update()
        self.gradientChanged.emit()

    def _on_bar_changed(self):
        self.gradientChanged.emit()

    def _add_stop(self):
        pos = 0.5
        color = QColor(128, 128, 128)
        self.bar.gradient.add_stop(pos, color)
        self.bar.selected_stop = len(self.bar.gradient.stops) - 1
        self.bar.update()
        self.gradientChanged.emit()

    def _del_stop(self):
        if len(self.bar.gradient.stops) <= 1:
            return
        idx = self.bar.selected_stop
        self.bar._delete_stop(idx)

    def _edit_color(self):
        if not self.bar.gradient.stops:
            return
        idx = self.bar.selected_stop
        stop = self.bar.gradient.stops[idx]
        c = QColorDialog.getColor(stop.color, self, "Edit Stop Color")
        if c.isValid():
            self.bar.gradient.stops[idx].color = c
            self.bar.update()
            self.gradientChanged.emit()

    def _load_preset(self, item):
        data = item.data(Qt.UserRole)
        if data:
            g = Gradient.from_dict(data)
            self.set_gradient(g)
            self.gradientChanged.emit()

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset Name:")
        if not ok or not name.strip():
            return
        data = self.bar.gradient.to_dict()
        entry = {"name": name.strip(), "gradient": data}
        presets = self._load_user_presets()
        presets.append(entry)
        os.makedirs(os.path.dirname(PRESETS_PATH), exist_ok=True)
        with open(PRESETS_PATH, "w") as f:
            json.dump(presets, f, indent=2)
        self._load_presets_list()

    def _reset_gradient(self):
        g = Gradient("linear")
        g.add_stop(0.0, QColor(0, 0, 0))
        g.add_stop(1.0, QColor(255, 255, 255))
        self.set_gradient(g)
        self.gradientChanged.emit()

    def _load_presets_list(self):
        self.preset_list.blockSignals(True)
        self.preset_list.clear()
        for preset in DEFAULT_PRESETS:
            item = QListWidgetItem(preset["name"])
            item.setData(Qt.UserRole, preset["gradient"])
            self.preset_list.addItem(item)
        user_presets = self._load_user_presets()
        for preset in user_presets:
            item = QListWidgetItem(preset["name"])
            item.setData(Qt.UserRole, preset["gradient"])
            self.preset_list.addItem(item)
        self.preset_list.blockSignals(False)

    def _load_user_presets(self):
        try:
            if os.path.exists(PRESETS_PATH):
                with open(PRESETS_PATH, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return []



