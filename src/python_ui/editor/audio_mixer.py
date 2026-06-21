from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QScrollArea, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QLinearGradient, QPen, QBrush
from editor.i18n import _


class PeakMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(16)
        self.setMinimumHeight(80)
        self._level = 0.0

    def set_level(self, level):
        self._level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(20, 20, 20))

        bar_h = int(h * self._level)
        green_h = int(h * 0.7)
        yellow_h = int(h * 0.85)

        if bar_h > 0:
            if bar_h <= green_h:
                p.fillRect(1, h - bar_h, w - 2, bar_h, QColor(0, 200, 0))
            elif bar_h <= yellow_h:
                p.fillRect(1, h - bar_h, w - 2, bar_h, QColor(0, 200, 0))
                p.fillRect(1, h - yellow_h, w - 2, bar_h - green_h, QColor(255, 200, 0))
            else:
                p.fillRect(1, h - bar_h, w - 2, bar_h, QColor(0, 200, 0))
                p.fillRect(1, h - yellow_h, w - 2, int(h * 0.15), QColor(255, 200, 0))
                p.fillRect(1, h - int(h * 0.08), w - 2, int(h * 0.08), QColor(255, 0, 0))

        p.setPen(QColor(60, 60, 60))
        p.drawRect(0, 0, w - 1, h - 1)


class ChannelStrip(QWidget):
    volumeChanged = pyqtSignal(int, float)
    muteToggled = pyqtSignal(int, bool)
    soloToggled = pyqtSignal(int, bool)

    def __init__(self, track_id, name=_("Track"), parent=None):
        super().__init__(parent)
        self._track_id = track_id
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self._name_label = QLabel(name)
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setWordWrap(True)
        self._name_label.setFixedWidth(60)
        f = self._name_label.font()
        f.setPointSize(8)
        self._name_label.setFont(f)
        layout.addWidget(self._name_label)

        self._meter = PeakMeter()
        layout.addWidget(self._meter, 1, Qt.AlignCenter)

        self._fader = QSlider(Qt.Vertical)
        self._fader.setRange(0, 100)
        self._fader.setValue(75)
        self._fader.setTickPosition(QSlider.TicksRight)
        self._fader.setTickInterval(25)
        self._fader.valueChanged.connect(self._on_fader)
        layout.addWidget(self._fader, 0, Qt.AlignCenter)

        db_label = QLabel("0 dB")
        db_label.setAlignment(Qt.AlignCenter)
        db_label.setFixedWidth(50)
        f2 = db_label.font()
        f2.setPointSize(7)
        db_label.setFont(f2)
        self._db_label = db_label
        layout.addWidget(db_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(2)
        self._mute_btn = QPushButton(_("M"))
        self._mute_btn.setFixedSize(22, 18)
        self._mute_btn.setCheckable(True)
        self._mute_btn.setStyleSheet(
            "QPushButton { font-size: 9px; padding: 0; }"
            "QPushButton:checked { background-color: #cc4400; color: white; }"
        )
        self._mute_btn.toggled.connect(lambda v: self.muteToggled.emit(self._track_id, v))
        btn_row.addWidget(self._mute_btn)

        self._solo_btn = QPushButton(_("S"))
        self._solo_btn.setFixedSize(22, 18)
        self._solo_btn.setCheckable(True)
        self._solo_btn.setStyleSheet(
            "QPushButton { font-size: 9px; padding: 0; }"
            "QPushButton:checked { background-color: #ccaa00; color: white; }"
        )
        self._solo_btn.toggled.connect(lambda v: self.soloToggled.emit(self._track_id, v))
        btn_row.addWidget(self._solo_btn)
        layout.addLayout(btn_row)

    def _on_fader(self, value):
        vol = value / 75.0
        db = 20 * __import__("math").log10(max(vol, 0.001))
        self._db_label.setText(f"{db:.1f} dB")
        self.volumeChanged.emit(self._track_id, vol)

    def set_level(self, level):
        self._meter.set_level(level)

    def track_id(self):
        return self._track_id


class AudioMixerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(_("Audio Mixer"))
        tf = title.font()
        tf.setBold(True)
        tf.setPointSize(10)
        title.setFont(tf)
        title.setStyleSheet("padding: 4px 8px;")
        layout.addWidget(title)

        self._strip_container = QWidget()
        self._strip_layout = QHBoxLayout(self._strip_container)
        self._strip_layout.setContentsMargins(4, 0, 4, 0)
        self._strip_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._strip_container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(280)
        layout.addWidget(scroll, 1)

        self._strips = {}

    def add_track(self, track_id, name=_("Track")):
        if track_id in self._strips:
            return
        strip = ChannelStrip(track_id, name)
        strip.volumeChanged.connect(self._on_volume_changed)
        strip.muteToggled.connect(self._on_mute_toggled)
        strip.soloToggled.connect(self._on_solo_toggled)
        self._strips[track_id] = strip
        self._strip_layout.addWidget(strip)
        self._strip_layout.addStretch()

    def remove_track(self, track_id):
        if track_id in self._strips:
            strip = self._strips.pop(track_id)
            self._strip_layout.removeWidget(strip)
            strip.deleteLater()

    def set_track_level(self, track_id, level):
        if track_id in self._strips:
            self._strips[track_id].set_level(level)

    def _on_volume_changed(self, track_id, vol):
        pass

    def _on_mute_toggled(self, track_id, muted):
        pass

    def _on_solo_toggled(self, track_id, soloed):
        pass
