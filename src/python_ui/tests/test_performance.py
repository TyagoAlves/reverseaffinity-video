"""
Performance benchmarks for reverseaffinity.
Mark with @pytest.mark.perf to skip in normal test runs.
"""
import time
import unittest
import numpy as np
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QImage, QColor, QPainter

from editor.canvas import CanvasView
from editor.filters import (
    grayscale, invert, brightness, gaussian_blur, sharpen,
    to_array, from_array,
)
from editor.layers import (
    Layer, LayerStack, _float_array_to_qimage, _qimage_to_float_array,
    BLEND_FUNCS,
)
from tests.test_data import solid_image


def _timeit(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


class TestBlendModeBenchmarks(unittest.TestCase):
    SIZES = [(1920, 1080), (3840, 2160)]

    def _make_layers(self, w, h):
        base = np.random.rand(h, w, 4).astype(np.float32)
        top = np.random.rand(h, w, 4).astype(np.float32)
        return base, top

    def test_blend_modes_4k(self):
        w, h = 1920, 1080
        base, top = self._make_layers(w, h)
        for name, func in BLEND_FUNCS.items():
            _, elapsed = _timeit(func, base[:, :, :3], top[:, :, :3])
            self.assertLess(elapsed, 5.0, f"{name} took {elapsed:.3f}s")

    def test_blend_modes_8k(self):
        w, h = 3840, 2160
        base, top = self._make_layers(w, h)
        for name, func in BLEND_FUNCS.items():
            _, elapsed = _timeit(func, base[:, :, :3], top[:, :, :3])
            self.assertLess(elapsed, 20.0, f"{name} took {elapsed:.3f}s")


class TestFilterBenchmarks(unittest.TestCase):
    def test_grayscale_4k(self):
        img = solid_image(1920, 1080)
        _, elapsed = _timeit(grayscale, img)
        self.assertLess(elapsed, 5.0)

    def test_invert_4k(self):
        img = solid_image(1920, 1080)
        _, elapsed = _timeit(invert, img)
        self.assertLess(elapsed, 5.0)

    def test_brightness_4k(self):
        img = solid_image(1920, 1080)
        _, elapsed = _timeit(brightness, img, 50)
        self.assertLess(elapsed, 5.0)

    def test_gaussian_blur_4k(self):
        img = solid_image(1920, 1080)
        _, elapsed = _timeit(gaussian_blur, img, 3)
        self.assertLess(elapsed, 10.0)

    def test_sharpen_4k(self):
        img = solid_image(1920, 1080)
        _, elapsed = _timeit(sharpen, img, 1.0)
        self.assertLess(elapsed, 10.0)


class TestFileIOBenchmarks(unittest.TestCase):
    def test_image_conversion_roundtrip_4k(self):
        w, h = 3840, 2160
        arr = np.random.rand(h, w, 4).astype(np.float32)
        _, t1 = _timeit(_float_array_to_qimage, arr, w, h)
        self.assertLess(t1, 5.0)


class TestNumpyVsPurePython(unittest.TestCase):
    def test_numpy_blend_faster(self):
        size = 5000
        b = np.random.rand(size, 3).astype(np.float32)
        l = np.random.rand(size, 3).astype(np.float32)

        def numpy_loop():
            return b * l

        def python_loop():
            out = np.empty_like(b)
            for i in range(size):
                out[i] = b[i] * l[i]
            return out

        _, t_np = _timeit(numpy_loop)
        _, t_py = _timeit(python_loop)
        self.assertLess(t_np, t_py, "numpy should be faster than Python loop")
