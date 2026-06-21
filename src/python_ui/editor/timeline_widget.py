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


BLEND_COLORS = {
    "normal": "#6aaa3a", "multiply": "#aa3a3a", "screen": "#3a6aaa",
    "overlay": "#aa8a3a", "darken": "#3a3a3a", "lighten": "#aaaaaa",
    "difference": "#aa3aaa", "add": "#3aaa3a", "subtract": "#aa6a3a",
}

class TrackRow(QWidget):
    clipClicked = pyqtSignal(int)
    trackClicked = pyqtSignal(int)
    splitRequested = pyqtSignal(float, int)
    visibilityToggled = pyqtSignal(int, bool)
    lockToggled = pyqtSignal(int, bool)
    muteToggled = pyqtSignal(int, bool)
    soloToggled = pyqtSignal(int, bool)
    blendCycle = pyqtSignal(int)

    def __init__(self, track=None, row_index=0, parent=None):
        super().__init__(parent)
        self._track = track
        self._row_index = row_index
        self._zoom = 50.0
        self._current_time = 0.0
        self._selected_clip_id = -1
        self._snap_time = -1.0
        self.setFixedHeight(52)
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

    def set_snap_time(self, time):
        self._snap_time = time
        self.update()

    @staticmethod
    def _header_width():
        return 130

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

    def _draw_track_header(self, p, hdr_w, h):
        if self._track is None:
            p.setPen(QColor("#555"))
            p.drawText(0, 0, hdr_w, h, Qt.AlignCenter, "Empty")
            return

        is_video = self._track.type == "video"
        base_color = QColor("#1e1e32")
        p.fillRect(0, 0, hdr_w, h, base_color)

        if not self._track.enabled:
            p.fillRect(0, 0, hdr_w, h, QColor(30, 30, 50, 200))

        type_color = QColor("#3a6aaa") if is_video else QColor("#3a8a3a")
        p.setBrush(type_color)
        p.setPen(Qt.NoPen)
        badge_size = 18
        p.drawRoundedRect(6, (h - badge_size) // 2, badge_size, badge_size, 3, 3)
        type_char = "V" if is_video else "A"
        p.setPen(QColor("#fff"))

        font = p.font()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        p.drawText(6, (h - badge_size) // 2, badge_size, badge_size, Qt.AlignCenter, type_char)

        font.setBold(False)
        font.setPointSize(8)
        p.setFont(font)

        name_x = 28
        name_w = hdr_w - 82
        p.setPen(QColor("#e0e0e0") if self._track.enabled else QColor("#666"))
        fm = QFontMetrics(font)
        elided = fm.elidedText(self._track.name or f"Track {self._track.id}",
                               Qt.ElideRight, name_w)
        p.drawText(name_x, 0, name_w, 22, Qt.AlignLeft | Qt.AlignVCenter, elided)

        if is_video:
            blend_lbl = self._track.blend_mode_label()
            p.setPen(QColor(BLEND_COLORS.get(self._track.blend_mode, "#aaa")))
            font.setPointSize(7)
            p.setFont(font)
            p.drawText(6, 24, hdr_w - 12, 12, Qt.AlignLeft, blend_lbl)

        btn_y = 24
        btn_w = 22
        btn_h = 22
        spacing = 2
        x = 6

        self._header_buttons = []

        eye_color = QColor("#ffcc00") if self._track.visible else QColor("#555")
        self._draw_header_btn(p, x, btn_y, btn_w, btn_h, eye_color, "\u25C9")
        self._header_buttons.append(("visible", x, btn_y, btn_w, btn_h))
        x += btn_w + spacing

        lock_color = QColor("#ff8844") if self._track.locked else QColor("#555")
        self._draw_header_btn(p, x, btn_y, btn_w, btn_h, lock_color, "\u26BF")
        self._header_buttons.append(("locked", x, btn_y, btn_w, btn_h))
        x += btn_w + spacing

        if not is_video:
            mute_color = QColor("#ff4444") if self._track.muted else QColor("#555")
            self._draw_header_btn(p, x, btn_y, btn_w, btn_h, mute_color, "M")
            self._header_buttons.append(("muted", x, btn_y, btn_w, btn_h))
            x += btn_w + spacing

            solo_color = QColor("#ffaa00") if self._track.solo else QColor("#555")
            self._draw_header_btn(p, x, btn_y, btn_w, btn_h, solo_color, "S")
            self._header_buttons.append(("solo", x, btn_y, btn_w, btn_h))

        p.fillRect(hdr_w - 1, 0, 1, h, QColor("#2a2a40"))

    def _draw_header_btn(self, p, x, y, w, h, color, text):
        p.setPen(QPen(color, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(x, y, w, h, 3, 3)
        p.setPen(color)
        font = p.font()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        p.drawText(x, y, w, h, Qt.AlignCenter, text)

    def _hit_test_header(self, x):
        if not hasattr(self, '_header_buttons'):
            return None
        for action, hx, hy, hw, hh in self._header_buttons:
            if hx <= x < hx + hw and hy <= y < hy + hh:
                return action
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            if x < self._header_width():
                if self._track is not None:
                    action = self._hit_test_header(x)
                    if action == "visible":
                        self._track.visible = not self._track.visible
                        self.visibilityToggled.emit(self._track.id, self._track.visible)
                        self.update()
                    elif action == "locked":
                        self._track.locked = not self._track.locked
                        self.lockToggled.emit(self._track.id, self._track.locked)
                        self.update()
                    elif action == "muted":
                        self._track.muted = not self._track.muted
                        self.muteToggled.emit(self._track.id, self._track.muted)
                        self.update()
                    elif action == "solo":
                        self._track.solo = not self._track.solo
                        self.soloToggled.emit(self._track.id, self._track.solo)
                        self.update()
                    elif y >= 24 and self._track.type == "video":
                        self._track.cycle_blend_mode()
                        self.blendCycle.emit(self._track.id)
                        self.update()
                    else:
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

        self._draw_track_header(p, hdr_w, h)

        if self._track is None:
            return

        p.setPen(Qt.NoPen)
        for clip in self._track.clips:
            if not self._track.visible and not self._track.locked:
                continue
            clip_x = hdr_w + int(clip.start_time * self._zoom)
            clip_w = max(4, int(clip.duration * self._zoom))
            if clip_x > w or clip_x + clip_w < 0:
                continue

            clip_h = h - 10
            clip_y = 5
            is_selected = clip.id == self._selected_clip_id

            if self._track.type == "video":
                clip_color = QColor("#3a6aaa")
                sel_color = QColor("#4a7abb")
            else:
                clip_color = QColor("#3a8a3a")
                sel_color = QColor("#4a9b4a")

            if not clip.enabled:
                clip_color = clip_color.darker(150)
                sel_color = sel_color.darker(150)

            p.setBrush(sel_color if is_selected else clip_color)

            has_transition = self._track.type == "video" and clip_w > 60
            if has_transition:
                p.drawRect(clip_x, clip_y, clip_w, clip_h)
                p.drawRoundedRect(clip_x + 6, clip_y + 6, clip_w - 12, clip_h - 12, 3, 3)
            else:
                p.drawRoundedRect(clip_x, clip_y, clip_w, clip_h, 3, 3)

            if self._track.type == "audio" and clip_w > 20 and clip.enabled:
                self._draw_audio_waveform(p, clip_x, clip_y, clip_w, clip_h, clip)

            if is_selected:
                p.setPen(QPen(QColor("#ff8800"), 2))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(clip_x, clip_y, clip_w, clip_h, 3, 3)
                p.setPen(Qt.NoPen)
                p.setBrush(sel_color)

            if clip_w > 30:
                p.setPen(QColor("#e0e0e0") if clip.enabled else QColor("#666"))
                font = p.font()
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

            if has_transition and is_selected:
                fade_w = min(20, clip_w // 4)
                fade_rect = QRect(clip_x + 6, clip_y + 6, fade_w, clip_h - 12)
                p.fillRect(fade_rect, QColor(255, 255, 255, 30))

        if self._snap_time >= 0:
            snap_x = hdr_w + int(self._snap_time * self._zoom)
            if 0 <= snap_x <= w:
                p.setPen(QPen(QColor(100, 200, 255), 1, Qt.DashLine))
                p.drawLine(snap_x, 0, snap_x, h)

        phx = hdr_w + int(self._current_time * self._zoom)
        if 0 <= phx <= w:
            p.setPen(QPen(QColor(255, 60, 60), 2))
            p.drawLine(phx, 0, phx, h)


class TimelineWidget(QWidget):
    dropAccepted = pyqtSignal(str)
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
        self.setAcceptDrops(True)

    MEDIA_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv',
                        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff',
                        '.webp', '.wav', '.mp3', '.aac', '.flac', '.ogg'}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile() or '')[1].lower()
                if ext in self.MEDIA_EXTENSIONS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        drop_time = self._current_time
        target_track = None
        if self._timeline.tracks:
            target_track = next((t for t in self._timeline.tracks if t.type == 'video'), self._timeline.tracks[0])
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext not in self.MEDIA_EXTENSIONS:
                continue
            if not self._timeline.tracks:
                tid = self.add_track(is_audio=(ext in ('.wav', '.mp3', '.aac', '.flac', '.ogg')))
            if target_track is None and self._timeline.tracks:
                target_track = self._timeline.tracks[-1]
            if target_track is not None:
                clip = target_track.add_clip(path, drop_time, duration=5.0)
                drop_time += 5.0
                self.refresh()
                self.dropAccepted.emit(os.path.basename(path))

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
                row.visibilityToggled.connect(lambda tid, v: self.refresh())
                row.lockToggled.connect(lambda tid, v: self.refresh())
                row.muteToggled.connect(lambda tid, v: self.refresh())
                row.soloToggled.connect(lambda tid, v: self.refresh())
                row.blendCycle.connect(lambda tid: self.refresh())
                self.scroll_layout.addWidget(row)

        self.scroll_layout.addStretch()
        self._update_content_size()

    def _update_content_size(self):
        dur = self._timeline.duration() if self._timeline and self._timeline.tracks else 60.0
        total_w = max(400, int(dur * self._zoom) + 80 + 20)
        count = len(self._timeline.tracks) if self._timeline else 1
        total_h = max(count, 1) * 52
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
