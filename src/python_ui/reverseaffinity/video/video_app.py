import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QTabWidget, QDockWidget, QToolBar, QAction, QStatusBar,
    QMenuBar, QSplitter, QListWidget, QTreeWidget, QTreeWidgetItem,
    QPushButton, QSlider, QSpinBox, QComboBox, QToolButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer, QSize, QUrl, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap, QImage, QKeySequence

from reverseaffinity.i18n import _
from reverseaffinity.shared.resources import apply_dark_theme
from editor.timeline_widget import TimelineWidget
from editor.transport_bar import TransportBar
from editor.video_engine import Timeline, Track, Clip, TransportState
from editor.file_dialog import get_open_file_name, get_open_file_names, get_save_file_name
from editor.color_grading import ColorGradingPanel
from editor.scopes import ScopesPanel
from editor.crop_tool import CropOverlay, CropControlPanel
from editor.lut import LutPanel, apply_lut
from editor.chroma_key import ChromaKeyWidget
from editor.blur_sharpen import BlurSharpenWidget
from editor.audio_mixer import AudioMixerPanel
from editor.video_glplayer import VideoGLPlayer
from editor.gpu_accel import GPUAccel
from editor.export_dialog import ExportDialog


class SourceMonitor(QWidget):
    mediaLoaded = pyqtSignal(str)

    def __init__(self, label="Preview", parent=None):
        super().__init__(parent)
        self._media_path = None
        self._playing = False
        self._current_frame = 0
        self._total_frames = 0
        self._fps = 30.0
        self._loop = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(250)

        tb = QToolBar()
        tb.setIconSize(QSize(16, 16))
        tb.addAction(_("Import"), self.import_media)
        self._play_action = tb.addAction(_("Play"), self.toggle_play)
        self._loop_action = tb.addAction(_("Loop"), self.toggle_loop)
        self._loop_action.setCheckable(True)
        self.time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self.time_label.setStyleSheet("color: #aaa; padding: 2px 8px;")
        tb.addWidget(self.time_label)
        layout.addWidget(tb)

        self._video_container = QWidget()
        self._video_layout = QVBoxLayout(self._video_container)
        self._video_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel(label)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumHeight(200)
        self.video_label.setStyleSheet(
            "background-color: #0a0a0a; color: #444; font-size: 18px; border: 1px solid #222;"
        )
        self.video_label.setVisible(False)

        self.gl_player = VideoGLPlayer()
        self.gl_player.setMinimumHeight(200)
        self._video_layout.addWidget(self.gl_player, 1)
        self._video_layout.addWidget(self.video_label, 1)

        self._crop_overlay = CropOverlay(self._video_container)
        self._crop_overlay.setVisible(False)
        layout.addWidget(self._video_container, 1)

        self.scrub_slider = QSlider(Qt.Horizontal)
        self.scrub_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #333; }
            QSlider::handle:horizontal { background: #ff6b35; width: 12px; margin: -4px 0; border-radius: 6px; }
            QSlider::sub-page:horizontal { background: #ff6b35; }
        """)
        self.scrub_slider.valueChanged.connect(self._on_scrub)
        layout.addWidget(self.scrub_slider)

        self._play_timer = QTimer()
        self._play_timer.setInterval(33)
        self._play_timer.timeout.connect(self._advance_frame)
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
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext in self.MEDIA_EXTENSIONS:
                self._load_media(path)
                self._media_path = path
                self.mediaLoaded.emit(path)

    def import_media(self):
        path, _filter = get_open_file_name(
            _("Import Media"), "",
            _("Media Files (*.mp4 *.avi *.mov *.mkv *.webm *.png *.jpg *.jpeg *.gif);;All Files (*)"),
            self
        )
        if path:
            self._media_path = path
            name = os.path.basename(path)
            self.video_label.setText(name)
            self._load_media(path)
            return path
        return None

    def _load_media(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            pix = QPixmap(path)
            if not pix.isNull():
                arr = self._pixmap_to_numpy(pix)
                self.gl_player.set_frame(arr)
                self.video_label.setVisible(False)
                self.gl_player.setVisible(True)
                self._total_frames = 1
                self._fps = 1
                self.scrub_slider.setRange(0, 0)
        elif ext in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"):
            pix = QPixmap(path)
            if not pix.isNull():
                arr = self._pixmap_to_numpy(pix)
                self.gl_player.set_frame(arr)
                self.video_label.setVisible(False)
                self.gl_player.setVisible(True)
        self.time_label.setText(f"00:00:00.000 / 00:00:00.000")
        self.mediaLoaded.emit(path)

    @staticmethod
    def _pixmap_to_numpy(pix):
        qimg = pix.toImage().convertToFormat(4)
        w, h = qimg.width(), qimg.height()
        ptr = qimg.constBits()
        ptr.setsize(h * w * 4)
        import numpy as np
        arr = np.frombuffer(ptr, np.uint8).reshape(h, w, 4)
        return arr[:, :, :3]

    def set_media(self, path):
        self._media_path = path
        name = os.path.basename(path)
        self.video_label.setText(name)
        self._load_media(path)

    def show_crop_overlay(self, visible=True):
        self._crop_overlay.setVisible(visible)
        if visible:
            self._crop_overlay.raise_()
            self._update_crop_overlay_geometry()

    def crop_overlay(self):
        return self._crop_overlay

    def _update_crop_overlay_geometry(self):
        vb = self.gl_player.geometry()
        self._crop_overlay.setGeometry(vb)

    def current_frame(self):
        qimg = self.gl_player.current_frame_qimage()
        if qimg is not None:
            return qimg
        return None

    def set_frame(self, qimage):
        if qimage is None or qimage.isNull():
            return
        h, w = qimage.height(), qimage.width()
        ptr = qimage.constBits()
        ptr.setsize(h * w * 4)
        import numpy as np
        arr = np.frombuffer(ptr, np.uint8).reshape(h, w, 4)
        self.gl_player.set_frame(arr[:, :, :3])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._crop_overlay.isVisible():
            self._update_crop_overlay_geometry()
        self.gl_player.update()

    def toggle_play(self):
        self._playing = not self._playing
        if self._playing:
            self._play_action.setText(_("Pause"))
            self._play_timer.start()
        else:
            self._play_action.setText(_("Play"))
            self._play_timer.stop()

    def toggle_loop(self):
        self._loop = not self._loop
        self._loop_action.setChecked(self._loop)

    def _advance_frame(self):
        if self._total_frames > 1:
            self._current_frame = (self._current_frame + 1) % self._total_frames
            if self._current_frame == 0 and not self._loop:
                self.toggle_play()
            self.scrub_slider.setValue(self._current_frame)
            self._update_time_label()

    def _on_scrub(self, value):
        self._current_frame = value
        self._update_time_label()

    def _update_time_label(self):
        current_s = self._current_frame / self._fps if self._fps else 0
        total_s = self._total_frames / self._fps if self._fps else 0
        self.time_label.setText(
            f"{self._format_time(current_s)} / {self._format_time(total_s)}"
        )

    @staticmethod
    def _format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def set_time(self, seconds):
        frame = int(seconds * self._fps)
        self._current_frame = frame
        self.scrub_slider.setValue(frame)
        self._update_time_label()

    def set_duration(self, seconds):
        self._total_frames = int(seconds * self._fps)
        self.scrub_slider.setRange(0, max(0, self._total_frames - 1))
        self._update_time_label()


class EffectsPanel(QWidget):
    effectSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel(_("Effects")))
        self.search_box = QComboBox()
        self.search_box.setEditable(True)
        self.search_box.setPlaceholderText(_("Search effects..."))
        layout.addWidget(self.search_box)

        self.effects_list = QListWidget()
        self.effects_list.addItems([
            _("Color Correction"), _("Brightness/Contrast"), _("Color Balance"),
            _("HSL Adjust"), _("Curves"), _("Blur/Gaussian"), _("Sharpen"),
            _("Chroma Key"), _("Luma Key"), _("Transform"), _("Crop"), _("Opacity"),
        ])
        self.effects_list.itemClicked.connect(
            lambda item: self.effectSelected.emit(item.text())
        )
        layout.addWidget(self.effects_list, 1)


class ProjectPanel(QWidget):
    mediaImported = object()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        tb = QToolBar()
        self._import_action = tb.addAction(_("Import Media"), self.import_media)
        self._add_to_timeline_action = tb.addAction(_("Add to Timeline"), self.add_to_timeline)
        self._add_to_timeline_action.setEnabled(False)
        layout.addWidget(tb)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Name"), _("Duration"), _("Type")])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(lambda: self.add_to_timeline())
        layout.addWidget(self.tree, 1)

    @property
    def files(self):
        return self._files

    def _on_selection_changed(self):
        selected = self.tree.selectedItems()
        self._add_to_timeline_action.setEnabled(len(selected) > 0)

    def import_media(self):
        paths, _filter = get_open_file_names(
            _("Import Media"), "",
            _("Media Files (*.mp4 *.avi *.mov *.mkv *.webm *.png *.jpg *.jpeg *.gif);;All Files (*)"),
            self
        )
        added = []
        for path in paths:
            if path not in self._files:
                self._files.append(path)
                name = os.path.basename(path)
                ext = os.path.splitext(path)[1].upper().lstrip(".")
                item = QTreeWidgetItem([name, "00:00:00", ext])
                item.setData(0, Qt.UserRole, path)
                self.tree.addTopLevelItem(item)
                added.append(path)
        self.tree.resizeColumnToContents(0)
        if added and self.parent():
            main_win = self.window()
            if hasattr(main_win, 'source_monitor'):
                main_win.source_monitor.set_media(added[0])
            self.status_message = f"{len(added)} file(s) imported"
        return added

    def add_to_timeline(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        main_win = self.window()
        if not hasattr(main_win, 'timeline'):
            return
        for item in selected:
            path = item.data(0, Qt.UserRole)
            name = item.text(0)
            main_win.timeline.add_clip_to_track(name, path)
        if self.status_message:
            main_win.statusBar().showMessage(self.status_message)
            self.status_message = None


class VideoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("reverseaffinity Video - [Untitled]"))
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(800, 500)
        self.setMaximumSize(screen.width(), screen.height())
        self.showMaximized()

        self._play_timer = QTimer()
        self._play_timer.setInterval(33)
        self._play_timer.timeout.connect(self._on_play_tick)
        self._current_time = 0.0
        self._duration = 60.0
        self._playing = False
        self._loop = False
        self._color_params = {}
        self._current_lut = None
        self._chroma_params = {}

        self._setup_menus()
        self._setup_toolbars()
        self._setup_central()
        self._setup_docks()
        self._connect_signals()
        self._color_grading_panel = None
        self.statusBar().showMessage(_("Ready"))
        self.setAcceptDrops(True)

        self._gpu_accel = GPUAccel.get_instance()
        self._gpu_label = QLabel(_("GPU: ") + self._gpu_accel.backend_name)
        self._gpu_label.setStyleSheet("padding: 2px 8px; color: {};".format(
            "#4a4" if self._gpu_accel.is_active else "#888"))
        self.statusBar().addPermanentWidget(self._gpu_label)

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
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            self._import_single_media(path)

    @staticmethod
    def _action(text, slot, shortcut=None):
        a = QAction(text)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        return a

    def _setup_menus(self):
        self.menuBar().setNativeMenuBar(False)
        mbar = self.menuBar()

        file_m = mbar.addMenu(_("&File"))
        file_m.addAction(self._action(_("&New Project"), self.new_project, "Ctrl+N"))
        file_m.addAction(self._action(_("&Open Project..."), self.open_project, "Ctrl+O"))
        file_m.addAction(self._action(_("&Save"), self.save_project, "Ctrl+S"))
        file_m.addAction(self._action(_("Save &As..."), self.save_as, "Ctrl+Shift+S"))
        file_m.addSeparator()
        file_m.addAction(self._action(_("&Import Media..."), self.import_media, "Ctrl+I"))
        file_m.addAction(self._action(_("&Export Media..."), self.export_media, "Ctrl+M"))
        file_m.addSeparator()
        file_m.addAction(self._action(_("E&xit"), self.close, "Ctrl+Q"))

        edit_m = mbar.addMenu(_("&Edit"))
        edit_m.addAction(self._action(_("&Undo"), self.undo, "Ctrl+Z"))
        edit_m.addAction(self._action(_("&Redo"), self.redo, "Ctrl+Shift+Z"))
        edit_m.addSeparator()
        edit_m.addAction(self._action(_("&Cut"), self.cut, "Ctrl+X"))
        edit_m.addAction(self._action(_("&Copy"), self.copy, "Ctrl+C"))
        edit_m.addAction(self._action(_("&Paste"), self.paste, "Ctrl+V"))
        edit_m.addSeparator()
        edit_m.addAction(self._action(_("Select &All"), self.select_all, "Ctrl+A"))

        clip_m = mbar.addMenu(_("&Clip"))
        clip_m.addAction(self._action(_("Split"), self.split_clip, "Ctrl+K"))
        clip_m.addAction(self._action(_("Ripple Delete"), self.ripple_delete, "Shift+Del"))
        clip_m.addAction(_("Add &Transition..."), self.add_transition)
        clip_m.addAction(self._action(_("Speed/Duration..."), self.speed_duration, "Ctrl+R"))
        clip_m.addSeparator()
        clip_m.addAction(self._action(_("Group"), self.group_clips, "Ctrl+G"))
        clip_m.addAction(self._action(_("Ungroup"), self.ungroup_clips, "Ctrl+Shift+G"))

        timeline_m = mbar.addMenu(_("&Timeline"))
        timeline_m.addAction(_("Add Video Track"), self.add_video_track)
        timeline_m.addAction(_("Add Audio Track"), self.add_audio_track)
        timeline_m.addAction(_("Delete Track"), self.delete_track)

        view_m = mbar.addMenu(_("&View"))
        view_m.addAction(self._action(_("Toggle Fullscreen"), self.toggle_fullscreen, "F11"))
        view_m.addAction(self._action(_("Zoom In"), self.zoom_in, "="))
        view_m.addAction(self._action(_("Zoom Out"), self.zoom_out, "-"))
        view_m.addAction(self._action(_("Fit to Window"), self.zoom_fit, "\\"))

    def _setup_toolbars(self):
        main_tb = QToolBar(_("Editing"))
        main_tb.setIconSize(QSize(20, 20))
        main_tb.addAction(self._action(_("Selection"), self.tool_select, "V"))
        main_tb.addAction(self._action(_("Cut"), self.tool_cut, "C"))
        main_tb.addAction(self._action(_("Razor"), self.tool_razor, "R"))
        main_tb.addAction(self._action(_("Hand"), self.tool_hand, "H"))
        main_tb.addAction(self._action(_("Zoom"), self.tool_zoom, "Z"))
        main_tb.addSeparator()
        main_tb.addAction(_("Snap"), self.toggle_snap)
        main_tb.addAction(_("Linked"), self.toggle_linked)
        self.addToolBar(main_tb)

    def _setup_central(self):
        self.timeline = TimelineWidget()
        self.transport = TransportBar()

        monitors = QSplitter(Qt.Horizontal)
        self.source_monitor = SourceMonitor(_("Source"))
        self.program_monitor = SourceMonitor(_("Program"))
        monitors.addWidget(self.source_monitor)
        monitors.addWidget(self.program_monitor)
        monitors.setSizes([400, 400])

        timeline_container = QWidget()
        tl_layout = QVBoxLayout(timeline_container)
        tl_layout.setContentsMargins(0, 0, 0, 0)
        tl_layout.setSpacing(0)
        tl_layout.addWidget(self.transport)
        tl_layout.addWidget(self.timeline, 1)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(monitors)
        splitter.addWidget(timeline_container)
        splitter.setSizes([350, 300])
        self.setCentralWidget(splitter)

    def _setup_docks(self):
        project_dock = QDockWidget(_("Project"), self)
        self.project_panel = ProjectPanel()
        project_dock.setWidget(self.project_panel)
        project_dock.setMinimumWidth(200)
        self.addDockWidget(Qt.LeftDockWidgetArea, project_dock)

        effects_dock = QDockWidget(_("Effects"), self)
        self.effects_panel = EffectsPanel()
        effects_dock.setWidget(self.effects_panel)
        effects_dock.setMinimumWidth(200)
        self.addDockWidget(Qt.RightDockWidgetArea, effects_dock)

        efctrl_dock = QDockWidget(_("Effect Controls"), self)
        self._efctrl_dock = efctrl_dock
        self._efctrl_label = QLabel(_("Select an effect from the Effects panel"))
        self._efctrl_label.setAlignment(Qt.AlignCenter)
        self._efctrl_label.setWordWrap(True)
        self._efctrl_label.setStyleSheet("color: #666; padding: 20px;")
        efctrl_dock.setWidget(self._efctrl_label)
        efctrl_dock.setMinimumWidth(200)
        self.addDockWidget(Qt.RightDockWidgetArea, efctrl_dock)

        scopes_dock = QDockWidget(_("Scopes"), self)
        self.scopes_panel = ScopesPanel()
        scopes_dock.setWidget(self.scopes_panel)
        scopes_dock.setMinimumWidth(180)
        scopes_dock.setMinimumHeight(180)
        self.addDockWidget(Qt.RightDockWidgetArea, scopes_dock)

        mixer_dock = QDockWidget(_("Audio Mixer"), self)
        self._audio_mixer = AudioMixerPanel()
        mixer_dock.setWidget(self._audio_mixer)
        mixer_dock.setMinimumWidth(220)
        self.addDockWidget(Qt.RightDockWidgetArea, mixer_dock)

    def _connect_signals(self):
        self.transport.playToggled.connect(self._on_transport_play)
        self.transport.stopTriggered.connect(self._on_transport_stop)
        self.transport.goToStart.connect(self.go_start)
        self.transport.goToEnd.connect(self.go_end)
        self.transport.stepForward.connect(self.next_frame)
        self.transport.stepBackward.connect(self.prev_frame)
        self.transport.zoomChanged.connect(self.timeline.set_zoom_level)
        self.effects_panel.effectSelected.connect(self._on_effect_selected)
        self.timeline.dropAccepted.connect(lambda name: self.statusBar().showMessage(_("Added to timeline: ") + name, 2000))
        self.program_monitor.mediaLoaded.connect(lambda _: self._update_scopes())
        self.source_monitor.mediaLoaded.connect(lambda _: self._update_scopes())

    def _on_transport_play(self, playing):
        if playing:
            self.toggle_play()
        else:
            self._stop_playback()

    def _on_transport_stop(self):
        self._stop_playback()
        self.go_start()

    def _on_play_tick(self):
        self._current_time += 1.0 / 30.0
        if self._current_time >= self._duration:
            if self._loop:
                self._current_time = 0.0
            else:
                self._stop_playback()
                return
        self.program_monitor.set_time(self._current_time)
        self.transport.set_current_time(self._current_time)
        self.timeline.set_current_time(self._current_time)

    def _stop_playback(self):
        self._playing = False
        self._play_timer.stop()
        self.transport.set_playing(False)

    def _start_playback(self):
        self._playing = True
        self._play_timer.start()
        self.transport.set_playing(True)

    # --- Menu actions ---
    def import_media(self):
        self.project_panel.import_media()

    def _import_single_media(self, path):
        if path not in self.project_panel._files:
            self.project_panel._files.append(path)
            name = os.path.basename(path)
            ext = os.path.splitext(path)[1].upper().lstrip(".")
            item = QTreeWidgetItem([name, "00:00:00", ext])
            item.setData(0, Qt.UserRole, path)
            self.project_panel.tree.addTopLevelItem(item)
            self.project_panel.tree.resizeColumnToContents(0)
            self.source_monitor.set_media(path)
            self.statusBar().showMessage(_("Imported: ") + name, 2000)

    def new_project(self):
        self.timeline.clear()
        self._current_time = 0.0
        self._duration = 60.0
        self.transport.set_current_time(0)
        self.transport.set_duration(self._duration)
        self.program_monitor.set_duration(self._duration)
        self.statusBar().showMessage(_("New project created"))

    def open_project(self):
        path, _filter = get_open_file_name(_("Open Project"), "", _("Project Files (*.revideo *.json);;All Files (*)"), self)
        if path:
            self.statusBar().showMessage(_("Project loaded: ") + os.path.basename(path))

    def save_project(self):
        path, _filter = get_save_file_name(_("Save Project"), "", _("Project Files (*.revideo);;All Files (*)"), self)
        if path:
            self.statusBar().showMessage(_("Project saved"))

    def save_as(self):
        self.save_project()

    def export_media(self):
        dlg = ExportDialog(self.timeline, self)
        dlg.exec_()

    def undo(self):
        self.statusBar().showMessage(_("Undo"), 2000)

    def redo(self):
        self.statusBar().showMessage(_("Redo"), 2000)

    def cut(self):
        self.statusBar().showMessage(_("Cut"), 2000)

    def copy(self):
        self.statusBar().showMessage(_("Copy"), 2000)

    def paste(self):
        self.statusBar().showMessage(_("Paste"), 2000)

    def select_all(self):
        self.statusBar().showMessage(_("Select All"), 2000)

    def split_clip(self):
        self.statusBar().showMessage(_("Clip split"), 2000)

    def ripple_delete(self):
        self.statusBar().showMessage(_("Ripple delete"), 2000)

    def add_transition(self):
        self.statusBar().showMessage(_("Transition dialog"), 2000)

    def speed_duration(self):
        self.statusBar().showMessage(_("Speed/Duration dialog"), 2000)

    def group_clips(self):
        self.statusBar().showMessage(_("Clips grouped"), 2000)

    def ungroup_clips(self):
        self.statusBar().showMessage(_("Clips ungrouped"), 2000)

    def add_video_track(self):
        idx = self.timeline.add_track()
        self.statusBar().showMessage(_("Video track added"))

    def add_audio_track(self):
        idx = self.timeline.add_track(is_audio=True)
        name = _("Audio {}").format(idx + 1)
        self._audio_mixer.add_track(idx, name)
        self.statusBar().showMessage(_("Audio track added"))

    def delete_track(self):
        self.timeline.remove_track()
        self._audio_mixer.remove_track(0)
        self.statusBar().showMessage(_("Track deleted"))

    def toggle_fullscreen(self):
        self.showFullScreen() if not self.isFullScreen() else self.showNormal()

    def zoom_in(self):
        self.timeline.zoom_in()

    def zoom_out(self):
        self.timeline.zoom_out()

    def zoom_fit(self):
        self.timeline.zoom_fit()

    def tool_select(self):
        self.statusBar().showMessage(_("Selection tool active"))

    def tool_cut(self):
        self.statusBar().showMessage(_("Cut tool active"))

    def tool_razor(self):
        self.statusBar().showMessage(_("Razor tool active"))

    def tool_hand(self):
        self.statusBar().showMessage(_("Hand tool active"))

    def tool_zoom(self):
        self.statusBar().showMessage(_("Zoom tool active"))

    def toggle_snap(self):
        self.timeline.toggle_snap()
        self.statusBar().showMessage(_("Snap ") + (_("on") if self.timeline.snap_enabled else _("off")))

    def toggle_linked(self):
        pass

    def _on_effect_selected(self, effect_name):
        normalized = effect_name.lower().replace(" ", "_").replace("/", "_")
        if normalized in ("color_correction", "brightness_contrast", "color_balance", "hsl_adjust", "curves"):
            self._show_color_grading()
            self.statusBar().showMessage(_("Color grading: ") + effect_name)
        elif normalized == "chroma_key":
            self._show_chroma_key()
        elif normalized == "luma_key":
            self._show_chroma_key()
            self._chroma_key_widget._key_label.setText(_("Key: Luma"))
            self.statusBar().showMessage(_("Luma Key activated"))
        elif normalized in ("blur_gaussian", "sharpen"):
            self._show_blur_sharpen()
        elif normalized == "crop":
            self._show_crop_tool()
        else:
            self.statusBar().showMessage(_("Effect selected: ") + effect_name)

    def _show_color_grading(self):
        if self._color_grading_panel is None:
            container = QWidget()
            cl = QVBoxLayout(container)
            cl.setContentsMargins(0, 0, 0, 0)

            self._color_grading_panel = ColorGradingPanel()
            self._color_grading_panel.paramsChanged.connect(self._on_color_params_changed)
            cl.addWidget(self._color_grading_panel)

            self._lut_panel = LutPanel()
            self._lut_panel.lutChanged.connect(self._on_lut_changed)
            cl.addWidget(self._lut_panel)

            self._cg_container = container

        self._efctrl_dock.setWidget(self._cg_container)
        self._efctrl_dock.setWindowTitle(_("Color Grading"))

    def _on_lut_changed(self, lut_data):
        self._current_lut = lut_data
        if self.program_monitor.current_frame() is not None:
            self._apply_color_to_preview()

    def _on_color_params_changed(self, params):
        self._color_params = params
        if self.program_monitor.current_frame() is not None:
            self._apply_color_to_preview()

    def _apply_color_to_preview(self):
        img = self.program_monitor.current_frame()
        if img is None:
            return
        graded = self._color_grading_panel.apply_to_image(img)
        if self._current_lut:
            graded = apply_lut(graded, self._current_lut)
        self.program_monitor.set_frame(graded)

    def _update_scopes(self):
        img = self.program_monitor.current_frame()
        if img is not None:
            self.scopes_panel.set_image(img)

    def _show_crop_tool(self):
        self.program_monitor.show_crop_overlay(True)
        overlay = self.program_monitor.crop_overlay()
        if not hasattr(self, '_crop_control_panel') or self._crop_control_panel is None:
            self._crop_control_panel = CropControlPanel()
            overlay.cropChanged.connect(
                lambda r: self._crop_control_panel.update_from_rect(
                    r, self.program_monitor._video_container.width(),
                    self.program_monitor._video_container.height()
                )
            )
            self._crop_control_panel.cropApplied.connect(self._apply_crop)
        self._efctrl_dock.setWidget(self._crop_control_panel)
        self._efctrl_dock.setWindowTitle(_("Crop"))
        self.statusBar().showMessage(_("Crop tool active"))

    def _apply_crop(self, left, top, right, bottom):
        self.program_monitor.show_crop_overlay(False)
        img = self.program_monitor.current_frame()
        if img is not None:
            w, h = img.width(), img.height()
            crop_x = left
            crop_y = top
            crop_w = w - left - right
            crop_h = h - top - bottom
            if crop_w > 0 and crop_h > 0:
                cropped = img.copy(crop_x, crop_y, crop_w, crop_h)
                self.program_monitor.set_frame(cropped)
                self._update_scopes()
                self.statusBar().showMessage(_("Crop applied"))

    def _show_chroma_key(self):
        if not hasattr(self, '_chroma_key_widget') or self._chroma_key_widget is None:
            self._chroma_key_widget = ChromaKeyWidget()
            self._chroma_key_widget.paramsChanged.connect(self._on_chroma_params_changed)
        self._efctrl_dock.setWidget(self._chroma_key_widget)
        self._efctrl_dock.setWindowTitle(_("Chroma Key"))
        if self.program_monitor.current_frame() is not None:
            self._on_chroma_params_changed(self._chroma_key_widget.params())

    def _on_chroma_params_changed(self, params):
        self._chroma_params = params
        img = self.program_monitor.current_frame()
        if img is None:
            return
        keyed = self._chroma_key_widget.apply_to_image(img)
        self.program_monitor.set_frame(keyed)
        self._update_scopes()

    def _show_blur_sharpen(self):
        if not hasattr(self, '_blur_sharpen_widget') or self._blur_sharpen_widget is None:
            self._blur_sharpen_widget = BlurSharpenWidget()
            self._blur_sharpen_widget.paramsChanged.connect(self._on_blur_sharpen_changed)
        self._efctrl_dock.setWidget(self._blur_sharpen_widget)
        self._efctrl_dock.setWindowTitle(_("Blur / Sharpen"))
        if self.program_monitor.current_frame() is not None:
            self._on_blur_sharpen_changed({"mode": "blur", "amount": 3})

    def _on_blur_sharpen_changed(self, params):
        img = self.program_monitor.current_frame()
        if img is None:
            return
        result = self._blur_sharpen_widget.apply_to_image(img)
        self.program_monitor.set_frame(result)
        self._update_scopes()

    def go_start(self):
        self._current_time = 0.0
        self.program_monitor.set_time(0)
        self.transport.set_current_time(0)
        self.timeline.set_current_time(0)

    def go_end(self):
        self._current_time = self._duration
        self.program_monitor.set_time(self._duration)
        self.transport.set_current_time(self._duration)
        self.timeline.set_current_time(self._duration)

    def prev_frame(self):
        self._current_time = max(0, self._current_time - 1.0 / 30.0)
        self.program_monitor.set_time(self._current_time)
        self.transport.set_current_time(self._current_time)

    def next_frame(self):
        self._current_time = min(self._duration, self._current_time + 1.0 / 30.0)
        self.program_monitor.set_time(self._current_time)
        self.transport.set_current_time(self._current_time)

    def toggle_play(self):
        if self._playing:
            self._stop_playback()
        else:
            self._start_playback()

    def toggle_loop(self):
        self._loop = not self._loop


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("reverseaffinity Video")
    win = VideoMainWindow()
    win.show()
    if QApplication.instance() is app:
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
