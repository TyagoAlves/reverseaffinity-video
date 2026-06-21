"""Professional tools (Photoshop-style naming)
Hotkeys:
  V - Move Tool       M - Rect Marquee   L - Lasso Tool
  W - Magic Wand      B - Brush Tool     P - Pen Tool
  N - Pencil Tool     E - Eraser Tool    G - Gradient Tool
  U - Rectangle Tool  S - Clone Stamp    J - Spot Healing
  H - Hand Tool       Z - Zoom Tool      I - Eyedropper
  K - Paint Bucket    C - Crop Tool      T - Type Tool
"""

from PyQt5.QtCore import Qt, QPointF, QRectF
from .brushengine import BrushEngine, CircleTip, SquareTip, TextureTip
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontDatabase, QPainterPath, QCursor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
    QSpinBox, QPushButton, QLabel, QCheckBox, QMessageBox,
)

SHORTCUT_MAP = {}


def register(name, shortcut, cls):
    SHORTCUT_MAP[shortcut.lower()] = cls


class Tool:
    name = "tool"
    shortcut = ""
    cursor_shape = None
    _cursor = None

    def __init__(self):
        self.pressure = 1.0

    @property
    def cursor(self):
        if self._cursor is None and self.cursor_shape is not None:
            self._cursor = QCursor(self.cursor_shape)
        return self._cursor

    def press(self, canvas, pos, modifiers): pass
    def move(self, canvas, last, pos, modifiers): pass
    def release(self, canvas, pos, modifiers): pass
    def double_click(self, canvas, pos, modifiers): pass


class MoveTool(Tool):
    name = "Move Tool"
    shortcut = "V"
    cursor_shape = Qt.SizeAllCursor

    def press(self, canvas, pos, mods):
        canvas.drag_start = pos
        canvas.dragging_layer = True

    def move(self, canvas, last, pos, mods):
        if canvas.dragging_layer:
            dx = pos.x() - canvas.drag_start.x()
            dy = pos.y() - canvas.drag_start.y()
            if abs(dx) >= 0.5 or abs(dy) >= 0.5:
                canvas.move_layer_content(dx, dy)
                canvas.drag_start = pos

    def release(self, canvas, pos, mods):
        canvas.dragging_layer = False


class RectSelectTool(Tool):
    name = "Rectangular Marquee Tool"
    shortcut = "M"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.selection_start = pos
        canvas.rubber_band_start = pos
        canvas.rubber_band_end = pos
        canvas.has_rubber_band = True

    def move(self, canvas, last, pos, mods):
        canvas.rubber_band_end = pos
        canvas.update()

    def release(self, canvas, pos, mods):
        canvas.has_rubber_band = False
        from PyQt5.QtCore import QRect, QPoint
        x1, y1 = int(canvas.selection_start.x()), int(canvas.selection_start.y())
        x2, y2 = int(pos.x()), int(pos.y())
        rect = QRect(QPoint(min(x1, x2), min(y1, y2)), QPoint(max(x1, x2), max(y1, y2)))
        canvas.set_selection_rect(rect)


class EllipseSelectTool(Tool):
    name = "Elliptical Marquee Tool"
    shortcut = ""
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.selection_start = pos
        canvas.rubber_band_start = pos
        canvas.rubber_band_end = pos
        canvas.has_rubber_band = True

    def move(self, canvas, last, pos, mods):
        canvas.rubber_band_end = pos
        canvas.viewport().update()

    def release(self, canvas, pos, mods):
        canvas.has_rubber_band = False
        from PyQt5.QtCore import QRect, QPoint
        x1, y1 = int(canvas.selection_start.x()), int(canvas.selection_start.y())
        x2, y2 = int(pos.x()), int(pos.y())
        rect = QRect(QPoint(min(x1, x2), min(y1, y2)), QPoint(max(x1, x2), max(y1, y2)))
        canvas.set_selection_ellipse(rect)


class LassoTool(Tool):
    name = "Lasso Tool"
    shortcut = "L"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.lasso_points = [pos]
        canvas.has_lasso = True

    def move(self, canvas, last, pos, mods):
        canvas.lasso_points.append(pos)
        canvas.viewport().update()

    def release(self, canvas, pos, mods):
        canvas.has_lasso = False
        if canvas.lasso_points:
            canvas.lasso_points.append(pos)
            canvas.set_selection_lasso(canvas.lasso_points)
        canvas.lasso_points = []
        canvas.viewport().update()


class MagicWandTool(Tool):
    name = "Magic Wand Tool"
    shortcut = "W"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.flood_fill_select(pos)


class PencilTool(Tool):
    name = "Pencil Tool"
    shortcut = "N"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.draw_point(pos)

    def move(self, canvas, last, pos, mods):
        canvas.draw_line(last, pos)


class BrushTool(Tool):
    name = "Brush Tool"
    shortcut = "B"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.draw_point(pos)

    def move(self, canvas, last, pos, mods):
        canvas.draw_line(last, pos)


class EraserTool(Tool):
    name = "Eraser Tool"
    shortcut = "E"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.erase_point(pos)

    def move(self, canvas, last, pos, mods):
        canvas.erase_line(last, pos)


class GradientTool(Tool):
    name = "Gradient Tool"
    shortcut = "G"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.gradient_start = pos
        canvas.temp_save_layer()

    def move(self, canvas, last, pos, mods):
        canvas.temp_restore_layer()
        canvas.draw_gradient(canvas.gradient_start, pos)

    def release(self, canvas, pos, mods):
        canvas.temp_restore_layer()
        canvas._save_state("Gradient")
        canvas.draw_gradient(canvas.gradient_start, pos)


class ShapeTool(Tool):
    name = "Rectangle Tool"
    shortcut = "U"
    cursor_shape = Qt.CrossCursor
    shape_mode = "rect"

    def press(self, canvas, pos, mods):
        canvas.shape_start = pos
        canvas.temp_save_layer()

    def move(self, canvas, last, pos, mods):
        canvas.temp_restore_layer()
        if self.shape_mode == "ellipse":
            canvas.draw_ellipse_shape(canvas.shape_start, pos)
        else:
            canvas.draw_rect_shape(canvas.shape_start, pos)

    def release(self, canvas, pos, mods):
        canvas.temp_restore_layer()
        canvas._save_state(self.name)
        if self.shape_mode == "ellipse":
            canvas.draw_ellipse_shape(canvas.shape_start, pos)
        else:
            canvas.draw_rect_shape(canvas.shape_start, pos)


class CloneStampTool(Tool):
    name = "Clone Stamp Tool"
    shortcut = "S"
    cursor_shape = Qt.CrossCursor
    clone_source = None

    def press(self, canvas, pos, mods):
        if mods & Qt.AltModifier:
            self.clone_source = pos
        elif self.clone_source:
            canvas.clone_stamp(self.clone_source, pos)

    def move(self, canvas, last, pos, mods):
        if self.clone_source and not (mods & Qt.AltModifier):
            dx = pos.x() - last.x()
            dy = pos.y() - last.y()
            canvas.clone_stamp(self.clone_source, pos)
            self.clone_source = QPointF(self.clone_source.x() + dx, self.clone_source.y() + dy)


class ColorPickerTool(Tool):
    name = "Eyedropper Tool"
    shortcut = "I"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        color = canvas.get_pixel_color(pos)
        if color:
            canvas.set_foreground_color(color)


class FloodFillTool(Tool):
    name = "Paint Bucket Tool"
    shortcut = "K"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.flood_fill(pos)


class HandTool(Tool):
    name = "Hand Tool"
    shortcut = "H"
    cursor_shape = Qt.OpenHandCursor

    def press(self, canvas, pos, mods):
        canvas.setDragMode(1)
        super().press(canvas, pos, mods)

    def release(self, canvas, pos, mods):
        canvas.setDragMode(0)
        super().release(canvas, pos, mods)


class ZoomTool(Tool):
    name = "Zoom Tool"
    shortcut = "Z"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        if mods & 0x04000000:  # Alt
            canvas.zoom_out()
        else:
            canvas.zoom_in()


class PenTool(Tool):
    name = "Pen Tool"
    shortcut = "P"
    cursor_shape = Qt.CrossCursor
    dragging = False

    def press(self, canvas, pos, mods):
        if not hasattr(canvas, 'pen_path'):
            canvas.pen_path = []
            canvas.pen_handle_offsets = []
        canvas.pen_path.append(pos)
        canvas.pen_handle_offsets.append(None)
        self.dragging = True
        self.press_pos = pos
        canvas.update()

    def move(self, canvas, last, pos, mods):
        if self.dragging and hasattr(canvas, 'pen_path') and canvas.pen_path:
            offset = pos - canvas.pen_path[-1]
            if offset.manhattanLength() > 3:
                canvas.pen_handle_offsets[-1] = offset
            canvas.update()

    def release(self, canvas, pos, mods):
        self.dragging = False

    def finalize(self, canvas):
        if not hasattr(canvas, 'pen_path') or len(canvas.pen_path) < 2:
            canvas.pen_path = []
            canvas.pen_handle_offsets = []
            canvas.update()
            return
        layer = canvas.layer_stack.active
        if layer and not layer.locked:
            p = QPainter(layer.image)
            p.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.moveTo(canvas.pen_path[0])
            for i in range(1, len(canvas.pen_path)):
                prev = canvas.pen_path[i - 1]
                curr = canvas.pen_path[i]
                h_out = canvas.pen_handle_offsets[i - 1]
                h_in = canvas.pen_handle_offsets[i]
                if h_out is not None and h_in is not None:
                    path.cubicTo(prev + h_out, curr - h_in, curr)
                elif h_out is not None:
                    path.cubicTo(prev + h_out, curr, curr)
                elif h_in is not None:
                    path.cubicTo(prev, curr - h_in, curr)
                else:
                    path.lineTo(curr)
            p.fillPath(path, QBrush(canvas.tool_color))
            p.setPen(QPen(canvas.tool_color, 1.5))
            p.drawPath(path)
            p.end()
            canvas._refresh()
        canvas.pen_path = []
        canvas.pen_handle_offsets = []
        canvas.update()

    def cancel(self, canvas):
        canvas.pen_path = []
        canvas.pen_handle_offsets = []
        canvas.update()


class TextTool(Tool):
    name = "Horizontal Type Tool"
    shortcut = "T"
    cursor_shape = Qt.IBeamCursor

    def press(self, canvas, pos, mods):
        dialog = QDialog()
        dialog.setWindowTitle("Text Tool")
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setPlainText("Type here")
        layout.addWidget(text_edit)

        font_layout = QHBoxLayout()
        font_combo = QComboBox()
        font_combo.addItems(QFontDatabase().families())
        font_combo.setCurrentText("Arial")
        font_layout.addWidget(QLabel("Font:"))
        font_layout.addWidget(font_combo)

        size_spin = QSpinBox()
        size_spin.setRange(1, 999)
        size_spin.setValue(32)
        font_layout.addWidget(QLabel("Size:"))
        font_layout.addWidget(size_spin)

        bold_cb = QCheckBox("B")
        italic_cb = QCheckBox("I")
        underline_cb = QCheckBox("U")
        font_layout.addWidget(bold_cb)
        font_layout.addWidget(italic_cb)
        font_layout.addWidget(underline_cb)
        layout.addLayout(font_layout)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        confirmed = False

        def on_ok():
            nonlocal confirmed
            confirmed = True
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec_()

        if confirmed:
            layer = canvas.layer_stack.active
            if not layer or layer.locked:
                return
            text = text_edit.toPlainText()
            font = QFont(font_combo.currentText(), size_spin.value())
            font.setBold(bold_cb.isChecked())
            font.setItalic(italic_cb.isChecked())
            font.setUnderline(underline_cb.isChecked())
            p = QPainter(layer.image)
            p.setRenderHint(QPainter.Antialiasing)
            p.setFont(font)
            p.setPen(canvas.tool_color)
            p.drawText(pos, text)
            p.end()
            canvas._refresh()


class HealingBrushTool(Tool):
    name = "Spot Healing Brush Tool"
    shortcut = "J"
    cursor_shape = Qt.CrossCursor
    healing_source = None

    def press(self, canvas, pos, mods):
        if mods & Qt.AltModifier:
            self.healing_source = pos
        elif self.healing_source is not None:
            self._heal(canvas, self.healing_source, pos)

    def move(self, canvas, last, pos, mods):
        if self.healing_source is not None and not (mods & Qt.AltModifier):
            dx = pos.x() - last.x()
            dy = pos.y() - last.y()
            src = self.healing_source
            self._heal(canvas, src, pos)
            self.healing_source = QPointF(src.x() + dx, src.y() + dy)

    def _heal(self, canvas, src, dst):
        layer = canvas.layer_stack.active
        if not layer or layer.locked:
            return
        from .filters import to_array, from_array, heal_patch
        img_arr = to_array(layer.image)
        h, w = img_arr.shape[:2]
        sx, sy = int(src.x()), int(src.y())
        dx, dy = int(dst.x()), int(dst.y())
        r = max(1, canvas.tool_size // 2 + 1)
        x1 = max(0, sx - r)
        x2 = min(w, sx + r + 1)
        y1 = max(0, sy - r)
        y2 = min(h, sy + r + 1)
        tx1 = max(0, dx - r)
        tx2 = min(w, dx + r + 1)
        ty1 = max(0, dy - r)
        ty2 = min(h, dy + r + 1)
        size_x = min(x2 - x1, tx2 - tx1)
        size_y = min(y2 - y1, ty2 - ty1)
        if size_x < 2 or size_y < 2:
            return
        src_patch = img_arr[y1:y1 + size_y, x1:x1 + size_x].copy()
        dst_patch = img_arr[ty1:ty1 + size_y, tx1:tx1 + size_x]
        heal_patch(src_patch, dst_patch, r)
        layer.image = from_array(img_arr)
        canvas._refresh()


class CropTool(Tool):
    name = "Crop Tool"
    shortcut = "C"
    cursor_shape = Qt.CrossCursor

    def _get_handles(self, canvas):
        rect = QRectF(canvas.crop_start, canvas.crop_end).normalized()
        hs = 6.0 / (canvas.zoom_level or 1.0)
        return {
            'top_left': (rect.topLeft(), hs),
            'top_right': (rect.topRight(), hs),
            'bottom_left': (rect.bottomLeft(), hs),
            'bottom_right': (rect.bottomRight(), hs),
            'top_mid': (QPointF(rect.center().x(), rect.top()), hs),
            'bottom_mid': (QPointF(rect.center().x(), rect.bottom()), hs),
            'left_mid': (QPointF(rect.left(), rect.center().y()), hs),
            'right_mid': (QPointF(rect.right(), rect.center().y()), hs),
        }

    def _hit_handle(self, canvas, pos):
        rect = QRectF(canvas.crop_start, canvas.crop_end).normalized()
        hs = 8.0 / (canvas.zoom_level or 1.0)
        for name, (pt, _) in self._get_handles(canvas).items():
            if abs(pos.x() - pt.x()) <= hs and abs(pos.y() - pt.y()) <= hs:
                return name
        return None

    def _handle_cursor(self, handle):
        if not handle:
            return Qt.CrossCursor
        if 'top' in handle and 'left' in handle:
            return Qt.SizeFDiagCursor
        if 'bottom' in handle and 'right' in handle:
            return Qt.SizeFDiagCursor
        if 'top' in handle and 'right' in handle:
            return Qt.SizeBDiagCursor
        if 'bottom' in handle and 'left' in handle:
            return Qt.SizeBDiagCursor
        if 'top' in handle or 'bottom' in handle:
            return Qt.SizeVerCursor
        if 'left' in handle or 'right' in handle:
            return Qt.SizeHorCursor
        return Qt.CrossCursor

    def _resize_rect(self, rect, handle, pos):
        r = QRectF(rect)
        if 'top' in handle:
            if 'left' in handle:
                r.setTopLeft(pos)
            elif 'right' in handle:
                r.setTopRight(pos)
            else:
                r.setTop(pos.y())
        elif 'bottom' in handle:
            if 'left' in handle:
                r.setBottomLeft(pos)
            elif 'right' in handle:
                r.setBottomRight(pos)
            else:
                r.setBottom(pos.y())
        elif 'left' in handle:
            r.setLeft(pos.x())
        elif 'right' in handle:
            r.setRight(pos.x())
        return r

    def press(self, canvas, pos, mods):
        handle = self._hit_handle(canvas, pos) if canvas.crop_active else None
        if handle:
            canvas.crop_drag_handle = handle
        else:
            canvas.crop_start = pos
            canvas.crop_end = pos
            canvas.crop_active = True
            canvas.crop_drag_handle = None
            canvas.crop_drag_offset = None

    def move(self, canvas, last, pos, mods):
        if not canvas.crop_active:
            return
        handle = canvas.crop_drag_handle
        if handle:
            rect = QRectF(canvas.crop_start, canvas.crop_end).normalized()
            new_rect = self._resize_rect(rect, handle, pos).normalized()
            canvas.crop_start = new_rect.topLeft()
            canvas.crop_end = new_rect.bottomRight()
        else:
            handle_hover = self._hit_handle(canvas, pos)
            if handle_hover:
                canvas.setCursor(self._handle_cursor(handle_hover))
            else:
                canvas.setCursor(Qt.CrossCursor)
            canvas.crop_end = pos
        canvas.update()

    def release(self, canvas, pos, mods):
        if not canvas.crop_active:
            return
        handle = canvas.crop_drag_handle
        if handle:
            rect = QRectF(canvas.crop_start, canvas.crop_end).normalized()
            new_rect = self._resize_rect(rect, handle, pos).normalized()
            canvas.crop_start = new_rect.topLeft()
            canvas.crop_end = new_rect.bottomRight()
        else:
            canvas.crop_end = pos
        canvas.crop_drag_handle = None
        canvas.update()

    def apply(self, canvas):
        if not canvas.crop_active:
            return
        rect = QRectF(canvas.crop_start, canvas.crop_end).normalized()
        if rect.width() < 2 or rect.height() < 2:
            self.cancel(canvas)
            return
        x, y, w, h = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
        canvas._save_state("Crop")
        for layer in canvas.layer_stack.layers:
            if hasattr(layer, 'image'):
                layer.image = layer.image.copy(x, y, w, h)
        canvas.crop_active = False
        canvas.crop_start = None
        canvas.crop_end = None
        canvas.crop_drag_handle = None
        canvas._refresh()

    def cancel(self, canvas):
        canvas.crop_active = False
        canvas.crop_start = None
        canvas.crop_end = None
        canvas.crop_drag_handle = None
        canvas.update()


class DodgeTool(Tool):
    name = "Dodge Tool"
    shortcut = "O"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.dodge_point(pos, canvas.tool_opacity)

    def move(self, canvas, last, pos, mods):
        canvas.dodge_line(last, pos, canvas.tool_opacity)


class BurnTool(Tool):
    name = "Burn Tool"
    shortcut = "O"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.burn_point(pos, canvas.tool_opacity)

    def move(self, canvas, last, pos, mods):
        canvas.burn_line(last, pos, canvas.tool_opacity)


class SpongeTool(Tool):
    name = "Sponge Tool"
    shortcut = "O"
    cursor_shape = Qt.CrossCursor

    def press(self, canvas, pos, mods):
        canvas.saturate_point(pos, canvas.tool_opacity * 2 - 1)

    def move(self, canvas, last, pos, mods):
        canvas.saturate_line(last, pos, canvas.tool_opacity * 2 - 1)


# Register all tools
for _cls in [MoveTool, RectSelectTool, EllipseSelectTool, LassoTool,
             MagicWandTool, PencilTool, BrushTool, EraserTool,
             GradientTool, ShapeTool, CloneStampTool,
             ColorPickerTool, FloodFillTool, HandTool, ZoomTool,
             PenTool, TextTool, HealingBrushTool, CropTool,
             DodgeTool, BurnTool, SpongeTool]:
    SHORTCUT_MAP[_cls.shortcut.lower()] = _cls

TOOLS_BY_NAME = {}
_ALIASES = {
    "brush": "Brush Tool",
    "pencil": "Pencil Tool",
    "eraser": "Eraser Tool",
    "move": "Move Tool",
    "zoom": "Zoom Tool",
    "hand": "Hand Tool",
    "text": "Text Tool",
    "pen": "Pen Tool",
    "gradient": "Gradient Tool",
    "shape": "Shape Tool",
    "clone": "Clone Stamp Tool",
    "heal": "Healing Brush Tool",
    "crop": "Crop Tool",
    "rect": "Rect Select Tool",
    "ellipse": "Ellipse Select Tool",
    "lasso": "Lasso Tool",
    "wand": "Magic Wand Tool",
    "picker": "Color Picker Tool",
    "fill": "Flood Fill Tool",
    "stamp": "Clone Stamp Tool",
    "dodge": "Dodge Tool",
    "burn": "Burn Tool",
    "sponge": "Sponge Tool",
}
for _cls in [MoveTool, RectSelectTool, EllipseSelectTool, LassoTool,
             MagicWandTool, PencilTool, BrushTool, EraserTool,
             GradientTool, ShapeTool, CloneStampTool,
             ColorPickerTool, FloodFillTool, HandTool, ZoomTool,
             PenTool, TextTool, HealingBrushTool, CropTool,
             DodgeTool, BurnTool, SpongeTool]:
    TOOLS_BY_NAME[_cls.name.lower()] = _cls
for _alias, _full in _ALIASES.items():
    TOOLS_BY_NAME[_alias] = TOOLS_BY_NAME.get(_full.lower())

TOOL_LIST = [
    ("Select", [MoveTool, RectSelectTool, EllipseSelectTool, LassoTool, MagicWandTool]),
    ("Draw", [BrushTool, PencilTool, PenTool, EraserTool, GradientTool, ShapeTool]),
    ("Text", [TextTool]),
    ("Retouch", [CloneStampTool, HealingBrushTool, DodgeTool, BurnTool, SpongeTool]),
    ("Crop", [CropTool]),
    ("Color", [ColorPickerTool, FloodFillTool]),
    ("View", [HandTool, ZoomTool]),
]
