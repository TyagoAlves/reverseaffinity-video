"""
Regression tests for reverseaffinity.

Add a test here when fixing a bug, named after the issue/bug description.
This ensures bugs stay fixed.
"""
import unittest

import numpy as np
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QImage, QPainter

from editor.canvas import CanvasView
from editor.filters import (
    brightness, contrast, invert, grayscale,
    gaussian_blur, sharpen,
)
from editor.layers import (
    Layer, LayerStack,
)
from editor.blend_modes import blend_color_dodge as _blend_color_dodge, blend_color_burn as _blend_color_burn
from tests.test_data import solid_image


class TestColorDodgeNoNan(unittest.TestCase):
    """Regression: Color Dodge should not produce NaN when bottom is zero."""

    def test_color_dodge_no_nan(self):
        b = np.zeros((1, 1, 3), dtype=np.float32)
        l = np.ones((1, 1, 3), dtype=np.float32)
        result = _blend_color_dodge(b, l)
        self.assertFalse(np.any(np.isnan(result)))
        self.assertFalse(np.any(np.isinf(result)))


class TestColorBurnNoInf(unittest.TestCase):
    """Regression: Color Burn should not produce inf when top is zero."""

    def test_color_burn_no_inf(self):
        b = np.ones((1, 1, 3), dtype=np.float32)
        l = np.zeros((1, 1, 3), dtype=np.float32)
        result = _blend_color_burn(b, l)
        self.assertFalse(np.any(np.isnan(result)))
        self.assertFalse(np.any(np.isinf(result)))


class TestFilterPreservesAlpha(unittest.TestCase):
    """Regression: Filters should preserve the alpha channel."""

    def test_grayscale_preserves_alpha(self):
        img = QImage(8, 8, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(0, 0, 8, 8, QColor(100, 150, 200, 128))
        p.end()
        alpha_before = QColor(img.pixelColor(0, 0)).alpha()
        result = grayscale(img)
        alpha_after = QColor(result.pixelColor(0, 0)).alpha()
        self.assertEqual(alpha_before, alpha_after)

    def test_invert_preserves_alpha(self):
        img = QImage(8, 8, QImage.Format_ARGB32)
        img.fill(QColor(100, 150, 200, 64))
        alpha_before = QColor(img.pixelColor(0, 0)).alpha()
        result = invert(img)
        alpha_after = QColor(result.pixelColor(0, 0)).alpha()
        self.assertEqual(alpha_before, alpha_after)


class TestBrightnessClipping(unittest.TestCase):
    """Regression: Brightness adjustment should clamp to [0, 255]."""

    def test_brightness_clips_high(self):
        img = QImage(4, 4, QImage.Format_ARGB32)
        img.fill(QColor(200, 200, 200))
        result = brightness(img, 200)
        c = result.pixelColor(0, 0)
        self.assertEqual(c.red(), 255)

    def test_brightness_clips_low(self):
        img = QImage(4, 4, QImage.Format_ARGB32)
        img.fill(QColor(50, 50, 50))
        result = brightness(img, -200)
        c = result.pixelColor(0, 0)
        self.assertEqual(c.red(), 0)


class TestCanvasMemory(unittest.TestCase):
    """Regression: Opening a new image should not crash."""

    def test_multiple_new_images(self):
        canvas = CanvasView()
        for _ in range(10):
            canvas.new_image(100, 100)
            self.assertIsNotNone(canvas.layer_stack.active)
