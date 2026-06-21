"""
Stress tests for reverseaffinity.
Mark with @pytest.mark.stress to skip in normal test runs.
"""
import os
import tempfile
import time
import unittest
import numpy as np
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QImage, QPainter

from editor.canvas import CanvasView
from editor.layers import Layer, LayerStack
from tests.test_data import solid_image


class TestOpenManyImages(unittest.TestCase):
    def test_open_50_images_sequentially(self):
        tmpdir = tempfile.mkdtemp()
        paths = []
        for i in range(50):
            path = os.path.join(tmpdir, f"img_{i}.png")
            img = solid_image(100, 100, QColor(i * 5 % 256, 0, 0))
            img.save(path)
            paths.append(path)
        canvas = CanvasView()
        for path in paths:
            result = canvas.open_image(path)
            self.assertTrue(result)
        for path in paths:
            os.remove(path)
        os.rmdir(tmpdir)


class TestManyUndoRedo(unittest.TestCase):
    def test_1000_undo_redo(self):
        canvas = CanvasView()
        canvas.new_image(20, 20, Qt.white)
        canvas.history.push("Init", canvas.layer_stack.layers, canvas.layer_stack.active_index)
        for i in range(500):
            canvas.tool_color = QColor((i * 50) % 256, 0, 0)
            canvas.draw_point(QPointF(i % 20, i // 20 % 20))
            canvas.history.push(f"Draw {i}", canvas.layer_stack.layers, canvas.layer_stack.active_index)
        for _ in range(500):
            if not canvas.history.can_undo():
                break
            canvas.history.undo(canvas.layer_stack)
        for _ in range(500):
            if not canvas.history.can_redo():
                break
            canvas.history.redo(canvas.layer_stack)
        self.assertTrue(len(canvas.layer_stack.layers) >= 1)


class TestLongBrushStroke(unittest.TestCase):
    def test_brush_10000_points(self):
        canvas = CanvasView()
        canvas.new_image(200, 200, Qt.white)
        canvas.tool_color = QColor(0, 0, 0)
        canvas.tool_size = 2
        t0 = time.perf_counter()
        for i in range(10000):
            x = i % 200
            y = (i // 200) % 200
            canvas.draw_point(QPointF(x, y))
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 65.0, f"10000 points took {elapsed:.2f}s")


class TestDeepLayerStack(unittest.TestCase):
    def test_100_layers(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        for i in range(99):
            canvas.layer_stack.add_layer(f"L{i}")
        self.assertEqual(len(canvas.layer_stack.layers), 100)
        composite = canvas.layer_stack.composite()
        self.assertFalse(composite.isNull())

    def test_100_layers_composite_time(self):
        canvas = CanvasView()
        canvas.new_image(100, 100, Qt.white)
        for i in range(99):
            canvas.layer_stack.add_layer(f"L{i}")
        t0 = time.perf_counter()
        composite = canvas.layer_stack.composite()
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 10.0, f"100 layer composite took {elapsed:.2f}s")
        self.assertFalse(composite.isNull())


class TestLargeSelection(unittest.TestCase):
    def test_selection_on_16k_image(self):
        w, h = 15360, 8640
        canvas = CanvasView()
        canvas.new_image(w, h, Qt.white)
        from PyQt5.QtCore import QRect
        canvas.set_selection_rect(QRect(0, 0, w, h))
        self.assertTrue(canvas.has_selection())
        canvas.clear_selection()
        self.assertFalse(canvas.has_selection())
