from collections import deque
import copy
import time
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QImage
from .layers import Layer


_THUMB_CACHE = {}
_THUMB_CACHE_MAX = 20


def _get_cached_thumbnail(composite_img, key):
    if key in _THUMB_CACHE:
        return _THUMB_CACHE[key]
    if len(_THUMB_CACHE) >= _THUMB_CACHE_MAX:
        _THUMB_CACHE.pop(next(iter(_THUMB_CACHE)))
    pix = QPixmap.fromImage(composite_img).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    _THUMB_CACHE[key] = pix
    return pix


class HistoryEntry:
    def __init__(self, description, snapshot, active_index, composite_img=None):
        self.description = description
        self.snapshot = snapshot
        self.active_index = active_index
        self.timestamp = time.time()
        self._thumbnail = None
        self._composite_key = None
        if composite_img is not None:
            w, h = composite_img.width(), composite_img.height()
            self.image_dimensions = (w, h)
            self._composite_key = id(composite_img)
            self._composite_img = composite_img
        else:
            self.image_dimensions = (0, 0)
            self._composite_key = None
            self._composite_img = None

    def get_thumbnail(self):
        if self._thumbnail is not None:
            return self._thumbnail
        if self._composite_key is not None and self._composite_img is not None:
            self._thumbnail = _get_cached_thumbnail(self._composite_img, self._composite_key)
            return self._thumbnail
        return None

    def has_snapshot(self):
        return self.snapshot is not None


class HistoryManager(QObject):
    history_changed = pyqtSignal()

    def __init__(self, max_states=50):
        super().__init__()
        self.max_states = max_states
        self.stack = deque(maxlen=max_states)
        self.index = -1

    def push(self, description, layers, active_index):
        composite_img = None
        if layers:
            try:
                from .layers import LayerStack
                temp = LayerStack(1, 1)
                temp.layers = list(layers)
                composite_img = temp.composite()
            except Exception:
                composite_img = None

        snap = [
            (l.name, l.image.copy(), l.visible, l.locked, l.opacity, l.blend_mode,
             l.fill, l.mask.copy() if l.mask else None, l.mask_enabled, l.mask_linked)
            for l in layers if hasattr(l, 'image')
        ]
        entry = HistoryEntry(description, snap, active_index, composite_img)

        while self.index < len(self.stack) - 1:
            self.stack.pop()
        self.stack.append(entry)
        self.index = len(self.stack) - 1

        self._enforce_limits()
        self.history_changed.emit()

    def _enforce_limits(self):
        while len(self.stack) > self.max_states:
            self.stack.popleft()
            self.index -= 1

    def _restore(self, layer_stack):
        entry = self.stack[self.index]
        if entry.snapshot is None:
            return False
        layer_stack.layers.clear()
        for data in entry.snapshot:
            name, img, vis, locked, opacity, blend = data[:6]
            l = Layer(img.width(), img.height(), name)
            l.image = img
            l.visible = vis
            l.locked = locked
            l.opacity = opacity
            l.blend_mode = blend
            if len(data) > 6:
                l.fill = data[6]
                l.mask = data[7].copy() if data[7] else None
                l.mask_enabled = data[8]
                l.mask_linked = data[9]
            layer_stack.layers.append(l)
        layer_stack.active_index = entry.active_index
        return True

    def undo(self, layer_stack):
        if self.index <= 0:
            return False
        self.index -= 1
        ok = self._restore(layer_stack)
        self.history_changed.emit()
        return ok

    def redo(self, layer_stack):
        if self.index >= len(self.stack) - 1:
            return False
        self.index += 1
        ok = self._restore(layer_stack)
        self.history_changed.emit()
        return ok

    def jump_to(self, layer_stack, index):
        if 0 <= index < len(self.stack):
            self.index = index
            ok = self._restore(layer_stack)
            self.history_changed.emit()
            return ok
        return False

    def can_undo(self):
        return self.index > 0

    def can_redo(self):
        return self.index < len(self.stack) - 1

    def clear(self):
        self.stack.clear()
        self.index = -1
        self.history_changed.emit()

    def delete_entry(self, index):
        if 0 <= index < len(self.stack) and len(self.stack) > 1:
            del self.stack[index]
            if self.index >= len(self.stack):
                self.index = len(self.stack) - 1
            self.history_changed.emit()
            return True
        return False

    def set_description(self, index, desc):
        if 0 <= index < len(self.stack):
            self.stack[index].description = desc
            self.history_changed.emit()
            return True
        return False
