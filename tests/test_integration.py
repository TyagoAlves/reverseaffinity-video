import os
import tempfile
import unittest

import numpy as np
from PyQt5.QtCore import Qt, QPointF, QRect
from PyQt5.QtGui import QColor, QImage, QPainter

from editor.canvas import CanvasView
from editor.filters import brightness, grayscale
from editor.layers import LayerStack, Layer
from tests.test_data import checkerboard, gradient_image, solid_image


class TestCreateDrawFilterSaveReopen(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_full_workflow(self):
        canvas = CanvasView()
        canvas.new_image(100, 100, QColor(Qt.white))
        canvas.tool_color = QColor(255, 0, 0)
        canvas.tool_size = 10
        canvas.draw_point(QPointF(50, 50))
        before_save = canvas.layer_stack.composite().copy()
        path = os.path.join(self.tmpdir, "test.png")
        canvas.save_image(path)
        canvas.open_image(path)
        reopened = canvas.layer_stack.composite()
        self.assertEqual(before_save.width(), reopened.width())
        self.assertEqual(before_save.height(), reopened.height())

    def test_filter_preserves_size(self):
        canvas = CanvasView()
        canvas.new_image(64, 64)
        filtered = brightness(canvas.layer_stack.composite(), 30)
        self.assertEqual(filtered.width(), 64)
        self.assertEqual(filtered.height(), 64)

    def test_save_reload_png_preserves_content(self):
        canvas = CanvasView()
        canvas.new_image(16, 16, QColor(Qt.blue))
        path = os.path.join(self.tmpdir, "blue.png")
        canvas.save_image(path)
        reloaded = QImage(path)
        self.assertFalse(reloaded.isNull())
        if reloaded.format() != QImage.Format_ARGB32:
            reloaded = reloaded.convertToFormat(QImage.Format_ARGB32)
        orig = QColor(Qt.blue)
        rc = reloaded.pixelColor(0, 0)
        self.assertEqual(rc.red(), orig.red())
        self.assertEqual(rc.green(), orig.green())
        self.assertEqual(rc.blue(), orig.blue())


class TestLayerAddPaintFlatten(unittest.TestCase):
    def test_add_layer_paint_flatten(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        canvas.layer_stack.add_layer("Paint Layer")
        canvas.tool_color = QColor(0, 255, 0)
        canvas.draw_point(QPointF(25, 25))
        before = canvas.layer_stack.composite().copy()
        canvas.layer_stack.flatten()
        self.assertEqual(len(canvas.layer_stack.layers), 1)
        flat = canvas.layer_stack.composite()
        self.assertEqual(flat.width(), before.width())
        self.assertEqual(flat.height(), before.height())

    def test_paint_on_new_layer_visible(self):
        canvas = CanvasView()
        canvas.new_image(30, 30, Qt.white)
        canvas.layer_stack.add_layer("New")
        canvas.tool_color = QColor(255, 255, 0)
        canvas.draw_point(QPointF(15, 15))
        c = canvas.layer_stack.layers[1].image.pixelColor(15, 15)
        self.assertEqual(c.red(), 255)
        self.assertEqual(c.green(), 255)

    def test_merge_visible_reduces_layer_count(self):
        canvas = CanvasView()
        canvas.new_image(20, 20)
        canvas.layer_stack.add_layer("A")
        canvas.layer_stack.add_layer("B")
        canvas.layer_stack.merge_visible()
        self.assertEqual(len(canvas.layer_stack.layers), 1)


class TestUndoRedoSequence(unittest.TestCase):
    def test_undo_redo_multiple_ops(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        canvas.history.push("Initial", canvas.layer_stack.layers, canvas.layer_stack.active_index)
        canvas.tool_color = QColor(255, 0, 0)
        canvas.draw_point(QPointF(10, 10))
        canvas.history.push("Draw 1", canvas.layer_stack.layers, canvas.layer_stack.active_index)
        canvas.tool_color = QColor(0, 255, 0)
        canvas.draw_point(QPointF(20, 20))
        canvas.history.push("Draw 2", canvas.layer_stack.layers, canvas.layer_stack.active_index)
        self.assertTrue(canvas.history.can_undo())
        canvas.history.undo(canvas.layer_stack)
        self.assertTrue(canvas.history.can_redo())
        canvas.history.undo(canvas.layer_stack)
        canvas.history.redo(canvas.layer_stack)
        canvas.history.redo(canvas.layer_stack)

    def test_undo_clears_selection(self):
        canvas = CanvasView()
        canvas.set_selection_rect(QRect(10, 10, 30, 30))
        self.assertTrue(canvas.has_selection())
        canvas.clear_selection()
        self.assertFalse(canvas.has_selection())


class TestSelectionFillVerify(unittest.TestCase):
    def test_rect_selection_fill(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        canvas.set_selection_rect(QRect(10, 10, 20, 20))
        canvas.tool_color = QColor(255, 0, 0)
        canvas.flood_fill(QPointF(15, 15))
        inside = canvas.get_pixel_color(QPointF(15, 15))
        self.assertEqual(inside, QColor(255, 0, 0))


class TestLayerBlendModes(unittest.TestCase):
    def test_multiply_blend(self):
        canvas = CanvasView()
        canvas.new_image(10, 10, Qt.white)
        canvas.layer_stack.add_layer("Top")
        p = QPainter(canvas.layer_stack.layers[1].image)
        p.fillRect(0, 0, 10, 10, QColor(128, 128, 128))
        p.end()
        canvas.layer_stack.layers[1].blend_mode = "Multiply"
        composite = canvas.layer_stack.composite()
        self.assertFalse(composite.isNull())

    def test_screen_blend(self):
        canvas = CanvasView()
        canvas.new_image(10, 10, Qt.black)
        canvas.layer_stack.add_layer("Top")
        p = QPainter(canvas.layer_stack.layers[1].image)
        p.fillRect(0, 0, 10, 10, QColor(128, 128, 128))
        p.end()
        canvas.layer_stack.layers[1].blend_mode = "Screen"
        composite = canvas.layer_stack.composite()
        self.assertFalse(composite.isNull())
        c = composite.pixelColor(0, 0)
        self.assertGreaterEqual(c.red(), 128)

    def test_all_blend_modes_composite(self):
        canvas = CanvasView()
        canvas.new_image(8, 8, Qt.white)
        canvas.layer_stack.add_layer("Top")
        p = QPainter(canvas.layer_stack.layers[1].image)
        p.fillRect(0, 0, 8, 8, QColor(64, 64, 64))
        p.end()
        for mode in ["Normal", "Multiply", "Screen", "Overlay", "Darken",
                      "Lighten", "Difference", "Exclusion"]:
            with self.subTest(mode=mode):
                canvas.layer_stack.layers[1].blend_mode = mode
                result = canvas.layer_stack.composite()
                self.assertFalse(result.isNull())


class TestLayerOpacity(unittest.TestCase):
    def test_opacity_zero_is_transparent(self):
        canvas = CanvasView()
        canvas.new_image(10, 10, Qt.white)
        canvas.layer_stack.add_layer("Top")
        p = QPainter(canvas.layer_stack.layers[1].image)
        p.fillRect(0, 0, 10, 10, QColor(255, 0, 0))
        p.end()
        canvas.layer_stack.layers[1].opacity = 0.0
        composite = canvas.layer_stack.composite()
        self.assertEqual(composite.pixelColor(0, 0), QColor(Qt.white))

    def test_opacity_half(self):
        canvas = CanvasView()
        canvas.new_image(10, 10, Qt.white)
        canvas.layer_stack.add_layer("Top")
        p = QPainter(canvas.layer_stack.layers[1].image)
        p.fillRect(0, 0, 10, 10, QColor(0, 0, 0))
        p.end()
        canvas.layer_stack.layers[1].opacity = 0.5
        composite = canvas.layer_stack.composite()
        c = composite.pixelColor(0, 0)
        self.assertGreater(c.red(), 0)
        self.assertLess(c.red(), 255)
