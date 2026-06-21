import os
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox, QSizePolicy
)
from PyQt5.QtGui import QColor

from .video_engine import VideoProject, Timeline, TransportState, Clip, Track
from .video_ffmpeg import get_metadata, extract_frame, FrameSequence
from .video_glplayer import VideoGLPlayer
from .timeline_widget import TimelineWidget
from .transport_bar import TransportBar
from .i18n import _


_TOOLBAR_STYLE = """
QPushButton {
    background-color: #1e1e32;
    color: #e0e0e0;
    border: 1px solid #2a2a40;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2a2a40;
    border-color: #3a3a5e;
}
QPushButton:pressed {
    background-color: #3a3a5e;
}
"""


class VideoMode(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = VideoProject()
        self.player = VideoGLPlayer()
        self.timeline = TimelineWidget()
        self.transport = TransportBar()
        self.play_timer = QTimer(self)
        self.frame_seq = None
        self.current_frame = None

        self._setup_ui()
        self._wire_signals()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #0e0e1a;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = self._build_toolbar()
        main_layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            "QSplitter::handle { background: #2a2a40; }"
        )

        self.player.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.timeline.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter.addWidget(self.player)
        splitter.addWidget(self.timeline)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter, 1)

        self.transport.setFixedHeight(44)
        main_layout.addWidget(self.transport)

    def _build_toolbar(self):
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("background-color: #121220; border-bottom: 1px solid #2a2a40;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._btn_import = QPushButton(_("Import"))
        self._btn_import.setStyleSheet(_TOOLBAR_STYLE)
        self._btn_import.clicked.connect(self.import_video)
        layout.addWidget(self._btn_import)

        self._btn_export = QPushButton(_("Export"))
        self._btn_export.setStyleSheet(_TOOLBAR_STYLE)
        self._btn_export.clicked.connect(self.export_video)
        layout.addWidget(self._btn_export)

        self._btn_timeline = QPushButton(_("Timeline"))
        self._btn_timeline.setStyleSheet(_TOOLBAR_STYLE)
        layout.addWidget(self._btn_timeline)

        layout.addStretch()
        return toolbar

    def _wire_signals(self):
        self.transport.playToggled.connect(self._on_play_toggled)
        self.transport.stopTriggered.connect(self.stop_playback)
        self.transport.stepForward.connect(self.step_forward)
        self.transport.stepBackward.connect(self.step_backward)
        self.transport.goToStart.connect(self._on_go_to_start)
        self.transport.goToEnd.connect(self._on_go_to_end)
        self.transport.zoomChanged.connect(self._on_zoom_changed)
        self.transport.snapToggled.connect(self._on_snap_toggled)
        self.transport.loopToggled.connect(self._on_loop_toggled)

        self.timeline.timeChanged.connect(self.seek_to)
        self.play_timer.timeout.connect(self.update_frame)

    def _on_play_toggled(self, playing):
        if playing:
            self.play_timer.start(int(1000.0 / self._get_fps()))
        else:
            self.play_timer.stop()

    def _on_go_to_start(self):
        self.seek_to(0.0)

    def _on_go_to_end(self):
        dur = self.project.timeline.duration()
        self.seek_to(dur)

    def _on_zoom_changed(self, scale):
        zoom_val = scale * 50.0
        self.timeline.set_zoom(zoom_val)

    def _on_snap_toggled(self, enabled):
        self.project.transport.snap = enabled

    def _on_loop_toggled(self, enabled):
        self.project.transport.loop = enabled

    def _get_fps(self):
        if self.frame_seq is not None:
            return self.frame_seq.fps
        return 30.0

    def _frame_duration(self):
        return 1.0 / self._get_fps()

    def _update_transport_display(self):
        dur = self.project.timeline.duration()
        self.transport.set_duration(dur)
        self.transport.set_current_time(self.project.transport.current_time)

    def _format_timecode(self, seconds):
        fps = self._get_fps()
        total_frames = int(round(seconds * fps))
        h = total_frames // (3600 * int(fps))
        m = (total_frames // (60 * int(fps))) % 60
        s = (total_frames // int(fps)) % 60
        f = total_frames % int(fps)
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

    def import_video(self):
        filepath, _filter = QFileDialog.getOpenFileName(
            self, _("Import Video"), "",
            _("Video Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv);;All Files (*)")
        )
        if not filepath:
            return

        meta = get_metadata(filepath)
        if meta is None:
            QMessageBox.warning(self, _("Import Error"),
                                _("Could not read video metadata. Ensure ffprobe is installed."))
            return

        self.project = VideoProject()
        self.project.add_media(meta)

        tl = self.project.timeline
        tl.add_track(_("Video 1"), "video")
        tl.add_track(_("Video 2"), "video")
        tl.add_track(_("Audio 1"), "audio")
        tl.add_track(_("Audio 2"), "audio")

        clip_name = os.path.splitext(os.path.basename(filepath))[0]
        clip_duration = meta.get('duration', 10.0)
        video_track = tl.tracks[0]
        clip_id = tl.next_clip_id
        tl.next_clip_id += 1
        clip = Clip(
            clip_id, filepath,
            start_time=0.0,
            duration=clip_duration,
            in_point=0.0,
            out_point=clip_duration,
            track_id=video_track.id,
            enabled=True,
            name=clip_name
        )
        video_track.add_clip(clip)

        w = meta.get('width', 640)
        h = meta.get('height', 480)
        fps = meta.get('fps', 30.0)

        if self.frame_seq is not None:
            self.frame_seq.close()
            self.frame_seq = None

        self.frame_seq = FrameSequence(filepath, w, h, fps)

        frame = self.frame_seq.read()
        if frame is not None:
            self.current_frame = frame
            aspect = float(w) / float(h) if h > 0 else 16.0 / 9.0
            self.player.set_aspect_ratio(aspect)
            self.player.set_frame(frame)
            self.player.set_timecode(self._format_timecode(0.0))

        self.project.transport.current_time = 0.0
        self.project.transport.playing = False

        self.timeline.set_timeline(tl)
        self.timeline.set_current_time(0.0)
        self._update_transport_display()

    def export_video(self):
        QMessageBox.information(
            self, _("Export"),
            _("Export functionality will be available in a future version.")
        )

    def toggle_playback(self):
        self.project.transport.toggle_play()
        playing = self.project.transport.playing
        if playing:
            self.play_timer.start(int(1000.0 / self._get_fps()))
            self.transport.set_playing(True)
        else:
            self.play_timer.stop()
            self.transport.set_playing(False)

    def stop_playback(self):
        self.play_timer.stop()
        self.project.transport.stop()
        self.transport.set_playing(False)
        self.seek_to(0.0)

    def step_forward(self):
        self.play_timer.stop()
        self.project.transport.playing = False
        self.transport.set_playing(False)
        fd = self._frame_duration()
        new_time = self.project.transport.current_time + fd
        self.seek_to(new_time)

    def step_backward(self):
        self.play_timer.stop()
        self.project.transport.playing = False
        self.transport.set_playing(False)
        fd = self._frame_duration()
        new_time = max(0.0, self.project.transport.current_time - fd)
        self.seek_to(new_time)

    def seek_to(self, seconds):
        seconds = max(0.0, seconds)
        self.project.transport.seek(seconds)
        self.timeline.set_current_time(seconds)

        if self.frame_seq is not None:
            self.frame_seq.seek(seconds)
            frame = self.frame_seq.read()
            if frame is not None:
                self.current_frame = frame
                self.player.set_frame(frame)
                self.player.set_timecode(self._format_timecode(seconds))

        self._update_transport_display()

    def update_frame(self):
        if self.frame_seq is None:
            self.play_timer.stop()
            return

        fd = self._frame_duration()
        new_time = self.project.transport.current_time + fd
        dur = self.project.timeline.duration()

        if new_time >= dur:
            if self.project.transport.loop:
                new_time = 0.0
                self.frame_seq.seek(0.0)
            else:
                self.play_timer.stop()
                self.project.transport.playing = False
                self.transport.set_playing(False)
                return

        self.project.transport.current_time = new_time
        self.timeline.set_current_time(new_time)

        frame = self.frame_seq.read()
        if frame is None:
            if self.project.transport.loop:
                self.frame_seq.seek(0.0)
                frame = self.frame_seq.read()
                self.project.transport.current_time = 0.0
                self.timeline.set_current_time(0.0)
            else:
                self.play_timer.stop()
                self.project.transport.playing = False
                self.transport.set_playing(False)
                return

        self.current_frame = frame
        self.player.set_frame(frame)
        self.player.set_timecode(self._format_timecode(new_time))
        self._update_transport_display()

    def refresh_timeline(self):
        self.timeline.refresh()

    def closeEvent(self, event):
        if self.frame_seq is not None:
            self.frame_seq.close()
            self.frame_seq = None
        self.play_timer.stop()
        super().closeEvent(event)
