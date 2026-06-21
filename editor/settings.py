import json
import os
import tempfile

from PyQt5.QtCore import QObject, pyqtSignal, QStandardPaths


DEFAULT_SETTINGS = {
    'default_width': 800,
    'default_height': 600,
    'default_bg_color': '#ffffff',
    'default_tool_size': 3,
    'default_tool_opacity': 100,
    'units': 'px',
    'language': 'system',
    'auto_save_interval': 0,
    'grid_color': '#808080',
    'grid_spacing': 50,
    'grid_style': 'Lines',
    'guide_color': '#4a8ac4',
    'snap_threshold': 5,
    'undo_levels': 100,
    'cache_size_mb': 512,
    'use_opengl': False,
    'live_preview': True,
    'theme': 'Dark',
    'font_size': 12,
    'canvas_bg': 'Checkered',
    'checkered_size': 'Medium',
    'default_save_format': 'png',
    'jpeg_quality': 95,
    'png_compression': 6,
    'include_layers': False,
    'recent_files': [],
}


class SettingsManager(QObject):
    setting_changed = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = dict(DEFAULT_SETTINGS)
        config_dir = QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
        self._config_dir = os.path.join(config_dir, 'reverseaffinity')
        self._settings_path = os.path.join(self._config_dir, 'settings.json')

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        old = self._settings.get(key)
        if old != value:
            self._settings[key] = value
            self.setting_changed.emit(key, value)

    def load(self):
        try:
            os.makedirs(self._config_dir, exist_ok=True)
            with open(self._settings_path, 'r') as f:
                data = json.load(f)
            for k, v in data.items():
                if k in DEFAULT_SETTINGS:
                    self._settings[k] = v
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save(self):
        os.makedirs(self._config_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self._config_dir, suffix='.json')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(self._settings, f, indent=2)
            os.replace(tmp_path, self._settings_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def reset(self):
        old = dict(self._settings)
        self._settings = dict(DEFAULT_SETTINGS)
        for k, v in DEFAULT_SETTINGS.items():
            if old.get(k) != v:
                self.setting_changed.emit(k, v)

    def all_settings(self):
        return dict(self._settings)

    def update_recent_files(self, path):
        recent = self._settings.get('recent_files', [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._settings['recent_files'] = recent[:10]
        self.save()
