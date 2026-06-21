import os

from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QLineF, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QFontMetrics
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton, QFrame, QSizePolicy
from .video_engine import Timeline, Track, Clip, TransportState, VideoProject


class TimeRuler(QWidget):
    timeSelected = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 50.0
        self._duration = 60.0
        self._current_time = 0.0
        self._scroll_offset = 0
        self.setFixedHeight(28)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @property
    def zoom(self):
        return self._zoom

    def set_zoom(self, scale):
        self._zoom = max(10.0, scale)
        self.update()

    def set_duration(self, seconds):
        self._duration = max(0.0, seconds)
        self.update()

    def set_current_time(self, time):
        self._current_time = max(0.0, time)
        self.update()

    def set_scroll_offset(self, offset):
        self._scroll_offset = offset
        self.update()

    def minimumSizeHint(self):
        return QSize(max(400, int(self._duration * self._zoom) + 80), 28)

    def sizeHint(self):
        return QSize(max(400, int(self._duration * self._zoom) + 80), 28)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x() + self._scroll_offset
            time = x / self._zoom
            self._current_time = max(0.0, min(time, self._duration))
            self.timeSelected.emit(self._current_time)
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            x = event.pos().x() + self._scroll_offset
            time = x / self._zoom
            self._current_time = max(0.0, min(time, self._duration))
            self.timeSelected.emit(self._current_time)
            self.update()
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(self.rect(), QColor("#1a1a2e"))

        font = p.font()
        font.setPointSize(8)
        font.setFamily("monospace")
        p.setFont(font)
        fm = QFontMetrics(font)

        p.save()
        p.translate(-self._scroll_offset, 0)

        p.setPen(QColor("#555"))
        total_sec = int(self._duration) + 1
        for sec in range(total_sec):
            x = int(sec * self._zoom)
            p.drawLine(x, 0, x, self.height())
            p.setPen(QColor("#aaa"))
            mins = sec // 60
            rem_sec = sec % 60
            label = f"{mins:02d}:{rem_sec:02d}"
            p.drawText(x + 3, 0, int(self._zoom - 6), self.height(),
                       Qt.AlignLeft | Qt.AlignVCenter, label)
            p.setPen(QColor("#555"))

        half_step = self._zoom / 2.0
        if half_step >= 8:
            p.setPen(QColor("#333"))
            for sec in range(total_sec):
                x = int(sec * self._zoom + half_step)
                p.drawLine(x, self.height() - 8, x, self.height())

        p.restore()

        phx = int(self._current_time * self._zoom) - self._scroll_offset
        if 0 <= phx <= self.width():
            p.setPen(QPen(QColor(255, 60, 60), 2))
            p.drawLine(phx, 0, phx, self.height())


class TrackRow(QWidget):
    clipClicked = pyqtSignal(int)
    trackClicked = pyqtSignal(int)
    splitRequested = pyqtSignal(float, int)

    def __init__(self, track=None, row_index=0, parent=None):
        super().__init__(parent)
        self._track = track
        self._row_index = row_index
        self._zoom = 50.0
        self._current_time = 0.0
        self._selected_clip_id = -1
        self.setFixedHeight(48)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_track(self, track):
        self._track = track
        self.update()

    def set_row_index(self, idx):
        self._row_index = idx
        self.update()

    def set_selected(self, clip_id):
        self._selected_clip_id = clip_id
        self.update()

    def set_zoom(self, scale):
        self._zoom = max(10.0, scale)
        self.update()

    def set_current_time(self, time):
        self._current_time = max(0.0, time)
        self.update()

    def minimumSizeHint(self):
        return QSize(400, 48)

    def sizeHint(self):
        return QSize(400, 48)

    @staticmethod
    def _header_width():
        return 80

    @staticmethod
    def _audio_waveform_data(clip, num_bars=40):
        import hashlib
        key = (clip.name or clip.filepath or str(clip.id)).encode()
        h = hashlib.md5(key).digest()
        bars = []
        for i in range(num_bars):
            v = (h[i % 16] + (i * 7)) % 256
            bars.append(0.15 + (v / 255.0) * 0.7)
        return bars

    def _draw_audio_waveform(self, p, clip_x, clip_y, clip_w, clip_h, clip):
        bars = self._audio_waveform_data(clip)
        bar_w = max(2, clip_w // len(bars))
        mid_y = clip_y + clip_h / 2
        p.setPen(Qt.NoPen)
        for i, amp in enumerate(bars):
            bx = clip_x + i * bar_w
            if bx > clip_x + clip_w:
                break
            bh = max(2, int(amp * clip_h * 0.4))
            color = QColor(100, 220, 100, 160)
            p.setBrush(color)
            p.drawRect(bx, int(mid_y - bh / 2), max(1, bar_w - 1), bh)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            if x < self._header_width():
                if self._track is not None:
                    self.trackClicked.emit(self._track.id)
                return
            if self._track is None:
                return
            content_x = x - self._header_width()
            for clip in self._track.clips:
                cx = int(clip.start_time * self._zoom)
                cw = max(4, int(clip.duration * self._zoom))
                if cx <= content_x < cx + cw:
                    self.clipClicked.emit(clip.id)
                    return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._track is not None:
            x = event.pos().x()
            if x >= self._header_width():
                content_x = x - self._header_width()
                time = content_x / self._zoom
                for clip in self._track.clips:
                    cx = int(clip.start_time * self._zoom)
                    cw = max(4, int(clip.duration * self._zoom))
                    if cx <= content_x < cx + cw:
                        self.splitRequested.emit(time, clip.id)
                        return
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        hdr_w = self._header_width()

        if self._row_index % 2 == 0:
            p.fillRect(self.rect(), QColor("#121220"))
        else:
            p.fillRect(self.rect(), QColor("#1a1a2e"))

        p.fillRect(0, 0, hdr_w, h, QColor("#1e1e32"))
        p.setPen(QPen(QColor("#2a2a40"), 1))
        p.drawLine(hdr_w - 1, 0, hdr_w - 1, h)

        font = p.font()
        font.setPointSize(9)
        p.setFont(font)

        if self._track is None:
            p.setPen(QColor("#555"))
            p.drawText(0, 0, hdr_w, h, Qt.AlignCenter, "Empty")
            return

        type_color = QColor("#3a6aaa") if self._track.type == "video" else QColor("#3a8a3a")
        p.setBrush(type_color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, (h - 16) // 2, 16, 16, 3, 3)
        type_char = "V" if self._track.type == "video" else "A"
        p.setPen(QColor("#fff"))
        p.drawText(4, (h - 16) // 2, 16, 16, Qt.AlignCenter, type_char)

        p.setPen(QColor("#e0e0e0") if self._track.enabled else QColor("#666"))
        name_x = 24
        name_w = hdr_w - 50
        fm = QFontMetrics(font)
        elided = fm.elidedText(self._track.name if self._track.name else f"Track {self._track.id}",
                                Qt.ElideRight, name_w)
        p.drawText(name_x, 0, name_w, h, Qt.AlignLeft | Qt.AlignVCenter, elided)

        p.setPen(QColor("#aaa") if self._track.enabled else QColor("#555"))
        p.drawText(hdr_w - 22, 0, 10, h, Qt.AlignCenter, "V" if self._track.enabled else "-")
        p.setPen(QColor("#555"))
        p.drawText(hdr_w - 12, 0, 10, h, Qt.AlignCenter, "-")

        p.setPen(Qt.NoPen)
        for clip in self._track.clips:
            clip_x = hdr_w + int(clip.start_time * self._zoom)
            clip_w = max(4, int(clip.duration * self._zoom))
            if clip_x > w or clip_x + clip_w < 0:
                continue

            clip_h = h - 8
            clip_y = 4
            is_selected = clip.id == self._selected_clip_id

            if self._track.type == "video":
                clip_color = QColor("#3a6aaa")
                sel_color = QColor("#4a7abb")
            else:
                clip_color = QColor("#3a8a3a")
                sel_color = QColor("#4a9b4a")

            p.setBrush(sel_color if is_selected else clip_color)
            p.drawRoundedRect(clip_x, clip_y, clip_w, clip_h, 3, 3)

            if self._track.type == "audio" and clip_w > 20:
                self._draw_audio_waveform(p, clip_x, clip_y, clip_w, clip_h, clip)

            if is_selected:
                p.setPen(QPen(QColor("#ff8800"), 2))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(clip_x, clip_y, clip_w, clip_h, 3, 3)
                p.setPen(Qt.NoPen)
                p.setBrush(sel_color)

            if clip_w > 30:
                p.setPen(QColor("#e0e0e0"))
                font.setPointSize(8)
                p.setFont(font)
                fname = clip.name if clip.name else (os.path.basename(clip.filepath) if clip.filepath else "")
                if fname:
                    try:
                        tw = p.fontMetrics().horizontalAdvance(fname)
                    except AttributeError:
                        tw = p.fontMetrics().width(fname)
                    label = fname
                    if clip_w - 8 > tw + 30:
                        dur_text = f" [{clip.duration:.1f}s]"
                        label = fname + dur_text
                    p.drawText(clip_x + 4, clip_y, clip_w - 8, clip_h,
                               Qt.AlignLeft | Qt.AlignVCenter, label)

        phx = hdr_w + int(self._current_time * self._zoom)
        if 0 <= phx <= w:
            p.setPen(QPen(QColor(255, 60, 60), 2))
            p.drawLine(phx, 0, phx, h)


class TimelineWidget(QWidget):
    timeChanged = pyqtSignal(float)
    clipSelected = pyqtSignal(int)
    trackSelected = pyqtSignal(int)
    splitRequested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timeline = Timeline()
        self._current_time = 0.0
        self._zoom = 50.0
        self._selected_clip_id = -1
        self._selected_track_id = -1
        self._snap_enabled = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.ruler = TimeRuler()
        self.ruler.timeSelected.connect(self._on_ruler_time_selected)
        layout.addWidget(self.ruler)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: #121220; border: none; }"
            "QScrollBar:horizontal { background: #1a1a2e; height: 10px; }"
            "QScrollBar:vertical { background: #1a1a2e; width: 10px; }"
        )
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._on_hscroll)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: #121220;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        transport_bar = QFrame()
        transport_bar.setFixedHeight(36)
        transport_bar.setStyleSheet("background: #1a1a2e; border-top: 1px solid #2a2a40;")
        tb_layout = QHBoxLayout(transport_bar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.addWidget(QLabel("Transport Controls", styleSheet="color: #555; font-size: 10px;"))
        layout.addWidget(transport_bar)

    @property
    def snap_enabled(self):
        return self._snap_enabled

    def add_track(self, is_audio=False):
        t = "audio" if is_audio else "video"
        track_id = self._timeline.add_track(f"{t.capitalize()} {len(self._timeline.tracks) + 1}", t)
        self.refresh()
        return track_id

    def remove_track(self, track_id=None):
        if track_id is None and self._timeline.tracks:
            track_id = self._timeline.tracks[-1].id
        if track_id is not None:
            self._timeline.remove_track(track_id)
            self.refresh()

    def clear(self):
        self._timeline.clear()
        self.refresh()

    def zoom_in(self):
        self.set_zoom(self._zoom * 1.4)

    def zoom_out(self):
        self.set_zoom(self._zoom / 1.4)

    def zoom_fit(self):
        dur = self._timeline.duration() if self._timeline else 60.0
        if dur > 0:
            avail = self.scroll_area.viewport().width() - 100
            self.set_zoom(max(10.0, avail / dur))
        else:
            self.set_zoom(50.0)

    def toggle_snap(self):
        self._snap_enabled = not self._snap_enabled

    def set_zoom_level(self, scale):
        self.set_zoom(scale * 50.0)

    def add_clip_to_track(self, name, filepath, track_index=0):
        if not self._timeline.tracks:
            self.add_track()
        if track_index >= len(self._timeline.tracks):
            track_index = 0
        track = self._timeline.tracks[track_index]
        start = self._timeline.duration()
        if self._snap_enabled:
            start = round(start * 4) / 4.0
        self._timeline.add_clip(track.id, filepath, start, 5.0, name)
        self.refresh()

    def set_timeline(self, timeline):
        self._timeline = timeline
        self.refresh()

    def set_current_time(self, seconds):
        self._current_time = max(0.0, seconds)
        self.ruler.set_current_time(self._current_time)
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TrackRow):
                item.widget().set_current_time(self._current_time)

    def set_zoom(self, scale):
        self._zoom = max(10.0, scale)
        self.ruler.set_zoom(self._zoom)
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TrackRow):
                item.widget().set_zoom(self._zoom)
        self._update_content_size()

    def refresh(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._timeline is not None:
            for i, track in enumerate(self._timeline.tracks):
                row = TrackRow(track, row_index=i)
                row.set_zoom(self._zoom)
                row.set_current_time(self._current_time)
                row.set_selected(self._selected_clip_id)
                row.clipClicked.connect(self._on_clip_clicked)
                row.trackClicked.connect(self._on_track_clicked)
                row.splitRequested.connect(self._on_split_requested)
                self.scroll_layout.addWidget(row)

        self.scroll_layout.addStretch()
        self._update_content_size()

    def _update_content_size(self):
        dur = self._timeline.duration() if self._timeline and self._timeline.tracks else 60.0
        total_w = max(400, int(dur * self._zoom) + 80 + 20)
        count = len(self._timeline.tracks) if self._timeline else 1
        total_h = max(count, 1) * 48
        self.scroll_content.setMinimumSize(total_w, total_h)

    def _on_hscroll(self, value):
        self.ruler.set_scroll_offset(value)

    def _on_ruler_time_selected(self, time):
        self._current_time = time
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TrackRow):
                item.widget().set_current_time(time)
        self.timeChanged.emit(time)

    def _on_clip_clicked(self, clip_id):
        self._selected_clip_id = clip_id
        self.clipSelected.emit(clip_id)
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TrackRow):
                item.widget().set_selected(clip_id)

    def _on_track_clicked(self, track_id):
        self._selected_track_id = track_id
        self.trackSelected.emit(track_id)

    def _on_split_requested(self, time, clip_id):
        self.splitRequested.emit(time)
