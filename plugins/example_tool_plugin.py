from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from plugins import PluginBase
import numpy as np


class StarryTool:
    name = "Starry Sky Tool"
    shortcut = "Y"
    cursor_shape = Qt.CrossCursor
    _cursor = None

    @property
    def cursor(self):
        if self._cursor is None and self.cursor_shape is not None:
            from PyQt5.QtGui import QCursor
            self._cursor = QCursor(self.cursor_shape)
        return self._cursor

    def press(self, canvas, pos, mods):
        layer = canvas.layer_stack.active
        if not layer or layer.locked:
            return
        import random
        w, h = layer.image.width(), layer.image.height()
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        star_count = random.randint(20, 50)
        for _ in range(star_count):
            x = random.randint(0, w - 1)
            y = random.randint(0, h - 1)
            r = random.uniform(0.5, 2.5)
            brightness = random.randint(128, 255)
            p.setPen(QPen(QColor(brightness, brightness, brightness), 0))
            p.setBrush(QBrush(QColor(brightness, brightness, brightness)))
            p.drawEllipse(x, y, r, r)
        p.end()
        canvas._save_state("Starry Sky")
        canvas._refresh()

    def move(self, canvas, last, pos, mods):
        pass

    def release(self, canvas, pos, mods):
        pass


class StarryPanel(QWidget):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Starry Sky Generator"))
        btn = QPushButton("Generate Stars")
        btn.clicked.connect(self._generate)
        layout.addWidget(btn)

    def _generate(self):
        tool = StarryTool()
        tool.press(self.canvas, None, None)


class ToolPlugin(PluginBase):
    name = "Starry Sky Plugin"
    author = "reverseaffinity"
    version = "1.0"
    description = "Adds Starry Sky tool and panel"

    def register_tools(self):
        return [StarryTool]

    def register_panels(self, tab_widget):
        panel = StarryPanel(tab_widget.canvas if hasattr(tab_widget, 'canvas') else None)
        tab_widget.addTab(panel, "Starry")

    def register_filters(self):
        def warm_filter(image, *args):
            arr = np.array(image)
            if arr.ndim == 3 and arr.shape[2] >= 3:
                arr[:, :, 0] = np.clip(arr[:, :, 0].astype(np.int32) + 30, 0, 255).astype(np.uint8)
                arr[:, :, 2] = np.clip(arr[:, :, 2].astype(np.int32) - 20, 0, 255).astype(np.uint8)
            from PyQt5.QtGui import QImage
            h, w = arr.shape[:2]
            return QImage(arr.data, w, h, arr.strides[0], QImage.Format_RGBA8888).copy()

        return [("Warm Filter", warm_filter)]

    def on_load(self, ctx):
        print(f"[Plugin] {self.name} loaded")
