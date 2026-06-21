import unittest
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor

from editor.layers import (
    Layer, AdjustmentLayer, GroupLayer, LayerStack,
    BLEND_FUNCS, BLEND_MODES,
    _float_array_to_qimage, _qimage_to_float_array,
)


def make_test_qimage(w=4, h=4, color=QColor(128, 64, 32)):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(color)
    return img


class TestBlendFunctions(unittest.TestCase):
    def setUp(self):
        self.b = np.array([[[0.2, 0.4, 0.6]]], dtype=np.float32)
        self.l = np.array([[[0.8, 0.6, 0.4]]], dtype=np.float32)

    def test_normal(self):
        r = BLEND_FUNCS["Normal"](self.b, self.l)
        np.testing.assert_array_equal(r, self.l)

    def test_multiply(self):
        r = BLEND_FUNCS["Multiply"](self.b, self.l)
        expected = self.b * self.l
        np.testing.assert_array_almost_equal(r, expected)

    def test_screen(self):
        r = BLEND_FUNCS["Screen"](self.b, self.l)
        expected = 1.0 - (1.0 - self.b) * (1.0 - self.l)
        np.testing.assert_array_almost_equal(r, expected)

    def test_darken(self):
        r = BLEND_FUNCS["Darken"](self.b, self.l)
        np.testing.assert_array_equal(r, np.minimum(self.b, self.l))

    def test_lighten(self):
        r = BLEND_FUNCS["Lighten"](self.b, self.l)
        np.testing.assert_array_equal(r, np.maximum(self.b, self.l))

    def test_difference(self):
        r = BLEND_FUNCS["Difference"](self.b, self.l)
        np.testing.assert_array_almost_equal(r, np.abs(self.b - self.l))

    def test_exclusion(self):
        r = BLEND_FUNCS["Exclusion"](self.b, self.l)
        np.testing.assert_array_almost_equal(r, self.b + self.l - 2.0 * self.b * self.l)

    def test_overlay(self):
        r = BLEND_FUNCS["Overlay"](self.b, self.l)
        mask = self.b < 0.5
        expected = np.where(mask, 2.0 * self.b * self.l, 1.0 - 2.0 * (1.0 - self.b) * (1.0 - self.l))
        np.testing.assert_array_almost_equal(r, expected)

    def test_all_blend_modes_listed(self):
        for mode in ["Normal", "Multiply", "Screen", "Overlay", "Darken", "Lighten",
                      "Color Dodge", "Color Burn", "Hard Light", "Soft Light",
                      "Difference", "Exclusion"]:
            self.assertIn(mode, BLEND_FUNCS)

    def test_color_dodge_division_by_zero(self):
        l_zero = np.zeros_like(self.l)
        r = BLEND_FUNCS["Color Dodge"](self.b, l_zero)
        self.assertFalse(np.any(np.isnan(r)))
        self.assertFalse(np.any(np.isinf(r)))

    def test_color_burn_division_by_zero(self):
        l_zero = np.zeros_like(self.l)
        r = BLEND_FUNCS["Color Burn"](self.b, l_zero)
        self.assertFalse(np.any(np.isnan(r)))
        self.assertFalse(np.any(np.isinf(r)))

    def test_hard_light(self):
        r = BLEND_FUNCS["Hard Light"](self.b, self.l)
        self.assertEqual(r.shape, self.b.shape)
        self.assertTrue(np.all(r >= 0.0))
        self.assertTrue(np.all(r <= 1.0))

    def test_soft_light(self):
        r = BLEND_FUNCS["Soft Light"](self.b, self.l)
        self.assertEqual(r.shape, self.b.shape)
        self.assertTrue(np.all(r >= 0.0))
        self.assertTrue(np.all(r <= 1.0))

    def test_color_dodge_basic(self):
        b = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        l = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        r = BLEND_FUNCS["Color Dodge"](b, l)
        self.assertTrue(np.all(r >= 0.0))
        self.assertTrue(np.all(r <= 1.0))

    def test_color_burn_basic(self):
        b = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        l = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        r = BLEND_FUNCS["Color Burn"](b, l)
        self.assertTrue(np.all(r >= 0.0))
        self.assertTrue(np.all(r <= 1.0))

    def test_subtract(self):
        b = np.array([[[0.8, 0.8, 0.8]]], dtype=np.float32)
        l = np.array([[[0.3, 0.3, 0.3]]], dtype=np.float32)
        r = BLEND_FUNCS["Subtract"](b, l)
        expected = np.clip(b - l, 0, 1)
        np.testing.assert_array_almost_equal(r, expected)

    def test_add(self):
        b = np.array([[[0.3, 0.3, 0.3]]], dtype=np.float32)
        l = np.array([[[0.4, 0.4, 0.4]]], dtype=np.float32)
        r = BLEND_FUNCS["Add"](b, l)
        expected = np.clip(b + l, 0, 1)
        np.testing.assert_array_almost_equal(r, expected)

    def test_hue(self):
        r = BLEND_FUNCS["Hue"](self.b, self.l)
        self.assertEqual(r.shape, self.b.shape)

    def test_saturation(self):
        r = BLEND_FUNCS["Saturation"](self.b, self.l)
        self.assertEqual(r.shape, self.b.shape)

    def test_color_blend(self):
        r = BLEND_FUNCS["Color"](self.b, self.l)
        self.assertEqual(r.shape, self.b.shape)

    def test_luminosity(self):
        r = BLEND_FUNCS["Luminosity"](self.b, self.l)
        self.assertEqual(r.shape, self.b.shape)


class TestLayer(unittest.TestCase):
    def test_create_background(self):
        layer = Layer(100, 200, "Background")
        self.assertEqual(layer.name, "Background")
        self.assertEqual(layer.image.width(), 100)
        self.assertEqual(layer.image.height(), 200)
        self.assertTrue(layer.visible)
        self.assertFalse(layer.locked)
        self.assertEqual(layer.opacity, 1.0)
        self.assertEqual(layer.blend_mode, "Normal")

    def test_create_transparent(self):
        layer = Layer(50, 50, "Layer 1", fill=None)
        self.assertEqual(layer.image.pixelColor(0, 0), QColor(Qt.transparent))

    def test_create_custom_fill(self):
        layer = Layer(10, 10, "Custom", fill=QColor(255, 0, 0))
        self.assertEqual(layer.image.pixelColor(0, 0), QColor(255, 0, 0))

    def test_copy(self):
        layer = Layer(20, 20, "Test")
        layer.opacity = 0.5
        layer.blend_mode = "Multiply"
        layer.locked = True
        c = layer.copy()
        self.assertEqual(c.name, "Test (copy)")
        self.assertEqual(c.opacity, layer.opacity)
        self.assertEqual(c.blend_mode, layer.blend_mode)
        self.assertEqual(c.locked, layer.locked)
        self.assertEqual(c.image.width(), layer.image.width())

    def test_zero_size(self):
        layer = Layer(0, 0, "Zero")
        self.assertEqual(layer.image.width(), 0)
        self.assertEqual(layer.image.height(), 0)


class TestAdjustmentLayer(unittest.TestCase):
    def test_create(self):
        def dummy(img, params):
            return img
        adj = AdjustmentLayer(100, 100, "Test", dummy, {"val": 1})
        self.assertEqual(adj.name, "Test")
        self.assertIsNotNone(adj.filter_func)
        self.assertEqual(adj.params, {"val": 1})


class TestGroupLayer(unittest.TestCase):
    def test_create(self):
        g = GroupLayer("My Group")
        self.assertEqual(g.name, "My Group")
        self.assertEqual(g.children, [])
        self.assertTrue(g.visible)

    def test_add_child(self):
        g = GroupLayer("Group")
        child = Layer(10, 10, "Child")
        g.add_child(child)
        self.assertEqual(len(g.children), 1)
        self.assertIn(child, g.children)

    def test_remove_child(self):
        g = GroupLayer("Group")
        child = Layer(10, 10, "Child")
        g.add_child(child)
        g.remove_child(child)
        self.assertEqual(len(g.children), 0)

    def test_remove_nonexistent_child(self):
        g = GroupLayer("Group")
        child = Layer(10, 10, "Child")
        g.remove_child(child)
        self.assertEqual(len(g.children), 0)


class TestLayerMasks(unittest.TestCase):
    def test_create_layer_without_mask(self):
        layer = Layer(10, 10, "Test")
        self.assertIsNone(layer.mask)

    def test_add_mask_to_layer(self):
        layer = Layer(10, 10, "Test")
        from PyQt5.QtGui import QImage
        mask = QImage(10, 10, QImage.Format_Grayscale8)
        mask.fill(255)
        layer.mask = mask
        self.assertIsNotNone(layer.mask)
        self.assertEqual(layer.mask.width(), 10)
        self.assertEqual(layer.mask.height(), 10)
        self.assertTrue(layer.mask_enabled)

    def test_mask_toggle(self):
        layer = Layer(10, 10, "Test")
        from PyQt5.QtGui import QImage
        mask = QImage(10, 10, QImage.Format_Grayscale8)
        mask.fill(255)
        layer.mask = mask
        self.assertTrue(layer.mask_enabled)
        layer.mask_enabled = False
        self.assertFalse(layer.mask_enabled)
        layer.mask_enabled = True
        self.assertTrue(layer.mask_enabled)

    def test_copy_layer_with_mask(self):
        layer = Layer(10, 10, "Test")
        from PyQt5.QtGui import QImage
        mask = QImage(10, 10, QImage.Format_Grayscale8)
        mask.fill(128)
        layer.mask = mask
        layer.mask_enabled = False
        c = layer.copy()
        self.assertIsNotNone(c.mask)
        self.assertFalse(c.mask_enabled)


class TestLayerStack(unittest.TestCase):
    def setUp(self):
        self.stack = LayerStack(100, 100)

    def test_initial_state(self):
        self.assertEqual(len(self.stack.layers), 1)
        self.assertEqual(self.stack.active_index, 0)
        self.assertIsNotNone(self.stack.active)

    def test_add_layer(self):
        l = self.stack.add_layer("New")
        self.assertEqual(len(self.stack.layers), 2)
        self.assertEqual(self.stack.active_index, 1)
        self.assertEqual(l.name, "New")

    def test_remove_layer_last_remaining(self):
        self.stack.remove_layer(0)
        self.assertEqual(len(self.stack.layers), 1)

    def test_remove_layer_invalid_index(self):
        self.stack.remove_layer(99)
        self.assertEqual(len(self.stack.layers), 1)

    def test_move_layer(self):
        self.stack.add_layer("A")
        self.stack.add_layer("B")
        self.stack.move_layer(2, 0)
        self.assertEqual(self.stack.layers[0].name, "B")

    def test_duplicate_layer(self):
        self.stack.add_layer("Original")
        self.stack.duplicate_layer(1)
        self.assertEqual(len(self.stack.layers), 3)
        self.assertIn("copy", self.stack.layers[2].name)

    def test_flatten(self):
        self.stack.add_layer("A")
        self.stack.add_layer("B")
        self.stack.flatten()
        self.assertEqual(len(self.stack.layers), 1)

    def test_merge_visible_single_layer(self):
        self.stack.merge_visible()
        self.assertEqual(len(self.stack.layers), 1)

    def test_active_property(self):
        self.assertIs(self.stack.active, self.stack.layers[0])

    def test_get_out_of_range(self):
        self.assertIsNone(self.stack._get(-1))
        self.assertIsNone(self.stack._get(999))

    def test_flatten_single_layer(self):
        self.stack.flatten()
        self.assertEqual(len(self.stack.layers), 1)

    def test_composite_empty(self):
        empty = LayerStack(100, 100)
        empty.layers.clear()
        result = empty.composite()
        self.assertTrue(result.isNull())

    def test_composite_with_invisible(self):
        self.stack.add_layer("Invisible")
        self.stack.layers[1].visible = False
        result = self.stack.composite()
        self.assertFalse(result.isNull())

    def test_composite_returns_qimage(self):
        result = self.stack.composite()
        self.assertIsInstance(result, QImage)

    def test_add_background(self):
        self.stack.add_background(QColor(Qt.blue))
        self.assertEqual(self.stack.layers[0].name, "Background")


class TestFloatArrayConversion(unittest.TestCase):
    def test_roundtrip(self):
        arr = np.random.rand(10, 10, 4).astype(np.float32)
        qimg = _float_array_to_qimage(arr, 10, 10)
        self.assertEqual(qimg.width(), 10)
        self.assertEqual(qimg.height(), 10)
        back = _qimage_to_float_array(qimg)
        np.testing.assert_array_almost_equal(arr, back, decimal=2)

    def test_qimage_to_float(self):
        img = make_test_qimage()
        arr = _qimage_to_float_array(img)
        self.assertEqual(arr.shape, (4, 4, 4))
        self.assertEqual(arr.dtype, np.float32)
        self.assertTrue(np.all(arr >= 0.0))
        self.assertTrue(np.all(arr <= 1.0))


if __name__ == "__main__":
    unittest.main()
