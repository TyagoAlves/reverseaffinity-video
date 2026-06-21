import os
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QRect, QTimer, QUrl
from PyQt5.QtGui import (
    QPainter, QPixmap, QPen, QColor, QImage, QBrush,
    QTransform, QPolygonF, QFont, QFontMetrics, QBitmap, QRegion,
    QPainterPath, QCursor,
)
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
import math
from collections import deque
import numpy as np

from .layers import LayerStack, Layer
from .history import HistoryManager
from .tools import SHORTCUT_MAP, PencilTool
from .guides import GuideManager
from .snapping import SnappingEngine
from .settings import SettingsManager
from .file_formats import FORMAT_REGISTRY, get_format_for_filename
from .path import Path


class CanvasView(QGraphicsView):
    mouse_moved = pyqtSignal(float, float)
    color_picked = pyqtSignal(QColor)
    bg_color_changed = pyqtSignal(QColor)
    status_changed = pyqtSignal(str)
    zoom_changed = pyqtSignal(float)
    history_changed = pyqtSignal()
    tool_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.layer_stack = LayerStack(800, 600)
        self.history = HistoryManager()
        self.history.history_changed.connect(self.history_changed.emit)
        self.history.push("New document", self.layer_stack.layers, self.layer_stack.active_index)

        self.zoom_level = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.tool = PencilTool()
        self.setCursor(getattr(self.tool, 'cursor', QCursor(Qt.ArrowCursor)))
        self.tool_size = 3
        self.tool_color = QColor(0, 0, 0)
        self.tool_opacity = 1.0
        self.tool_flow = 1.0
        self.bg_color = QColor(255, 255, 255)
        self.drawing = False
        self.dragging_layer = False
        self.last_point = None
        self.selection_start = None
        self.selection = None
        self.rubber_band_start = None
        self.rubber_band_end = None
        self.has_rubber_band = False
        self.lasso_points = []
        self.has_lasso = False
        self.gradient_start = None
        self.shape_start = None
        self.clone_source = None

        self.selection_mask = None
        self.selection_path = None
        self.selection_phase = 0
        self.selection_timer = QTimer()
        self.selection_timer.timeout.connect(self._march_selection)
        self.selection_timer.start(120)
        self.guide_mgr = GuideManager()
        self.snapping = SnappingEngine()
        self._settings = SettingsManager()

        self.pen_path = []
        self.pen_handle_offsets = []
        self.vector_paths = []
        self.selected_path_idx = -1
        self.edit_anchor_idx = -1
        self.edit_handle = None
        self.ruler_dragging_guide = False
        self.dragging_guide_index = -1
        self.ruler_drag_orientation = None
        self.ruler_drag_pos = None
        self.crop_active = False
        self.crop_start = None
        self.crop_end = None
        self.crop_drag_handle = None
        self._plugin_filters = {}

        self.show_grid = False
        self.show_rulers = True
        self.snap_indicator = None

        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setAcceptDrops(True)

        self.tool_changed.emit(self.tool.name)
        self._refresh()

    def _refresh(self):
        composite = self.layer_stack.composite()
        self.pixmap_item.setPixmap(QPixmap.fromImage(composite))
        self.scene.setSceneRect(QRectF(composite.rect()))
        self.viewport().update()

    def temp_save_layer(self):
        layer = self.layer_stack.active
        if layer:
            self._temp_layer_image = layer.image.copy()

    def temp_restore_layer(self):
        if hasattr(self, '_temp_layer_image') and self._temp_layer_image:
            layer = self.layer_stack.active
            if layer:
                layer.image = self._temp_layer_image.copy()
                self._refresh()

    def _save_state(self, desc="Edit"):
        self.history.push(desc, self.layer_stack.layers, self.layer_stack.active_index)

    def new_image(self, width, height, bg=None):
        if bg is None:
            bg = QColor(Qt.white)
        self.layer_stack = LayerStack(width, height)
        if bg != Qt.white:
            self.layer_stack.layers[0].image.fill(bg)
        self.history.clear()
        self.history.push("New document", self.layer_stack.layers, self.layer_stack.active_index)
        self._refresh()
        self.zoom_fit()

    def open_image(self, path):
        if not path:
            return False
        try:
            ext = get_format_for_filename(path)
            fmt = FORMAT_REGISTRY.get(ext)
            if fmt and fmt.get('importer'):
                layer_stack = fmt['importer'](path)
                if layer_stack and layer_stack.layers:
                    self.layer_stack = layer_stack
                    w = self.layer_stack.layers[0].image.width()
                    h = self.layer_stack.layers[0].image.height()
                    self.history.clear()
                    self.history.push(f"Open {path}", self.layer_stack.layers, self.layer_stack.active_index)
                    self._refresh()
                    self.zoom_fit()
                    return True
            img = QImage(path)
            if img.isNull():
                return False
            if img.format() != QImage.Format_ARGB32:
                img = img.convertToFormat(QImage.Format_ARGB32)
            w, h = img.width(), img.height()
            self.layer_stack = LayerStack(w, h)
            self.layer_stack.layers[0].image = img.copy()
            self.history.clear()
            self.history.push(f"Open {path}", self.layer_stack.layers, self.layer_stack.active_index)
            self._refresh()
            self.zoom_fit()
            return True
        except Exception:
            return False

    def save_image(self, path, opts=None):
        if not path:
            return False
        try:
            ext = get_format_for_filename(path)
            fmt = FORMAT_REGISTRY.get(ext)
            if fmt and fmt.get('exporter'):
                return fmt['exporter'](self.layer_stack, path, opts)
            composite = self.layer_stack.composite()
            return composite.save(path)
        except Exception:
            return False

    def import_image_as_layer(self, path):
        if not path:
            return None
        try:
            img = QImage(path)
            if img.isNull():
                return None
            if img.format() != QImage.Format_ARGB32:
                img = img.convertToFormat(QImage.Format_ARGB32)
            name = os.path.splitext(os.path.basename(path))[0]
            w, h = self.layer_stack.layers[0].image.width(), self.layer_stack.layers[0].image.height()
            if img.width() != w or img.height() != h:
                img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            layer = Layer(w, h, name, Qt.transparent)
            layer.image = img.copy()
            self.layer_stack.layers.append(layer)
            self.layer_stack.active_index = len(self.layer_stack.layers) - 1
            self._save_state(f"Place {name}")
            self._refresh()
            return layer
        except Exception:
            return None

    def export_png(self, path):
        if not path:
            return False
        try:
            return self.layer_stack.composite().save(path, "PNG")
        except Exception:
            return False

    def export_jpg(self, path, quality=95):
        if not path:
            return False
        try:
            return self.layer_stack.composite().save(path, "JPEG", quality)
        except Exception:
            return False

    def set_tool(self, tool_name):
        from .tools import TOOLS_BY_NAME
        cls = TOOLS_BY_NAME.get(tool_name.lower())
        if cls:
            self.tool = cls()
            self.setCursor(getattr(self.tool, 'cursor', QCursor(Qt.ArrowCursor)))
            self.tool_changed.emit(self.tool.name)

    def set_tool_size(self, size):
        self.tool_size = max(1, size)

    def set_tool_opacity(self, val):
        self.tool_opacity = val / 100.0

    def set_tool_flow(self, val):
        self.tool_flow = val / 100.0

    def set_foreground_color(self, color):
        self.tool_color = color
        self.color_picked.emit(color)

    def set_background_color(self, color):
        self.bg_color = color
        self.bg_color_changed.emit(color)

    def set_drag_mode(self, mode):
        """0=NoDrag, 1=ScrollHandDrag"""
        self.setDragMode(
            QGraphicsView.ScrollHandDrag if mode == 1 else QGraphicsView.NoDrag
        )
        self.dragging_layer = False

    def zoom_in(self):
        self.zoom_level *= 1.25
        self._apply_zoom()

    def zoom_out(self):
        self.zoom_level /= 1.25
        self._apply_zoom()

    def zoom_fit(self):
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.zoom_level = self.transform().m11()
        self.zoom_changed.emit(self.zoom_level)

    def zoom_100(self):
        self.zoom_level = 1.0
        self._apply_zoom()

    def zoom_to_selection(self):
        if not self.has_selection():
            return
        rect = self.selection_path.boundingRect()
        if rect.isEmpty():
            return
        margin = 20
        rect.adjust(-margin, -margin, margin, margin)
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.zoom_level = self.transform().m11()
        self.zoom_changed.emit(self.zoom_level)

    def _apply_zoom(self):
        self.resetTransform()
        self.scale(self.zoom_level, self.zoom_level)
        self.zoom_changed.emit(self.zoom_level)

    def update_pixmap_position(self):
        pos = self.pixmap_item.pos()
        self.pixmap_item.setPos(pos.x() + self.pan_offset_x, pos.y() + self.pan_offset_y)

    def _march_selection(self):
        if self.selection_mask is not None:
            self.selection_phase = (self.selection_phase + 1) % 6
            self.viewport().update()

    def has_selection(self):
        return self.selection_mask is not None

    def clear_selection(self):
        self.selection_mask = None
        self.selection_path = None
        self.selection_phase = 0
        self.viewport().update()

    def _apply_selection_clip(self, painter):
        if self.selection_mask is None:
            return
        if self.selection_path is not None:
            painter.setClipPath(self.selection_path)
        else:
            mono = self.selection_mask.convertToFormat(QImage.Format_Mono,
                                                       Qt.ThresholdDither)
            bitmap = QBitmap.fromImage(mono)
            region = QRegion(bitmap)
            painter.setClipRegion(region)

    def _selection_mask_from_path(self, path):
        w = int(self.scene.sceneRect().width())
        h = int(self.scene.sceneRect().height())
        mask = QImage(w, h, QImage.Format_ARGB32)
        mask.fill(Qt.transparent)
        p = QPainter(mask)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawPath(path)
        p.end()
        return mask

    def set_selection_rect(self, rect):
        from PyQt5.QtCore import QRect
        path = QPainterPath()
        path.addRect(QRectF(rect))
        self.selection_path = path
        self.selection_mask = self._selection_mask_from_path(path)
        self.selection_phase = 0
        self.viewport().update()

    def set_selection_ellipse(self, rect):
        from PyQt5.QtCore import QRect
        path = QPainterPath()
        path.addEllipse(QRectF(rect))
        self.selection_path = path
        self.selection_mask = self._selection_mask_from_path(path)
        self.selection_phase = 0
        self.viewport().update()

    def set_selection_lasso(self, points):
        path = QPainterPath()
        poly = QPolygonF(points)
        path.addPolygon(poly)
        path.closeSubpath()
        self.selection_path = path
        self.selection_mask = self._selection_mask_from_path(path)
        self.selection_phase = 0
        self.viewport().update()

    def set_selection_mask_image(self, mask_qimage):
        self.selection_mask = mask_qimage
        self.selection_path = None
        self.selection_phase = 0
        self.viewport().update()

    def move_layer_content(self, dx, dy):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return False
        w, h = layer.image.width(), layer.image.height()
        i_dx, i_dy = int(dx), int(dy)
        if i_dx == 0 and i_dy == 0:
            return False
        new_img = QImage(w, h, QImage.Format_ARGB32)
        new_img.fill(Qt.transparent)
        p = QPainter(new_img)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(i_dx, i_dy, layer.image)
        p.end()
        layer.image = new_img
        self._refresh()
        return True

    def draw_point(self, pos):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        if self.has_selection():
            self._apply_selection_clip(p)
        c = self.tool_color
        c.setAlpha(int(255 * self.tool_opacity))
        pen = QPen(c, self.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawPoint(pos)
        p.end()
        self.layer_stack.invalidate_cache()
        self._refresh()

    def draw_line(self, p1, p2):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        if self.has_selection():
            self._apply_selection_clip(p)
        c = self.tool_color
        c.setAlpha(int(255 * self.tool_opacity))
        pen = QPen(c, self.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(p1, p2)
        p.end()
        self.layer_stack.invalidate_cache()
        self._refresh()

    def erase_point(self, pos):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        if self.has_selection():
            self._apply_selection_clip(p)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        pen = QPen(QColor(0, 0, 0, 0), self.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawPoint(pos)
        p.end()
        self.layer_stack.invalidate_cache()
        self._refresh()

    def erase_line(self, p1, p2):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        if self.has_selection():
            self._apply_selection_clip(p)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        pen = QPen(QColor(0, 0, 0, 0), self.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(p1, p2)
        p.end()
        self.layer_stack.invalidate_cache()
        self._refresh()

    def _apply_pixel_op(self, pos, op_func, strength=1.0):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        radius = max(1, self.tool_size // 2)
        x, y = int(pos.x()), int(pos.y())
        w, h = layer.image.width(), layer.image.height()
        x0, y0 = max(0, x - radius), max(0, y - radius)
        x1, y1 = min(w, x + radius + 1), min(h, y + radius + 1)
        if x0 >= x1 or y0 >= y1:
            return
        from .filters import to_array, from_array
        rect = QRect(x0, y0, x1 - x0, y1 - y0)
        arr = to_array(layer.image.copy(rect)).astype(np.float32) / 255.0
        result = op_func(arr, strength)
        result = np.clip(result * 255.0, 0, 255).astype(np.uint8)
        new_img = from_array(result)
        p = QPainter(layer.image)
        p.setClipRect(rect)
        if self.has_selection():
            self._apply_selection_clip(p)
        p.drawImage(x0, y0, new_img)
        p.end()
        self.layer_stack.invalidate_cache()
        self._refresh()

    def _dodge_func(self, arr, exposure):
        result = np.clip(arr[..., :3] + (1.0 - arr[..., :3]) * exposure * 0.5, 0, 1)
        if arr.shape[2] == 4:
            result = np.concatenate([result, arr[..., 3:4]], axis=2)
        return result

    def _burn_func(self, arr, exposure):
        result = np.clip(arr[..., :3] - arr[..., :3] * exposure * 0.5, 0, 1)
        if arr.shape[2] == 4:
            result = np.concatenate([result, arr[..., 3:4]], axis=2)
        return result

    def _sponge_func(self, arr, amount):
        gray = np.mean(arr[..., :3], axis=2, keepdims=True)
        gray = np.repeat(gray, 3, axis=2)
        if amount > 0:
            result = arr[..., :3] + (arr[..., :3] - gray) * amount * 0.5
        else:
            result = arr[..., :3] + (gray - arr[..., :3]) * abs(amount) * 0.5
        result = np.clip(result, 0, 1)
        if arr.shape[2] == 4:
            result = np.concatenate([result, arr[..., 3:4]], axis=2)
        return result

    def dodge_point(self, pos, exposure=0.5):
        self._apply_pixel_op(pos, self._dodge_func, exposure)

    def burn_point(self, pos, exposure=0.5):
        self._apply_pixel_op(pos, self._burn_func, exposure)

    def saturate_point(self, pos, amount=0.5):
        self._apply_pixel_op(pos, self._sponge_func, amount)

    def dodge_line(self, p1, p2, exposure=0.5):
        steps = max(int(p1.distance(p2) / 2), 1)
        for t in range(steps + 1):
            frac = t / steps
            pt = QPointF(p1.x() + (p2.x() - p1.x()) * frac,
                         p1.y() + (p2.y() - p1.y()) * frac)
            self.dodge_point(pt, exposure)

    def burn_line(self, p1, p2, exposure=0.5):
        steps = max(int(p1.distance(p2) / 2), 1)
        for t in range(steps + 1):
            frac = t / steps
            pt = QPointF(p1.x() + (p2.x() - p1.x()) * frac,
                         p1.y() + (p2.y() - p1.y()) * frac)
            self.burn_point(pt, exposure)

    def saturate_line(self, p1, p2, amount=0.5):
        steps = max(int(p1.distance(p2) / 2), 1)
        for t in range(steps + 1):
            frac = t / steps
            pt = QPointF(p1.x() + (p2.x() - p1.x()) * frac,
                         p1.y() + (p2.y() - p1.y()) * frac)
            self.saturate_point(pt, amount)

    def get_pixel_color(self, pos):
        layer = self.layer_stack.active
        if not layer:
            return None
        x = max(0, min(int(pos.x()), layer.image.width() - 1))
        y = max(0, min(int(pos.y()), layer.image.height() - 1))
        return layer.image.pixelColor(x, y)

    def flood_fill(self, pos):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        x, y = int(pos.x()), int(pos.y())
        w_i, h_i = layer.image.width(), layer.image.height()
        if x < 0 or x >= w_i or y < 0 or y >= h_i:
            return

        target = layer.image.pixelColor(x, y)
        if target == self.tool_color:
            return

        q = deque()
        q.append((x, y))
        visited = {(x, y)}

        p = QPainter(layer.image)
        if self.has_selection():
            self._apply_selection_clip(p)
        p.setPen(QPen(self.tool_color, 1))

        while q:
            cx, cy = q.popleft()
            if layer.image.pixelColor(cx, cy) == target:
                p.drawPoint(cx, cy)
                for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                    if 0 <= nx < w_i and 0 <= ny < h_i and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        q.append((nx, ny))
        p.end()
        self._refresh()

    def flood_fill_select(self, pos):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        x, y = int(pos.x()), int(pos.y())
        w_i, h_i = layer.image.width(), layer.image.height()
        if x < 0 or x >= w_i or y < 0 or y >= h_i:
            return

        target = layer.image.pixelColor(x, y)
        tolerance = 32

        q = deque()
        q.append((x, y))
        visited = np.zeros((h_i, w_i), dtype=bool)
        visited[y, x] = True

        mask = QImage(w_i, h_i, QImage.Format_ARGB32)
        mask.fill(Qt.transparent)

        while q:
            cx, cy = q.popleft()
            color = layer.image.pixelColor(cx, cy)
            diff = (abs(color.red() - target.red()) +
                    abs(color.green() - target.green()) +
                    abs(color.blue() - target.blue()))
            if diff <= tolerance:
                mask.setPixel(cx, cy, QColor(255, 255, 255).rgba())
                for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                    if 0 <= nx < w_i and 0 <= ny < h_i and not visited[ny, nx]:
                        visited[ny, nx] = True
                        q.append((nx, ny))

        self.set_selection_mask_image(mask)

    def draw_gradient(self, start, end):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        w, h = layer.image.width(), layer.image.height()
        grad_obj = getattr(self, "gradient_obj", None)
        if grad_obj is not None and grad_obj.stops:
            grad = grad_obj.to_qgradient(start, end)
        else:
            from PyQt5.QtGui import QLinearGradient
            grad = QLinearGradient(start, end)
            grad.setColorAt(0.0, self.tool_color)
            grad.setColorAt(1.0, self.bg_color)
        p = QPainter(layer.image)
        if self.has_selection():
            self._apply_selection_clip(p)
        p.fillRect(0, 0, w, h, grad)
        p.end()
        self._refresh()

    def draw_rect_shape(self, start, end):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        if self.has_selection():
            self._apply_selection_clip(p)
        pen = QPen(self.tool_color, self.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        rect = QRectF(start, end)
        p.drawRect(rect.normalized())
        p.end()
        self._refresh()

    def draw_ellipse_shape(self, start, end):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        if self.has_selection():
            self._apply_selection_clip(p)
        pen = QPen(self.tool_color, self.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        rect = QRectF(start, end)
        p.drawEllipse(rect.normalized())
        p.end()
        self._refresh()

    def clone_stamp(self, src, dst):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        sx, sy = int(src.x()), int(src.y())
        dx, dy = int(dst.x()), int(dst.y())
        w, h = layer.image.width(), layer.image.height()
        if not (0 <= sx < w and 0 <= sy < h and 0 <= dx < w and 0 <= dy < h):
            return
        color = layer.image.pixelColor(sx, sy)
        p = QPainter(layer.image)
        if self.has_selection():
            self._apply_selection_clip(p)
        pen = QPen(color, self.tool_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawPoint(dx, dy)
        p.end()
        self._refresh()

    def draw_rubber_band(self, painter):
        if not self.has_rubber_band or not self.rubber_band_start or not self.rubber_band_end:
            return
        painter.save()
        painter.setPen(QPen(QColor(100, 150, 255, 200), 1, Qt.DashLine))
        painter.setBrush(QBrush(QColor(100, 150, 255, 30)))
        rect = QRectF(self.rubber_band_start, self.rubber_band_end)
        painter.drawRect(rect.normalized())
        painter.restore()

    def draw_selection_overlay(self, painter):
        if self.selection_mask is None:
            return
        w = self.selection_mask.width()
        h = self.selection_mask.height()
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        sel_pix = QPixmap.fromImage(self.selection_mask)
        tinted = QPixmap(w, h)
        tinted.fill(QColor(60, 120, 255, 40))
        tinted.setMask(sel_pix.createHeuristicMask())
        painter.drawPixmap(0, 0, tinted)
        if self.selection_path is not None:
            pen = QPen(QColor(60, 120, 255), 1, Qt.CustomDashLine)
            pen.setDashPattern([6, 4])
            pen.setDashOffset(self.selection_phase)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self.selection_path)
        painter.restore()

    def draw_lasso(self, painter):
        if not self.has_lasso or len(self.lasso_points) < 2:
            return
        painter.save()
        painter.setPen(QPen(QColor(100, 150, 255, 200), 1, Qt.DashLine))
        painter.setBrush(QBrush(QColor(100, 150, 255, 20)))
        poly = QPolygonF([pt for pt in self.lasso_points])
        painter.drawPolygon(poly)
        painter.restore()

    def draw_grid(self, painter):
        if not self.show_grid:
            return
        w = int(self.scene.sceneRect().width())
        h = int(self.scene.sceneRect().height())
        if self._settings:
            spacing = self._settings.get('grid_spacing', 50)
            color = QColor(self._settings.get('grid_color', '#808080'))
            style = self._settings.get('grid_style', 'Lines')
        else:
            spacing = 50
            color = QColor(128, 128, 128)
            style = 'Lines'
        painter.save()
        painter.setPen(QPen(color, 1 / self.zoom_level))
        if style == 'Lines':
            for x in range(spacing, w, spacing):
                painter.drawLine(x, 0, x, h)
            for y in range(spacing, h, spacing):
                painter.drawLine(0, y, w, y)
        elif style == 'Dots':
            for x in range(spacing, w, spacing):
                for y in range(spacing, h, spacing):
                    painter.drawPoint(x, y)
        elif style == 'Crosses':
            s = 4 / self.zoom_level
            for x in range(spacing, w, spacing):
                for y in range(spacing, h, spacing):
                    painter.drawLine(x - s, y, x + s, y)
                    painter.drawLine(x, y - s, x, y + s)
        painter.restore()

    def draw_rulers(self, painter):
        if not self.show_rulers:
            return
        ruler_size = 20
        w = int(self.pixmap_item.pixmap().width())
        h = int(self.pixmap_item.pixmap().height())
        painter.save()
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.setBrush(QBrush(QColor(50, 50, 50)))
        painter.drawRect(0, 0, w, ruler_size)
        painter.drawRect(0, 0, ruler_size, h)

        painter.setPen(QColor(180, 180, 180))
        font = QFont("monospace", 7)
        painter.setFont(font)
        spacing = self._settings.get('grid_spacing', 50) if self._settings else 50
        for x in range(spacing, w, spacing):
            painter.drawLine(x, ruler_size - 4, x, ruler_size)
            painter.drawText(x + 2, ruler_size - 2, str(x))
        for y in range(spacing, h, spacing):
            painter.drawLine(ruler_size - 4, y, ruler_size, y)
            painter.drawText(2, y + 10, str(y))
        painter.restore()

    def draw_pen_path(self, painter):
        painter.save()
        z = self.zoom_level
        if self.pen_path and len(self.pen_path) >= 2:
            path = QPainterPath()
            path.moveTo(self.pen_path[0])
            for i in range(1, len(self.pen_path)):
                prev = self.pen_path[i - 1]
                curr = self.pen_path[i]
                h_out = self.pen_handle_offsets[i - 1] if i - 1 < len(self.pen_handle_offsets) else None
                h_in = self.pen_handle_offsets[i] if i < len(self.pen_handle_offsets) else None
                if h_out is not None and h_in is not None:
                    path.cubicTo(prev + h_out, curr - h_in, curr)
                elif h_out is not None:
                    path.cubicTo(prev + h_out, curr, curr)
                elif h_in is not None:
                    path.cubicTo(prev, curr - h_in, curr)
                else:
                    path.lineTo(curr)
            painter.setPen(QPen(QColor(self.tool_color), 1.5 / z))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
            for pt in self.pen_path:
                painter.setBrush(QBrush(self.tool_color))
                painter.setPen(QPen(Qt.white, 1))
                r = 3.0 / z
                painter.drawEllipse(pt, r, r)
        self.draw_path_edit_overlay(painter)
        painter.restore()

    def draw_path_edit_overlay(self, painter):
        if self.selected_path_idx < 0 or self.selected_path_idx >= len(self.vector_paths):
            return
        pobj = self.vector_paths[self.selected_path_idx]
        if not pobj.anchors:
            return
        z = self.zoom_level
        painter.save()
        track_anchor_r = 4.0 / z
        track_handle_r = 3.0 / z
        for i, anchor in enumerate(pobj.anchors):
            pos = anchor.position
            is_selected = (i == self.edit_anchor_idx)
            painter.setBrush(QBrush(QColor(100, 150, 255, 180)))
            painter.setPen(QPen(Qt.white if is_selected else Qt.black, 1.0 / z))
            painter.drawEllipse(pos, track_anchor_r, track_anchor_r)
            for htype in ('handle_in', 'handle_out'):
                hpos = anchor.handle_in if htype == 'handle_in' else anchor.handle_out
                if (hpos - pos).manhattanLength() > 0.5:
                    painter.setPen(QPen(QColor(100, 150, 255), 1.0 / z, Qt.DashLine))
                    painter.drawLine(pos, hpos)
                    is_hover = (self.edit_handle == htype and i == self.edit_anchor_idx)
                    painter.setBrush(QBrush(QColor(255, 200, 100)))
                    painter.setPen(QPen(Qt.white if is_hover else Qt.black, 1.0 / z))
                    painter.drawEllipse(hpos, track_handle_r, track_handle_r)
        painter.restore()

    def _rasterize_vector_paths(self):
        layer = self.layer_stack.active
        if not layer or layer.locked:
            return
        layer.image.fill(Qt.transparent)
        for pobj in self.vector_paths:
            if pobj.visible:
                pobj.rasterize_to(layer.image, fill_color=self.tool_color, stroke_color=self.tool_color)
        self._refresh()

    def draw_crop_overlay(self, painter):
        if not self.crop_active or self.crop_start is None or self.crop_end is None:
            return
        rect = QRectF(self.crop_start, self.crop_end).normalized()
        painter.save()
        overlay_color = QColor(0, 0, 0, 128)
        painter.setBrush(overlay_color)
        painter.setPen(Qt.NoPen)
        sr = self.scene.sceneRect()
        painter.drawRect(0, 0, sr.width(), rect.top())
        painter.drawRect(0, rect.bottom(), sr.width(), sr.height() - rect.bottom())
        painter.drawRect(0, rect.top(), rect.left(), rect.height())
        painter.drawRect(rect.right(), rect.top(), sr.width() - rect.right(), rect.height())
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(100, 150, 255), 1.5 / self.zoom_level))
        painter.drawRect(rect)
        hs = 6.0 / self.zoom_level
        painter.setBrush(QColor(100, 150, 255))
        painter.setPen(Qt.NoPen)
        for pt in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
            painter.drawRect(QRectF(pt.x() - hs / 2, pt.y() - hs / 2, hs, hs))
        for pt in [QPointF(rect.center().x(), rect.top()),
                   QPointF(rect.center().x(), rect.bottom()),
                   QPointF(rect.left(), rect.center().y()),
                   QPointF(rect.right(), rect.center().y())]:
            painter.drawRect(QRectF(pt.x() - hs / 2, pt.y() - hs / 2, hs, hs))
        painter.restore()

    def _snap_point(self, pos):
        if not hasattr(self, 'snapping'):
            return pos, None
        grid_spacing = self._settings.get('grid_spacing', 50) if self._settings else 50
        guides = self.guide_mgr.guides if self.guide_mgr else []
        return self.snapping.snap_point(pos, guides=guides, grid_spacing=grid_spacing)

    def _show_snap_indicator(self, pos, text):
        self.snap_indicator = (pos, text)

    def draw_snap_indicator(self, painter):
        if self.snap_indicator is None:
            return
        pos, text = self.snap_indicator
        painter.save()
        painter.setPen(QPen(QColor(255, 255, 0, 200), 1, Qt.DashLine))
        painter.setBrush(QBrush(QColor(255, 255, 0, 30)))
        hs = 4.0 / self.zoom_level
        painter.drawRect(QRectF(pos.x() - hs, pos.y() - hs, hs * 2, hs * 2))
        painter.setPen(QColor(255, 255, 0, 200))
        font = QFont("monospace", 8)
        painter.setFont(font)
        painter.drawText(QPointF(pos.x() + hs + 2, pos.y() - hs - 2), text)
        painter.restore()

    def draw_overlay(self, painter):
        self.draw_grid(painter)
        self.draw_selection_overlay(painter)
        self.draw_rubber_band(painter)
        self.draw_lasso(painter)
        self.draw_pen_path(painter)
        self.draw_crop_overlay(painter)
        self.guide_mgr.draw(painter, self.pixmap_item.pixmap().size())
        self.draw_snap_indicator(painter)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor(30, 30, 30))
        scene_rect = self.scene.sceneRect()
        if scene_rect.isEmpty():
            return
        # Drop shadow behind image
        shadow_rect = scene_rect.translated(3, 3)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 80))
        # Checkerboard pattern for transparency
        painter.save()
        painter.setClipRect(scene_rect)
        light = QColor(0x1a, 0x1a, 0x1a)
        dark = QColor(0x0d, 0x0d, 0x0d)
        s = 16
        for x in range(int(scene_rect.left()), int(scene_rect.right()), s):
            for y in range(int(scene_rect.top()), int(scene_rect.bottom()), s):
                col = light if ((x // s) + (y // s)) % 2 == 0 else dark
                painter.fillRect(x, y, s, s, col)
        painter.restore()
        # 2px border around image
        painter.setPen(QPen(QColor(10, 10, 10), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(scene_rect)

    def drawForeground(self, painter, rect):
        self.draw_overlay(painter)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.zoom_level *= factor
            self.scale(factor, factor)
            self.zoom_changed.emit(self.zoom_level)
            self.status_changed.emit(f"Zoom: {self.zoom_level * 100:.0f}%")
        else:
            super().wheelEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path and path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext not in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.psd'):
                continue
            layer = self.import_image_as_layer(path)
            if layer:
                main = self.window()
                if hasattr(main, 'statusBar'):
                    main.statusBar().showMessage(f"Placed: {os.path.basename(path)}")
                if hasattr(main, 'layer_panel'):
                    main.layer_panel.refresh()
                if hasattr(main, 'nav_panel'):
                    main.nav_panel.refresh()
                event.acceptProposedAction()
                return
        event.ignore()

    def paste_from_clipboard(self):
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasImage():
            img = clipboard.image()
            if img.isNull():
                return False
            if img.format() != QImage.Format_ARGB32:
                img = img.convertToFormat(QImage.Format_ARGB32)
            w, h = self.layer_stack.layers[0].image.width(), self.layer_stack.layers[0].image.height()
            if img.width() != w or img.height() != h:
                img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            layer = Layer(w, h, "Pasted", Qt.transparent)
            layer.image = img.copy()
            self.layer_stack.layers.append(layer)
            self.layer_stack.active_index = len(self.layer_stack.layers) - 1
            self._save_state("Paste image")
            self._refresh()
            return True
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path:
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.psd'):
                        layer = self.import_image_as_layer(path)
                        if layer:
                            self._save_state(f"Paste {os.path.basename(path)}")
                            return True
        return False

    def _ruler_hit_test(self, view_pos):
        ruler_size = 20
        if view_pos.x() < ruler_size:
            return Qt.Vertical
        if view_pos.y() < ruler_size:
            return Qt.Horizontal
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            from .tools import PenTool
            if isinstance(self.tool, PenTool):
                self.tool.finalize(self)
            return
        if event.button() == Qt.LeftButton:
            view_pos = event.pos()
            ruler_orientation = self._ruler_hit_test(view_pos)
            if ruler_orientation is not None:
                pos = self.mapToScene(view_pos)
                if not self.guide_mgr.locked:
                    gi = self.guide_mgr.hit_test(pos, 8.0 / self.zoom_level)
                    if gi >= 0:
                        self.dragging_guide_index = gi
                        self.ruler_dragging_guide = True
                        self.ruler_drag_orientation = self.guide_mgr.guides[gi].orientation
                        self.ruler_drag_pos = pos.x() if self.ruler_drag_orientation == Qt.Vertical else pos.y()
                    else:
                        self.ruler_dragging_guide = True
                        self.ruler_drag_orientation = ruler_orientation
                        self.ruler_drag_pos = pos.x() if ruler_orientation == Qt.Vertical else pos.y()
                return
            self.drawing = True
            pos = self.mapToScene(view_pos)
            sn_pos, snap_info = self._snap_point(pos)
            self.last_point = sn_pos
            mods = int(event.modifiers())
            self._save_state(f"{self.tool.name if hasattr(self.tool, 'name') else 'Tool'}")
            self.tool.press(self, sn_pos, mods)
            if snap_info:
                self._show_snap_indicator(snap_info[0], snap_info[1])
                self.status_changed.emit(f"Snap to {snap_info[1]}")
        elif event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(pos.x(), pos.y())
        if self.ruler_dragging_guide:
            self.ruler_drag_pos = pos.x() if self.ruler_drag_orientation == Qt.Vertical else pos.y()
            self.viewport().update()
            return
        if self.drawing and self.last_point:
            mods = int(event.modifiers())
            sn_pos, snap_info = self._snap_point(pos)
            self.tool.move(self, self.last_point, sn_pos, mods)
            self.last_point = sn_pos
            if snap_info:
                self._show_snap_indicator(snap_info[0], snap_info[1])
                self.status_changed.emit(f"Snap to {snap_info[1]}")
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.ruler_dragging_guide:
                pos = self.mapToScene(event.pos())
                if self.dragging_guide_index >= 0:
                    if not self.guide_mgr.locked:
                        view_pos = event.pos()
                        ruler_orientation = self._ruler_hit_test(view_pos)
                        if ruler_orientation is not None:
                            self.guide_mgr.remove_guide(self.dragging_guide_index)
                        else:
                            g = self.guide_mgr.guides[self.dragging_guide_index]
                            g.position = pos.x() if g.orientation == Qt.Vertical else pos.y()
                    self.dragging_guide_index = -1
                else:
                    pv = pos.x() if self.ruler_drag_orientation == Qt.Vertical else pos.y()
                    if pv >= 0:
                        self.guide_mgr.add_guide(self.ruler_drag_orientation, pv)
                self.ruler_dragging_guide = False
                self.ruler_drag_orientation = None
                self.ruler_drag_pos = None
                self.viewport().update()
                return
            if self.drawing:
                self.drawing = False
                mods = int(event.modifiers())
                pos = self.mapToScene(event.pos())
                sn_pos, snap_info = self._snap_point(pos)
                self.tool.release(self, sn_pos, mods)
                if snap_info:
                    self._show_snap_indicator(snap_info[0], snap_info[1])
                    self.status_changed.emit(f"Snap to {snap_info[1]}")
        elif event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.NoDrag)
            event.ignore()

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()

        # Tool shortcuts (Photoshop-style)
        if key == Qt.Key_V and not mods: self.set_tool("Move Tool")
        elif key == Qt.Key_M and not mods: self.set_tool("Rectangular Marquee Tool")
        elif key == Qt.Key_L and not mods: self.set_tool("Lasso Tool")
        elif key == Qt.Key_W and not mods: self.set_tool("Magic Wand Tool")
        elif key == Qt.Key_B and not mods: self.set_tool("Brush Tool")
        elif key == Qt.Key_P and not mods: self.set_tool("Pen Tool")
        elif key == Qt.Key_N and not mods: self.set_tool("Pencil Tool")
        elif key == Qt.Key_E and not mods: self.set_tool("Eraser Tool")
        elif key == Qt.Key_G and not mods: self.set_tool("Gradient Tool")
        elif key == Qt.Key_U and not mods: self.set_tool("Rectangle Tool")
        elif key == Qt.Key_S and not mods: self.set_tool("Clone Stamp Tool")
        elif key == Qt.Key_J and not mods: self.set_tool("Spot Healing Brush Tool")
        elif key == Qt.Key_C and not mods: self.set_tool("Crop Tool")
        elif key == Qt.Key_T and not mods: self.set_tool("Horizontal Type Tool")
        elif key == Qt.Key_H and not mods: self.set_tool("Hand Tool")
        elif key == Qt.Key_Z and not mods: self.set_tool("Zoom Tool")
        elif key == Qt.Key_I and not mods: self.set_tool("Eyedropper Tool")
        elif key == Qt.Key_K and not mods: self.set_tool("Paint Bucket Tool")

        elif key == Qt.Key_BracketRight and not mods: self.set_tool_size(self.tool_size + 1)
        elif key == Qt.Key_BracketLeft and not mods: self.set_tool_size(max(1, self.tool_size - 1))

        # Enter / Return to finalize pen or apply crop
        elif key in (Qt.Key_Return, Qt.Key_Enter) and not mods:
            from .tools import PenTool, CropTool
            if isinstance(self.tool, PenTool):
                self.tool.finalize(self)
            elif isinstance(self.tool, CropTool):
                self.tool.apply(self)

        # Backspace to delete selected anchor in pen tool
        elif key == Qt.Key_Backspace and not mods:
            from .tools import PenTool
            if isinstance(self.tool, PenTool):
                self.tool.key_press(self, key)

        # Escape to cancel pen or crop
        elif key == Qt.Key_Escape and not mods:
            from .tools import PenTool, CropTool
            if isinstance(self.tool, PenTool):
                self.tool.cancel(self)
            elif isinstance(self.tool, CropTool):
                self.tool.cancel(self)

        # Ctrl+
        elif mods & Qt.ControlModifier:
            if key == Qt.Key_Z:
                if mods & Qt.ShiftModifier:
                    if self.history.can_redo():
                        self.history.redo(self.layer_stack)
                        self._refresh()
                else:
                    if self.history.can_undo():
                        self.history.undo(self.layer_stack)
                        self._refresh()
            elif key == Qt.Key_V:
                if self.paste_from_clipboard():
                    self.status_changed.emit("Pasted image from clipboard")
                    main = self.window()
                    if hasattr(main, 'layer_panel'):
                        main.layer_panel.refresh()
                    if hasattr(main, 'nav_panel'):
                        main.nav_panel.refresh()
            elif key == Qt.Key_Plus: self.zoom_in()
            elif key == Qt.Key_Minus: self.zoom_out()
            elif key == Qt.Key_0: self.zoom_fit()
            elif key == Qt.Key_1: self.zoom_100()
            elif key == Qt.Key_2: self.zoom_to_selection()

        super().keyPressEvent(event)
