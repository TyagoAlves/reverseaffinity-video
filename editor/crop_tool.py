from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QSpinBox, QGroupBox, QGridLayout
from PyQt5.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from editor.i18n import _


HANDLE_SIZE = 10
MIN_CROP = 20


class CropOverlay(QWidget):
    cropChanged = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self._crop_rect = QRect(40, 40, 200, 150)
        self._dragging = None
        self._drag_start = None
        self._crop_start = None

    def set_crop(self, rect):
        self._crop_rect = rect
        self.update()

    def crop_rect(self):
        return QRect(self._crop_rect)

    def _handle_rects(self):
        r = self._crop_rect
        h = HANDLE_SIZE
        return {
            "tl": QRect(r.left() - h//2, r.top() - h//2, h, h),
            "tr": QRect(r.right() - h//2, r.top() - h//2, h, h),
            "bl": QRect(r.left() - h//2, r.bottom() - h//2, h, h),
            "br": QRect(r.right() - h//2, r.bottom() - h//2, h, h),
            "tm": QRect(r.left() + r.width()//2 - h//2, r.top() - h//2, h, h),
            "bm": QRect(r.left() + r.width()//2 - h//2, r.bottom() - h//2, h, h),
            "ml": QRect(r.left() - h//2, r.top() + r.height()//2 - h//2, h, h),
            "mr": QRect(r.right() - h//2, r.top() + r.height()//2 - h//2, h, h),
        }

    def _handle_at(self, pos):
        for name, hr in self._handle_rects().items():
            if hr.contains(pos):
                return name
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            h = self._handle_at(event.pos())
            if h:
                self._dragging = h
                self._drag_start = event.pos()
                self._crop_start = QRect(self._crop_rect)
            elif self._crop_rect.contains(event.pos()):
                self._dragging = "move"
                self._drag_start = event.pos()
                self._crop_start = QRect(self._crop_rect)

    def mouseMoveEvent(self, event):
        if not self._dragging or not self._drag_start:
            cursor = Qt.ArrowCursor
            h = self._handle_at(event.pos())
            if h in ("tl", "br"):
                cursor = Qt.SizeFDiagCursor
            elif h in ("tr", "bl"):
                cursor = Qt.SizeBDiagCursor
            elif h in ("tm", "bm"):
                cursor = Qt.SizeVerCursor
            elif h in ("ml", "mr"):
                cursor = Qt.SizeHorCursor
            elif self._crop_rect.contains(event.pos()):
                cursor = Qt.SizeAllCursor
            self.setCursor(cursor)
            return

        delta = event.pos() - self._drag_start
        r = QRect(self._crop_start)
        w, h = self.width(), self.height()

        if self._dragging == "move":
            r.translate(delta)
        elif self._dragging == "tl":
            r.setLeft(r.left() + delta.x())
            r.setTop(r.top() + delta.y())
        elif self._dragging == "tr":
            r.setRight(r.right() + delta.x())
            r.setTop(r.top() + delta.y())
        elif self._dragging == "bl":
            r.setLeft(r.left() + delta.x())
            r.setBottom(r.bottom() + delta.y())
        elif self._dragging == "br":
            r.setRight(r.right() + delta.x())
            r.setBottom(r.bottom() + delta.y())
        elif self._dragging == "tm":
            r.setTop(r.top() + delta.y())
        elif self._dragging == "bm":
            r.setBottom(r.bottom() + delta.y())
        elif self._dragging == "ml":
            r.setLeft(r.left() + delta.x())
        elif self._dragging == "mr":
            r.setRight(r.right() + delta.x())

        r.setLeft(max(0, r.left()))
        r.setTop(max(0, r.top()))
        r.setRight(min(w, r.right()))
        r.setBottom(min(h, r.bottom()))

        if r.width() >= MIN_CROP and r.height() >= MIN_CROP:
            self._crop_rect = r
            self.update()
            self.cropChanged.emit(self._crop_rect)

    def mouseReleaseEvent(self, event):
        self._dragging = None
        self._drag_start = None
        self._crop_start = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = self._crop_rect

        overlay = QColor(0, 0, 0, 120)
        p.fillRect(0, 0, w, r.top(), overlay)
        p.fillRect(0, r.bottom(), w, h - r.bottom(), overlay)
        p.fillRect(0, r.top(), r.left(), r.height(), overlay)
        p.fillRect(r.right(), r.top(), w - r.right(), r.height(), overlay)

        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(r)

        for hr in self._handle_rects().values():
            p.fillRect(hr, QColor(255, 255, 255))
            p.setPen(QPen(QColor(0, 0, 0), 1))
            p.drawRect(hr)

        rule_text = _("Drag handles to crop | Right-click to reset")
        p.setPen(QColor(200, 200, 200))
        p.drawText(10, h - 10, rule_text)


class CropControlPanel(QWidget):
    cropApplied = pyqtSignal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel(_("Crop"))
        tf = QFont()
        tf.setBold(True)
        tf.setPointSize(11)
        title.setFont(tf)
        layout.addWidget(title)

        form = QGridLayout()
        form.setSpacing(4)

        self._left_sb = QSpinBox()
        self._top_sb = QSpinBox()
        self._right_sb = QSpinBox()
        self._bottom_sb = QSpinBox()
        for sb in (self._left_sb, self._top_sb, self._right_sb, self._bottom_sb):
            sb.setRange(0, 10000)
            sb.setSuffix(" px")
            sb.valueChanged.connect(self._on_value_changed)

        form.addWidget(QLabel(_("Left:")), 0, 0)
        form.addWidget(self._left_sb, 0, 1)
        form.addWidget(QLabel(_("Top:")), 0, 2)
        form.addWidget(self._top_sb, 0, 3)
        form.addWidget(QLabel(_("Right:")), 1, 0)
        form.addWidget(self._right_sb, 1, 1)
        form.addWidget(QLabel(_("Bottom:")), 1, 2)
        form.addWidget(self._bottom_sb, 1, 3)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        reset_btn = QPushButton(_("Reset"))
        reset_btn.clicked.connect(self._reset)
        apply_btn = QPushButton(_("Apply Crop"))
        apply_btn.clicked.connect(self._apply)
        btn_row.addStretch()
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

    def update_from_rect(self, rect, parent_w, parent_h):
        self._left_sb.blockSignals(True)
        self._top_sb.blockSignals(True)
        self._right_sb.blockSignals(True)
        self._bottom_sb.blockSignals(True)
        self._left_sb.setValue(rect.left())
        self._top_sb.setValue(rect.top())
        self._right_sb.setValue(parent_w - rect.right())
        self._bottom_sb.setValue(parent_h - rect.bottom())
        self._left_sb.blockSignals(False)
        self._top_sb.blockSignals(False)
        self._right_sb.blockSignals(False)
        self._bottom_sb.blockSignals(False)

    def _on_value_changed(self):
        l = self._left_sb.value()
        t = self._top_sb.value()
        r = self._right_sb.value()
        b = self._bottom_sb.value()
        self.cropApplied.emit(l, t, r, b)

    def _reset(self):
        self._left_sb.setValue(0)
        self._top_sb.setValue(0)
        self._right_sb.setValue(0)
        self._bottom_sb.setValue(0)

    def _apply(self):
        self._on_value_changed()
