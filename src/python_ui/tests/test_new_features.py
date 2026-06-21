from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QImage, QColor

from editor.canvas import CanvasView
from editor.layers import Layer, LayerStack, GroupLayer, AdjustmentLayer
from editor.tools import CropTool, MoveTool, PenTool, CloneStampTool
from editor.brushengine import BrushEngine, CircleTip
from editor.history import HistoryManager
from editor.filters import gaussian_blur, adjustment_brightness_contrast, adjustment_curves, curves, to_array
from editor.gradient import GradientStop, Gradient
from editor.snapping import SnappingEngine
from editor.settings import SettingsManager
from editor.file_formats import get_open_filter, get_save_filter, FORMAT_REGISTRY
from editor.file_formats import qimage_to_pil, pil_to_qimage


class TestCanvasDefaults:
    def setup_method(self):
        self.c = CanvasView()

    def test_tool_size_default(self):
        assert self.c.tool_size == 3

    def test_set_tool_size(self):
        self.c.set_tool_size(20)
        assert self.c.tool_size == 20

    def test_set_tool_opacity(self):
        self.c.tool_opacity = 0.5
        assert self.c.tool_opacity == 0.5

    def test_colors(self):
        c = QColor(255, 0, 0)
        self.c.set_foreground_color(c)
        assert self.c.tool_color == c


class TestCropTool:
    def setup_method(self):
        self.c = CanvasView()
        self.tool = CropTool()

    def test_activate_crop(self):
        self.tool.press(self.c, QPointF(10, 10), Qt.NoModifier)
        assert self.c.crop_active

    def test_crop_then_apply(self):
        self.tool.press(self.c, QPointF(5, 5), Qt.NoModifier)
        self.tool.move(self.c, QPointF(5, 5), QPointF(100, 80), Qt.NoModifier)
        self.tool.apply(self.c)
        assert not self.c.crop_active

    def test_crop_cancel(self):
        self.tool.press(self.c, QPointF(10, 10), Qt.NoModifier)
        self.tool.cancel(self.c)
        assert not self.c.crop_active

    def test_handle_drag(self):
        self.tool.press(self.c, QPointF(10, 10), Qt.NoModifier)
        self.tool.move(self.c, QPointF(10, 10), QPointF(100, 80), Qt.NoModifier)
        self.tool.release(self.c, QPointF(100, 80), Qt.NoModifier)
        assert hasattr(self.c, 'crop_drag_handle')


class TestLayerAdvanced:
    def test_init_with_name(self):
        l = Layer(100, 80, "test")
        assert l.name == "test"
        assert l.image.width() == 100

    def test_opacity_no_clamping(self):
        l = Layer(50, 50)
        l.opacity = -0.1
        assert l.opacity == -0.1

    def test_visibility(self):
        l = Layer(50, 50)
        l.visible = False
        assert not l.visible

    def test_locked(self):
        l = Layer(50, 50)
        l.locked = True
        assert l.locked

    def test_group(self):
        g = GroupLayer("g")
        assert g.name == "g"
        l = Layer(30, 30, "child")
        g.add_child(l)
        assert len(g.children) == 1
        g.remove_child(l)
        assert len(g.children) == 0

    def test_adjustment_layer(self):
        func = adjustment_brightness_contrast
        adj = AdjustmentLayer(100, 100, "test", func, {"brightness": 30})
        assert adj.filter_func == func
        img = QImage(20, 20, QImage.Format_ARGB32)
        img.fill(QColor(100, 100, 100).rgb())
        result = adj.filter_func(img, adj.params)
        assert result is not None


class TestLayerStack:
    def setup_method(self):
        self.ls = LayerStack(100, 100)

    def test_add(self):
        self.ls.add_layer("new")
        assert len(self.ls.layers) == 2
        assert self.ls.active is not None

    def test_background_add(self):
        bg = self.ls.layers[0]
        assert bg.name == "Background"
        assert bg.image.width() == 100

    def test_composite(self):
        result = self.ls.composite()
        assert result is not None


class TestHistory:
    def test_push_undo_redo(self):
        h = HistoryManager(max_states=10)
        ls = LayerStack(50, 50)
        h.push("init", ls.layers, ls.active_index)
        ls.add_layer("new")
        h.push("add", ls.layers, ls.active_index)
        assert h.can_undo()
        h.undo(ls)
        assert h.can_redo()
        h.redo(ls)

    def test_max_states(self):
        h = HistoryManager(max_states=3)
        ls = LayerStack(50, 50)
        h.push("s1", ls.layers, ls.active_index)
        h.push("s2", ls.layers, ls.active_index)
        h.push("s3", ls.layers, ls.active_index)
        h.push("s4", ls.layers, ls.active_index)
        assert len(h.stack) <= 3

    def test_empty(self):
        h = HistoryManager()
        assert not h.can_undo()
        assert not h.can_redo()


class TestBrushEngine:
    def test_circle_tip(self):
        tip = CircleTip()
        img = QImage(30, 30, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        from PyQt5.QtGui import QPainter
        p = QPainter(img)
        tip.apply(p, 15, 15, 1.0, 10)
        p.end()
        assert img.pixelColor(15, 15).alpha() > 0

    def test_engine_render(self):
        engine = BrushEngine()
        engine.size = 10
        img = QImage(30, 30, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        from PyQt5.QtGui import QPainter
        p = QPainter(img)
        engine.render(p, [QPointF(15, 15)], QColor(0, 255, 0))
        p.end()
        assert img.pixelColor(15, 15).alpha() > 0


class TestFilters:
    def test_gaussian_blur(self):
        img = QImage(10, 10, QImage.Format_ARGB32)
        img.fill(QColor(100, 150, 200).rgb())
        result = gaussian_blur(img, 2)
        assert result is not None

    def test_brightness_contrast(self):
        img = QImage(10, 10, QImage.Format_ARGB32)
        img.fill(QColor(100, 100, 100).rgb())
        result = adjustment_brightness_contrast(img, {"brightness": 30, "contrast": 20})
        assert result is not None

    def test_adjustment_curves(self):
        img = QImage(10, 10, QImage.Format_ARGB32)
        img.fill(QColor(100, 100, 100).rgb())
        result = adjustment_curves(img, {"points": [(0, 0), (0.5, 0.3), (1, 1)]})
        assert result is not None


class TestGradient:
    def test_stop(self):
        s = GradientStop(0.0, QColor(255, 0, 0))
        assert s.position == 0.0
        assert s.color == QColor(255, 0, 0)

    def test_gradient_default(self):
        g = Gradient()
        g.add_stop(0.0, QColor(0, 0, 0))
        g.add_stop(1.0, QColor(255, 255, 255))
        assert len(g.stops) == 2


class TestSnapping:
    def test_enabled(self):
        e = SnappingEngine()
        assert e.enabled

    def test_snap_point_qpointf(self):
        e = SnappingEngine()
        e.enabled = False
        pt, info = e.snap_point(QPointF(17, 10))
        assert pt == QPointF(17, 10)

    def test_snap_grid(self):
        e = SnappingEngine()
        e.enabled = True
        e.snap_to_grid = True
        pt, info = e.snap_point(QPointF(17, 10), grid_spacing=10)
        assert pt.x() == 20


class TestMoveTool:
    def test_drag(self):
        c = CanvasView()
        tool = MoveTool()
        tool.press(c, QPointF(10, 10), Qt.NoModifier)
        assert c.dragging_layer
        tool.release(c, QPointF(30, 30), Qt.NoModifier)
        assert not c.dragging_layer


class TestPenTool:
    def test_pen(self):
        c = CanvasView()
        tool = PenTool()
        tool.press(c, QPointF(50, 50), Qt.NoModifier)
        assert len(c.pen_path) == 1
        tool.cancel(c)
        assert not c.pen_path


class TestFileFormats:
    def test_filters(self):
        f = get_open_filter()
        assert "PNG" in f
        assert "WebP" in f

    def test_registry(self):
        assert '.psd' in FORMAT_REGISTRY
        assert '.webp' in FORMAT_REGISTRY

    def test_qimage_pil(self):
        img = QImage(10, 10, QImage.Format_RGBA8888)
        img.fill(QColor(100, 150, 200, 255).rgb())
        pil = qimage_to_pil(img)
        assert pil.size == (10, 10)
        q2 = pil_to_qimage(pil)
        assert q2.width() == 10


class TestSettings:
    def test_get_set(self):
        m = SettingsManager()
        m.set("k", "v")
        assert m.get("k") == "v"
        assert m.get("nope", "d") == "d"
