from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPalette
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSlider, QFrame, QSizePolicy,
)


_BTN_STYLE = """
QPushButton {
    background-color: #1a1a2e;
    color: #ffffff;
    border: 1px solid #2a2a3e;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    padding: 0px;
}
QPushButton:hover {
    background-color: #2a2a3e;
    border-color: #3a3a5e;
}
QPushButton:pressed {
    background-color: #3a3a5e;
}
"""

_PLAY_STYLE = """
QPushButton {
    background-color: #f97316;
    color: #ffffff;
    border: 1px solid #f97316;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    padding: 0px;
}
QPushButton:hover {
    background-color: #fb923c;
    border-color: #fb923c;
}
QPushButton:pressed {
    background-color: #ea580c;
}
"""

_TOGGLE_ON_STYLE = """
QPushButton {
    background-color: #2a5a8a;
    color: #ffffff;
    border: 1px solid #3a7aba;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    padding: 0px;
}
QPushButton:hover {
    background-color: #3a7aba;
}
"""


class TransportButton(QPushButton):
    def __init__(self, text, shortcut="", parent=None):
        super().__init__(text, parent)
        self.setFixedSize(32, 32)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(_BTN_STYLE)
        if shortcut:
            self.setToolTip(f"{text} ({shortcut})")
        else:
            self.setToolTip(text)


class TimecodeDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_time = 0.0
        self._duration = 0.0
        font = QFont("Consolas, Courier New, monospace")
        font.setPixelSize(14)
        font.setBold(True)
        self._font = font
        self.setFixedHeight(32)
        self.setMinimumWidth(200)

    def _frames_to_timecode(self, seconds, fps=30.0):
        if seconds < 0:
            seconds = 0
        total_frames = int(round(seconds * fps))
        h = int(total_frames // (3600 * fps))
        m = int((total_frames // (60 * fps)) % 60)
        s = int((total_frames // fps) % 60)
        f = int(total_frames % fps)
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

    def set_time(self, seconds):
        self._current_time = seconds
        self.update()

    def set_duration(self, seconds):
        self._duration = seconds
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0e0e1a"))
        current_str = self._frames_to_timecode(self._current_time)
        duration_str = self._frames_to_timecode(self._duration)
        text = f"{current_str} / {duration_str}"
        painter.setFont(self._font)
        painter.setPen(QColor("#00ff88"))
        painter.drawText(self.rect(), Qt.AlignCenter, text)


class TransportBar(QWidget):
    playToggled = pyqtSignal(bool)
    stopTriggered = pyqtSignal()
    stepForward = pyqtSignal()
    stepBackward = pyqtSignal()
    goToStart = pyqtSignal()
    goToEnd = pyqtSignal()
    zoomChanged = pyqtSignal(float)
    snapToggled = pyqtSignal(bool)
    loopToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playing = False
        self._snap = True
        self._loop = False
        self._zoom_scale = 1.0
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(44)
        self.setStyleSheet("background-color: #0e0e1a;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        self._build_transport_buttons(layout)
        self._build_timecode(layout)
        layout.addStretch(1)
        self._build_timeline_controls(layout)

    def _build_transport_buttons(self, layout):
        self._btn_start = TransportButton("\u23ee")
        self._btn_start.clicked.connect(self._on_go_to_start)
        layout.addWidget(self._btn_start)

        self._btn_prev = TransportButton("\u25c0\u25c0")
        self._btn_prev.clicked.connect(self.stepBackward.emit)
        layout.addWidget(self._btn_prev)

        self._btn_play = TransportButton("\u25b6")
        self._btn_play.clicked.connect(self._on_play_toggle)
        layout.addWidget(self._btn_play)

        self._btn_stop = TransportButton("\u23f9")
        self._btn_stop.clicked.connect(self._on_stop)
        layout.addWidget(self._btn_stop)

        self._btn_next = TransportButton("\u25b6\u25b6")
        self._btn_next.clicked.connect(self.stepForward.emit)
        layout.addWidget(self._btn_next)

        self._btn_end = TransportButton("\u23ed")
        self._btn_end.clicked.connect(self._on_go_to_end)
        layout.addWidget(self._btn_end)

    def _build_timecode(self, layout):
        self._timecode = TimecodeDisplay()
        layout.addWidget(self._timecode)

    def _build_timeline_controls(self, layout):
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(10, 500)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.setFixedHeight(20)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self._zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2a2a3e;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00ff88;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #00ff88;
                height: 4px;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self._zoom_slider)

        self._btn_snap = TransportButton("\u2699")
        self._btn_snap.setStyleSheet(_TOGGLE_ON_STYLE)
        self._btn_snap.clicked.connect(self._on_snap_toggle)
        layout.addWidget(self._btn_snap)

        self._btn_loop = TransportButton("\u21bb")
        self._btn_loop.clicked.connect(self._on_loop_toggle)
        layout.addWidget(self._btn_loop)

    def _on_play_toggle(self):
        self._playing = not self._playing
        if self._playing:
            self._btn_play.setText("\u23f8")
            self._btn_play.setStyleSheet(_PLAY_STYLE)
        else:
            self._btn_play.setText("\u25b6")
            self._btn_play.setStyleSheet(_BTN_STYLE)
        self.playToggled.emit(self._playing)

    def _on_stop(self):
        self._playing = False
        self._btn_play.setText("\u25b6")
        self._btn_play.setStyleSheet(_BTN_STYLE)
        self.stopTriggered.emit()

    def _on_go_to_start(self):
        self.goToStart.emit()

    def _on_go_to_end(self):
        self.goToEnd.emit()

    def _on_zoom_changed(self, value):
        self._zoom_scale = value / 100.0
        self.zoomChanged.emit(self._zoom_scale)

    def _on_snap_toggle(self):
        self._snap = not self._snap
        if self._snap:
            self._btn_snap.setStyleSheet(_TOGGLE_ON_STYLE)
        else:
            self._btn_snap.setStyleSheet(_BTN_STYLE)
        self.snapToggled.emit(self._snap)

    def _on_loop_toggle(self):
        self._loop = not self._loop
        if self._loop:
            self._btn_loop.setStyleSheet(_TOGGLE_ON_STYLE)
        else:
            self._btn_loop.setStyleSheet(_BTN_STYLE)
        self.loopToggled.emit(self._loop)

    def set_playing(self, playing):
        self._playing = playing
        if self._playing:
            self._btn_play.setText("\u23f8")
            self._btn_play.setStyleSheet(_PLAY_STYLE)
        else:
            self._btn_play.setText("\u25b6")
            self._btn_play.setStyleSheet(_BTN_STYLE)

    def set_current_time(self, seconds):
        self._timecode.set_time(seconds)

    def set_duration(self, seconds):
        self._timecode.set_duration(seconds)

    def set_zoom(self, scale):
        self._zoom_scale = scale
        value = max(10, min(500, int(scale * 100)))
        self._zoom_slider.setValue(value)
