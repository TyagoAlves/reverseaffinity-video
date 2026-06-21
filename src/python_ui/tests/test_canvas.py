import unittest
import os
import tempfile
from PyQt5.QtCore import Qt, QPointF, QPoint, QRect
from PyQt5.QtGui import QImage, QColor, QPainter

from editor.canvas import CanvasView
from editor.layers import Layer, LayerStack


class TestCanvasComposite(unittest.TestCase):
    def setUp(self):
        self.canvas = CanvasView()

    def test_composite_returns_image(self):
        result = self.canvas.layer_stack.composite()
        self.assertIsInstance(result, QImage)
        self.assertFalse(result.isNull())

    def test_composite_size(self):
        result = self.canvas.layer_stack.composite()
        self.assertEqual(result.width(), 800)
        self.assertEqual(result.height(), 600)

    def test_composite_after_clear(self):
        self.canvas.layer_stack.clear()
        result = self.canvas.layer_stack.composite()
        self.assertTrue(result.isNull())

    def test_composite_with_multiple_layers(self):
        self.canvas.layer_stack.add_layer("Overlay")
        result = self.canvas.layer_stack.composite()
        self.assertFalse(result.isNull())

    def test_composite_invisible_layer(self):
        self.canvas.layer_stack.add_layer("Hidden")
        self.canvas.layer_stack.layers[1].visible = False
        result = self.canvas.layer_stack.composite()
        self.assertIsInstance(result, QImage)


class TestCanvasSelection(unittest.TestCase):
    def setUp(self):
        self.canvas = CanvasView()

    def test_no_selection_initially(self):
        self.assertFalse(self.canvas.has_selection())

    def test_set_rect_selection(self):
        self.canvas.set_selection_rect(QRect(10, 10, 50, 50))
        self.assertTrue(self.canvas.has_selection())

    def test_set_ellipse_selection(self):
        self.canvas.set_selection_ellipse(QRect(10, 10, 50, 50))
        self.assertTrue(self.canvas.has_selection())

    def test_clear_selection(self):
        self.canvas.set_selection_rect(QRect(10, 10, 50, 50))
        self.canvas.clear_selection()
        self.assertFalse(self.canvas.has_selection())


class TestCanvasFileIO(unittest.TestCase):
    def setUp(self):
        self.canvas = CanvasView()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_save_png(self):
        path = os.path.join(self.tmpdir, "test.png")
        result = self.canvas.save_image(path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(path))

    def test_save_and_reload(self):
        path = os.path.join(self.tmpdir, "roundtrip.png")
        self.canvas.save_image(path)
        self.canvas.open_image(path)
        self.assertEqual(self.canvas.layer_stack.layers[0].image.width(), 800)

    def test_export_png(self):
        path = os.path.join(self.tmpdir, "export.png")
        result = self.canvas.export_png(path)
        self.assertTrue(result)

    def test_export_jpg(self):
        path = os.path.join(self.tmpdir, "export.jpg")
        result = self.canvas.export_jpg(path)
        self.assertTrue(result)

    def test_export_jpg_quality(self):
        path = os.path.join(self.tmpdir, "export_q.jpg")
        result = self.canvas.export_jpg(path, 85)
        self.assertTrue(result)

    def test_open_nonexistent(self):
        result = self.canvas.open_image("/nonexistent/path.png")
        self.assertFalse(result)

    def test_new_image(self):
        self.canvas.new_image(100, 200)
        self.assertEqual(self.canvas.layer_stack.layers[0].image.width(), 100)
        self.assertEqual(self.canvas.layer_stack.layers[0].image.height(), 200)

    def test_new_image_custom_bg(self):
        self.canvas.new_image(50, 50, QColor(Qt.red))
        c = self.canvas.layer_stack.layers[0].image.pixelColor(0, 0)
        self.assertEqual(c, QColor(Qt.red))


class TestCanvasZoomPan(unittest.TestCase):
    def setUp(self):
        self.canvas = CanvasView()

    def test_zoom_in(self):
        initial = self.canvas.zoom_level
        self.canvas.zoom_in()
        self.assertGreater(self.canvas.zoom_level, initial)

    def test_zoom_out(self):
        self.canvas.zoom_in()
        self.canvas.zoom_out()
        self.assertAlmostEqual(self.canvas.zoom_level, 1.0, places=5)

    def test_zoom_100(self):
        self.canvas.zoom_in()
        self.canvas.zoom_100()
        self.assertEqual(self.canvas.zoom_level, 1.0)

    def test_tool_size(self):
        self.canvas.set_tool_size(10)
        self.assertEqual(self.canvas.tool_size, 10)
        self.canvas.set_tool_size(0)
        self.assertEqual(self.canvas.tool_size, 1)

    def test_tool_opacity(self):
        self.canvas.set_tool_opacity(50)
        self.assertEqual(self.canvas.tool_opacity, 0.5)


class TestCanvasDrawing(unittest.TestCase):
    def setUp(self):
        self.canvas = CanvasView()
        self.canvas.tool_color = QColor(255, 0, 0)
        self.canvas.tool_size = 2

    def test_draw_point_modifies_layer(self):
        original = self.canvas.layer_stack.composite().copy()
        self.canvas.draw_point(QPointF(10, 10))
        new = self.canvas.layer_stack.composite()
        self.assertFalse(original == new)

    def test_erase_point(self):
        self.canvas.draw_point(QPointF(10, 10))
        self.canvas.erase_point(QPointF(10, 10))

    def test_get_pixel_color(self):
        c = self.canvas.get_pixel_color(QPointF(0, 0))
        self.assertIsInstance(c, QColor)

    def test_get_pixel_color_out_of_bounds(self):
        c = self.canvas.get_pixel_color(QPointF(-100, -100))
        self.assertIsNotNone(c)

    def test_flood_fill(self):
        self.canvas.flood_fill(QPointF(400, 300))
        c = self.canvas.get_pixel_color(QPointF(400, 300))
        self.assertEqual(c, self.canvas.tool_color)


class TestCanvasMoveLayer(unittest.TestCase):
    def setUp(self):
        self.canvas = CanvasView()

    def test_move_layer_content(self):
        self.canvas.layer_stack.active.locked = False
        result = self.canvas.move_layer_content(10, 10)
        self.assertTrue(result)

    def test_move_layer_content_zero(self):
        result = self.canvas.move_layer_content(0, 0)
        self.assertFalse(result)

    def test_move_layer_content_locked(self):
        self.canvas.layer_stack.active.locked = True
        result = self.canvas.move_layer_content(10, 10)
        self.assertFalse(result)


class TestCanvasTempSave(unittest.TestCase):
    def setUp(self):
        self.canvas = CanvasView()
        self.canvas.new_image(50, 50, Qt.white)
        self.canvas.tool_color = QColor(255, 0, 0)

    def test_temp_save_restore(self):
        self.canvas.draw_point(QPointF(10, 10))
        self.canvas.temp_save_layer()
        orig = self.canvas.layer_stack.active.image.copy()
        self.canvas.draw_point(QPointF(20, 20))
        self.canvas.temp_restore_layer()
        restored = self.canvas.layer_stack.active.image
        self.assertEqual(orig, restored)

    def test_temp_save_no_active_layer(self):
        self.canvas.layer_stack.layers.clear()
        self.canvas.temp_save_layer()
        self.canvas.temp_restore_layer()

    def test_save_state(self):
        self.canvas._save_state("Test")
        self.assertTrue(self.canvas.history.can_undo())

    def test_draw_gradient(self):
        self.canvas.draw_gradient(QPointF(0, 0), QPointF(50, 50))
        c = self.canvas.get_pixel_color(QPointF(0, 0))
        self.assertNotEqual((c.red(), c.green(), c.blue()), (255, 255, 255))

    def test_draw_gradient_locked_layer(self):
        self.canvas.layer_stack.active.locked = True
        self.canvas.draw_gradient(QPointF(0, 0), QPointF(50, 50))

    def test_draw_rect_shape(self):
        self.canvas.tool_size = 2
        self.canvas.draw_rect_shape(QPointF(5, 5), QPointF(20, 20))
        c = self.canvas.get_pixel_color(QPointF(5, 5))
        self.assertEqual(c, self.canvas.tool_color)

    def test_draw_ellipse_shape(self):
        self.canvas.tool_size = 5
        self.canvas.draw_ellipse_shape(QPointF(5, 5), QPointF(25, 20))
        c = self.canvas.get_pixel_color(QPointF(5, 13))
        self.assertNotEqual((c.red(), c.green(), c.blue()), (255, 255, 255))

    def test_apply_pixel_op(self):
        self.canvas._apply_pixel_op(QRect(0, 0, 10, 10), lambda arr, s: arr)
        c = self.canvas.get_pixel_color(QPointF(5, 5))
        self.assertEqual(c, QColor(255, 255, 255))


if __name__ == "__main__":
    unittest.main()
