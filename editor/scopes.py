import math
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import (
    QPainter, QColor, QPixmap, QImage, QPen, QBrush, QFont,
)
from editor.i18n import _


class WaveformScope(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 100)
        self._image = None

    def set_image(self, image):
        if image and not image.isNull():
            self._image = image.convertToFormat(QImage.Format_ARGB32)
        else:
            self._image = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor(20, 20, 20))
        p.setPen(QColor(60, 60, 60))
        for i in range(0, 5):
            y = h * i / 4
            p.drawLine(0, int(y), w, int(y))
        for i in range(0, 5):
            x = w * i / 4
            p.drawLine(int(x), 0, int(x), h)

        p.setPen(QColor(40, 40, 40))
        p.drawText(w - 60, h - 4, _("Waveform"))

        if self._image is None or self._image.isNull():
            p.setPen(QColor(100, 100, 100))
            p.drawText(w // 2 - 40, h // 2, _("No signal"))
            return

        src_w, src_h = self._image.width(), self._image.height()
        if src_w == 0 or src_h == 0:
            return

        ptr = self._image.bits()
        ptr.setsize(self._image.byteCount())
        arr = bytearray(ptr.asstring())

        scope_data = [0.0] * w
        sample_count = [0] * w
        col_x = int(src_w / 4)
        for y_src in range(0, src_h, 4):
            for x_src in range(0, src_w, 4):
                i = (y_src * src_w + x_src) * 4
                if i + 3 >= len(arr):
                    continue
                b, g, r = arr[i], arr[i+1], arr[i+2]
                luma = 0.299 * r + 0.587 * g + 0.114 * b
                luma_norm = luma / 255.0
                col = x_src // col_x
                if col < w:
                    scope_data[col] += luma_norm
                    sample_count[col] += 1

        for x in range(w):
            if sample_count[x] > 0:
                avg = scope_data[x] / sample_count[x]
                y_pos = h - 1 - int(avg * (h - 4)) - 2
                p.setPen(QColor(144, 238, 144))
                p.drawPoint(x, y_pos)


class VectorscopeScope(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self._image = None
        self._scope_pixmap = None

    def set_image(self, image):
        if image and not image.isNull():
            self._image = image.convertToFormat(QImage.Format_ARGB32)
        else:
            self._image = None
        self._scope_pixmap = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 10

        p.fillRect(0, 0, w, h, QColor(20, 20, 20))

        p.setPen(QColor(60, 60, 60))
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        p.drawEllipse(int(cx - r/2), int(cy - r/2), int(r), int(r))
        p.drawLine(int(cx - r), int(cy), int(cx + r), int(cy))
        p.drawLine(int(cx), int(cy - r), int(cx), int(cy + r))

        color_labels = [(0, "R"), (60, "Y"), (120, "G"), (180, "C"), (240, "B"), (300, "M")]
        for angle, label in color_labels:
            rad = math.radians(angle - 90)
            lx = cx + (r + 10) * math.cos(rad)
            ly = cy + (r + 10) * math.sin(rad)
            p.setPen(QColor(120, 120, 120))
            p.drawText(int(lx - 5), int(ly + 4), label)

        if self._image is None or self._image.isNull():
            p.setPen(QColor(100, 100, 100))
            p.drawText(int(cx - 30), int(cy), _("No signal"))
            return

        src_w, src_h = self._image.width(), self._image.height()
        if src_w == 0 or src_h == 0:
            return

        ptr = self._image.bits()
        ptr.setsize(self._image.byteCount())
        arr = bytearray(ptr.asstring())

        p.setPen(QColor(144, 238, 144, 80))
        points_drawn = 0
        step = max(1, (src_w * src_h) // 2000)
        pixel_i = 0
        for y_src in range(0, src_h, 3):
            for x_src in range(0, src_w, 3):
                pixel_i += 1
                if pixel_i % step != 0:
                    continue
                i = (y_src * src_w + x_src) * 4
                if i + 3 >= len(arr):
                    continue
                b, g, r, a = arr[i], arr[i+1], arr[i+2], arr[i+3]
                if a < 128:
                    continue
                nr = r / 255.0
                ng = g / 255.0
                nb = b / 255.0

                u = -0.1687 * nr - 0.3313 * ng + 0.5 * nb
                v = 0.5 * nr - 0.4187 * ng - 0.0813 * nb

                px = cx + u * r * 1.4
                py = cy - v * r * 1.4
                p.drawPoint(int(px), int(py))
                points_drawn += 1


class ScopesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        self.waveform = WaveformScope()
        self.vectorscope = VectorscopeScope()
        tabs.addTab(self.waveform, _("Waveform"))
        tabs.addTab(self.vectorscope, _("Vectorscope"))
        layout.addWidget(tabs)

    def set_image(self, image):
        self.waveform.set_image(image)
        self.vectorscope.set_image(image)
