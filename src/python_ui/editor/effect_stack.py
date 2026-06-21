from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QScrollArea, QFrame,
    QGroupBox, QComboBox, QSlider, QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QColor
from editor.i18n import _
from editor.filters import gaussian_blur, sharpen


class EffectItem:
    def __init__(self, name, effect_type, params=None, enabled=True):
        self.name = name
        self.effect_type = effect_type
        self.params = params or {}
        self.enabled = enabled

    def apply(self, image):
        if not self.enabled:
            return image
        et = self.effect_type
        if et == "gaussian_blur":
            return gaussian_blur(image, self.params.get("radius", 3))
        elif et == "sharpen":
            return sharpen(image, self.params.get("amount", 3))
        elif et == "grayscale":
            return self._grayscale(image)
        elif et == "invert":
            return self._invert(image)
        elif et == "brightness":
            return self._adjust_brightness(image, self.params.get("value", 0))
        elif et == "contrast":
            return self._adjust_contrast(image, self.params.get("value", 0))
        return image

    @staticmethod
    def _grayscale(image):
        if image.isNull():
            return image
        from PyQt5.QtGui import QPainter
        result = image.convertToFormat(QImage.Format_Grayscale8)
        return result.convertToFormat(QImage.Format_RGB32)

    @staticmethod
    def _invert(image):
        if image.isNull():
            return image
        result = image.copy()
        result.invertPixels()
        return result

    @staticmethod
    def _adjust_brightness(image, value):
        if image.isNull():
            return image
        import numpy as np
        w, h = image.width(), image.height()
        ptr = image.constBits()
        ptr.setsize(h * w * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape(h, w, 4).copy()
        arr = np.clip(arr.astype(np.int16) + value, 0, 255).astype(np.uint8)
        from PyQt5.QtGui import QImage
        return QImage(arr.data, w, h, w * 4, QImage.Format_RGBA8888)

    @staticmethod
    def _adjust_contrast(image, value):
        if image.isNull():
            return image
        import numpy as np
        w, h = image.width(), image.height()
        ptr = image.constBits()
        ptr.setsize(h * w * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape(h, w, 4).copy()
        factor = (259 * (value + 255)) / (255 * (259 - value))
        arr = np.clip(factor * (arr.astype(np.float32) - 128) + 128, 0, 255).astype(np.uint8)
        from PyQt5.QtGui import QImage
        return QImage(arr.data, w, h, w * 4, QImage.Format_RGBA8888)


class EffectStack:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    def remove(self, index):
        if 0 <= index < len(self.items):
            del self.items[index]

    def move_up(self, index):
        if 0 < index < len(self.items):
            self.items[index], self.items[index - 1] = self.items[index - 1], self.items[index]

    def move_down(self, index):
        if 0 <= index < len(self.items) - 1:
            self.items[index], self.items[index + 1] = self.items[index + 1], self.items[index]

    def apply(self, image):
        for item in self.items:
            image = item.apply(image)
        return image

    def count(self):
        return len(self.items)

    def clear(self):
        self.items.clear()


EFFECT_TYPES = [
    ("Gaussian Blur", "gaussian_blur", {"radius": 3}),
    ("Sharpen", "sharpen", {"amount": 3}),
    ("Grayscale", "grayscale", {}),
    ("Invert", "invert", {}),
    ("Brightness", "brightness", {"value": 30}),
    ("Contrast", "contrast", {"value": 30}),
]


class EffectStackWidget(QWidget):
    stackChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stack = EffectStack()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel(_("Effect Stack"))
        tf = title.font()
        tf.setBold(True)
        tf.setPointSize(10)
        title.setFont(tf)
        layout.addWidget(title)

        add_row = QHBoxLayout()
        self._add_combo = QComboBox()
        for name, etype, _ in EFFECT_TYPES:
            self._add_combo.addItem(_(name), etype)
        self._add_btn = QPushButton(_("+"))
        self._add_btn.setFixedWidth(28)
        self._add_btn.clicked.connect(self._add_effect)
        add_row.addWidget(self._add_combo, 1)
        add_row.addWidget(self._add_btn)
        layout.addLayout(add_row)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        self._up_btn = QPushButton(_("\u25B2"))
        self._up_btn.setFixedWidth(28)
        self._up_btn.clicked.connect(self._move_up)
        self._down_btn = QPushButton(_("\u25BC"))
        self._down_btn.setFixedWidth(28)
        self._down_btn.clicked.connect(self._move_down)
        self._toggle_btn = QPushButton(_("Toggle"))
        self._toggle_btn.clicked.connect(self._toggle_selected)
        self._del_btn = QPushButton(_("Del"))
        self._del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(self._up_btn)
        btn_row.addWidget(self._down_btn)
        btn_row.addWidget(self._toggle_btn)
        btn_row.addWidget(self._del_btn)
        layout.addLayout(btn_row)

        self._selected_index = -1

    def set_stack(self, stack):
        self._stack = stack
        self._rebuild_list()

    def stack(self):
        return self._stack

    def _rebuild_list(self):
        self._list.clear()
        for i, item in enumerate(self._stack.items):
            icon = "\u25C9" if item.enabled else "\u25CB"
            txt = f"{icon} {item.name}"
            li = QListWidgetItem(txt)
            li.setData(Qt.UserRole, i)
            if not item.enabled:
                li.setForeground(QColor("#666"))
            self._list.addItem(li)
        self._selected_index = -1

    def _add_effect(self):
        etype = self._add_combo.currentData()
        name = self._add_combo.currentText()
        params = {}
        for n, et, p in EFFECT_TYPES:
            if et == etype:
                params = dict(p)
                break
        item = EffectItem(name, etype, params, True)
        self._stack.add(item)
        self._rebuild_list()
        self.stackChanged.emit()

    def _on_item_clicked(self, item):
        self._selected_index = item.data(Qt.UserRole)

    def _move_up(self):
        if self._selected_index > 0:
            self._stack.move_up(self._selected_index)
            self._selected_index -= 1
            self._rebuild_list()
            self.stackChanged.emit()

    def _move_down(self):
        if 0 <= self._selected_index < self._stack.count() - 1:
            self._stack.move_down(self._selected_index)
            self._selected_index += 1
            self._rebuild_list()
            self.stackChanged.emit()

    def _toggle_selected(self):
        if 0 <= self._selected_index < self._stack.count():
            self._stack.items[self._selected_index].enabled = not self._stack.items[self._selected_index].enabled
            self._rebuild_list()
            self.stackChanged.emit()

    def _delete_selected(self):
        if 0 <= self._selected_index < self._stack.count():
            self._stack.remove(self._selected_index)
            self._selected_index = -1
            self._rebuild_list()
            self.stackChanged.emit()

    def apply_to_image(self, image):
        return self._stack.apply(image)
