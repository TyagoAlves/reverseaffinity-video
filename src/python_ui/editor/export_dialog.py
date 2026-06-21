import os
import subprocess
import threading
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QSpinBox, QPushButton, QProgressBar, QGroupBox,
    QCheckBox, QFileDialog, QMessageBox, QLineEdit, QWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal
from editor.i18n import _


PRESETS = {
    "H.264 (MP4)": {
        "ext": ".mp4",
        "codec": "libx264",
        "crf": 23,
        "preset": "medium",
        "pixel_fmt": "yuv420p",
    },
    "H.265 (MP4)": {
        "ext": ".mp4",
        "codec": "libx265",
        "crf": 28,
        "preset": "medium",
        "pixel_fmt": "yuv420p",
    },
    "ProRes (MOV)": {
        "ext": ".mov",
        "codec": "prores_ks",
        "profile": "standard",
        "pixel_fmt": "yuv422p10le",
    },
    "DNxHD (MOV)": {
        "ext": ".mov",
        "codec": "dnxhd",
        "b": "36M",
        "pixel_fmt": "yuv422p",
    },
    "GIF": {
        "ext": ".gif",
        "codec": "gif",
        "palette": True,
    },
    "PNG Sequence": {
        "ext": ".png",
        "codec": "png",
        "image_seq": True,
    },
    "JPEG Sequence": {
        "ext": ".jpg",
        "codec": "mjpeg",
        "qscale": 2,
        "image_seq": True,
    },
    "WebP": {
        "ext": ".webp",
        "codec": "libwebp",
        "crf": 30,
        "pixel_fmt": "yuv420p",
    },
    "VP9 (WebM)": {
        "ext": ".webm",
        "codec": "libvpx-vp9",
        "crf": 30,
        "b": "0",
        "pixel_fmt": "yuv420p",
    },
}


class ExportDialog(QDialog):
    def __init__(self, timeline, parent=None):
        super().__init__(parent)
        self._timeline = timeline
        self._ffmpeg_path = self._find_ffmpeg()
        self._process = None
        self._cancelled = False
        self.setWindowTitle(_("Export Media"))
        self.setMinimumWidth(500)
        self._build_ui()

    def _find_ffmpeg(self):
        for name in ("ffmpeg", "ffmpeg.exe"):
            try:
                r = subprocess.run([name, "-version"], capture_output=True, timeout=5)
                if r.returncode == 0:
                    return name
            except Exception:
                pass
        return None

    def _build_ui(self):
        layout = QVBoxLayout(self)

        if not self._ffmpeg_path:
            warn = QLabel(_("ffmpeg not found. Install ffmpeg to enable export."))
            warn.setStyleSheet("color: #ff8844; padding: 8px;")
            layout.addWidget(warn)

        preset_group = QGroupBox(_("Preset"))
        pg = QFormLayout(preset_group)
        self._preset_combo = QComboBox()
        for name in PRESETS:
            self._preset_combo.addItem(name)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        pg.addRow(_("Format:"), self._preset_combo)

        self._ext_label = QLabel(".mp4")
        pg.addRow(_("Extension:"), self._ext_label)
        layout.addWidget(preset_group)

        video_group = QGroupBox(_("Video Settings"))
        vg = QFormLayout(video_group)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(64, 8192)
        self._width_spin.setValue(1920)
        self._width_spin.setSingleStep(2)
        vg.addRow(_("Width:"), self._width_spin)

        self._height_spin = QSpinBox()
        self._height_spin.setRange(64, 8192)
        self._height_spin.setValue(1080)
        self._height_spin.setSingleStep(2)
        vg.addRow(_("Height:"), self._height_spin)

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 120)
        self._fps_spin.setValue(30)
        vg.addRow(_("FPS:"), self._fps_spin)

        self._crf_spin = QSpinBox()
        self._crf_spin.setRange(0, 63)
        self._crf_spin.setValue(23)
        vg.addRow(_("CRF (quality):"), self._crf_spin)

        self._faststart_cb = QCheckBox(_("Fast start (web optimized)"))
        self._faststart_cb.setChecked(True)
        vg.addRow(self._faststart_cb)
        layout.addWidget(video_group)

        audio_group = QGroupBox(_("Audio Settings"))
        ag = QFormLayout(audio_group)
        self._audio_cb = QCheckBox(_("Include audio"))
        self._audio_cb.setChecked(True)
        ag.addRow(self._audio_cb)

        self._audio_bitrate = QComboBox()
        self._audio_bitrate.addItems(["128k", "192k", "256k", "320k"])
        self._audio_bitrate.setCurrentText("192k")
        ag.addRow(_("Audio bitrate:"), self._audio_bitrate)
        layout.addWidget(audio_group)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        btn_row = QHBoxLayout()
        self._export_btn = QPushButton(_("Export"))
        self._export_btn.clicked.connect(self._start_export)
        self._cancel_btn = QPushButton(_("Cancel"))
        self._cancel_btn.clicked.connect(self._cancel)
        btn_row.addStretch()
        btn_row.addWidget(self._export_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        self._on_preset_changed(0)

    def _on_preset_changed(self, idx):
        name = self._preset_combo.currentText()
        preset = PRESETS.get(name, {})
        self._ext_label.setText(preset.get("ext", ".mp4"))
        has_crf = "crf" in preset
        self._crf_spin.setVisible(has_crf)
        self._crf_spin.setValue(preset.get("crf", 23))
        label = self.findChild(QLabel, "", Qt.FindChildrenRecursively)
        for w in self.findChildren(QWidget):
            if isinstance(w, QLabel) and w.text() == _("CRF (quality):"):
                w.setVisible(has_crf)

    def _start_export(self):
        if not self._ffmpeg_path:
            QMessageBox.warning(self, _("Export"),
                                _("ffmpeg not found. Please install ffmpeg:\n"
                                  "  sudo apt install ffmpeg  # Debian/Ubuntu\n"
                                  "  sudo dnf install ffmpeg  # Fedora"))
            return

        path, _filter = QFileDialog.getSaveFileName(
            self, _("Save Export As"), "",
            _("Media Files (*{});;All Files (*)").format(self._ext_label.text())
        )
        if not path:
            return

        self._export_btn.setEnabled(False)
        self._cancel_btn.setText(_("Cancel"))
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._cancelled = False

        preset_name = self._preset_combo.currentText()
        preset = PRESETS.get(preset_name, {})
        w = self._width_spin.value()
        h = self._height_spin.value()
        fps = self._fps_spin.value()

        dur = self._timeline._timeline.duration() if self._timeline and hasattr(self._timeline, '_timeline') else 0.0

        cmd = [self._ffmpeg_path, "-y"]
        if dur > 0:
            cmd.extend(["-t", str(dur)])

        cmd.extend([
            "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={fps}:d={max(dur, 1)}",
            "-vf", f"drawtext=text='Export Preview':fontsize=24:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        ])

        ext = preset.get("ext", ".mp4")
        if not path.lower().endswith(ext):
            path += ext

        if preset.get("image_seq"):
            base, _ = os.path.splitext(path)
            os.makedirs(base + "_frames", exist_ok=True)
            path = os.path.join(base + "_frames", f"frame_%05d{ext}")

        cmd.extend(["-c:v", preset.get("codec", "libx264")])
        if "crf" in preset:
            cmd.extend(["-crf", str(self._crf_spin.value())])
        if "preset" in preset:
            cmd.extend(["-preset", preset["preset"]])
        if "b" in preset:
            cmd.extend(["-b:v", preset["b"]])
        if "qscale" in preset:
            cmd.extend(["-qscale:v", str(preset["qscale"])])
        if "profile" in preset:
            cmd.extend(["-profile:v", preset["profile"]])
        if "pixel_fmt" in preset:
            cmd.extend(["-pixel_format", preset["pixel_fmt"]])

        if not preset.get("image_seq") and self._faststart_cb.isChecked():
            cmd.extend(["-movflags", "+faststart"])

        if self._audio_cb.isChecked() and not preset.get("image_seq"):
            cmd.extend(["-c:a", "aac", "-b:a", self._audio_bitrate.currentText()])

        cmd.append(path)

        thread = threading.Thread(target=self._run_ffmpeg, args=(cmd, path), daemon=True)
        thread.start()

    def _run_ffmpeg(self, cmd, path):
        try:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True
            )
            for line in self._process.stderr:
                if self._cancelled:
                    self._process.terminate()
                    break
                if "time=" in line:
                    try:
                        ts = line.split("time=")[1].split()[0]
                        parts = ts.split(":")
                        secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        dur = self._timeline._timeline.duration() if self._timeline else 60
                        pct = min(100, int(secs / max(dur, 1) * 100))
                        self._progress.setValue(pct)
                    except Exception:
                        pass
            self._process.wait()
            if self._process.returncode == 0 and not self._cancelled:
                self._progress.setValue(100)
                self._on_export_finished(path)
            elif self._cancelled:
                self._on_export_cancelled()
            else:
                self._on_export_error(self._process.stderr.read())
        except Exception as e:
            self._on_export_error(str(e))

    def _on_export_finished(self, path):
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, _("Export Complete"),
                                _("File exported successfully:\n{}").format(path))
        self._export_btn.setEnabled(True)
        self._progress.setVisible(False)
        self.accept()

    def _on_export_error(self, msg):
        QMessageBox.warning(self, _("Export Error"),
                            _("Export failed:\n{}").format(msg[:500]))
        self._export_btn.setEnabled(True)
        self._progress.setVisible(False)

    def _on_export_cancelled(self):
        self._progress.setVisible(False)
        self._export_btn.setEnabled(True)
        self._cancel_btn.setText(_("Close"))

    def _cancel(self):
        if self._process and self._process.poll() is None:
            self._cancelled = True
            self._process.terminate()
        else:
            self.reject()
