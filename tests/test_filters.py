import unittest
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor

from editor.filters import (
    to_array, from_array,
    grayscale, invert, brightness, contrast, levels,
    hue_saturation, color_balance, curves,
    gaussian_blur, sharpen, edge_detect,
    pixelate, posterize, sepia,
    adjustment_brightness_contrast, adjustment_hsl, adjustment_levels,
    heal_patch, noise_reduce,
)


def make_image(w=8, h=8, fmt=QImage.Format_ARGB32):
    img = QImage(w, h, fmt)
    img.fill(QColor(100, 150, 200))
    return img


def make_gradient_image(w=16, h=16):
    img = QImage(w, h, QImage.Format_ARGB32)
    for y in range(h):
        for x in range(w):
            r = int(255 * x / w)
            g = int(255 * y / h)
            b = 128
            img.setPixel(x, y, QColor(r, g, b).rgba())
    return img


class TestArrayConversion(unittest.TestCase):
    def test_to_array(self):
        img = make_image(4, 4)
        arr = to_array(img)
        self.assertEqual(arr.shape, (4, 4, 4))
        self.assertEqual(arr.dtype, np.uint8)

    def test_from_array(self):
        arr = np.full((4, 4, 4), 100, dtype=np.uint8)
        arr[:, :, 3] = 255
        img = from_array(arr)
        self.assertEqual(img.width(), 4)
        self.assertEqual(img.height(), 4)

    def test_roundtrip(self):
        original = make_image(8, 8)
        arr = to_array(original)
        reconstructed = from_array(arr)
        arr2 = to_array(reconstructed)
        np.testing.assert_array_equal(arr, arr2)


class TestFilters(unittest.TestCase):
    def setUp(self):
        self.img = make_image()

    def _arr(self):
        return to_array(self.img)

    def test_grayscale(self):
        result = grayscale(self.img)
        self.assertIsInstance(result, QImage)
        arr = to_array(result)
        self.assertEqual(arr.shape, (8, 8, 4))
        np.testing.assert_array_equal(arr[:, :, 0], arr[:, :, 1])
        np.testing.assert_array_equal(arr[:, :, 1], arr[:, :, 2])

    def test_invert(self):
        result = invert(self.img)
        arr = to_array(result)
        orig = to_array(self.img)
        np.testing.assert_array_equal(arr[:, :, :3], 255 - orig[:, :, :3])
        np.testing.assert_array_equal(arr[:, :, 3], orig[:, :, 3])

    def test_brightness(self):
        result = brightness(self.img, 50)
        arr = to_array(result)
        orig = to_array(self.img)
        expected = np.clip(orig.astype(np.int32) + 50, 0, 255).astype(np.uint8)
        np.testing.assert_array_equal(arr, expected)

    def test_brightness_negative(self):
        result = brightness(self.img, -200)
        arr = to_array(result)
        self.assertTrue(np.all(arr[:, :, :3] == 0))

    def test_contrast(self):
        result = contrast(self.img, 2.0)
        self.assertIsInstance(result, QImage)

    def test_contrast_zero(self):
        result = contrast(self.img, 0)
        arr = to_array(result)
        np.testing.assert_array_equal(arr[:, :, :3], 128)

    def test_levels(self):
        result = levels(self.img, 50, 1.0, 200)
        self.assertIsInstance(result, QImage)

    def test_levels_identical_shadow_highlight(self):
        result = levels(self.img, 100, 1.0, 100)
        self.assertIsInstance(result, QImage)

    def test_hue_saturation(self):
        result = hue_saturation(self.img, 45, 1.5, 10)
        self.assertIsInstance(result, QImage)

    def test_color_balance(self):
        result = color_balance(self.img, (20, -10, 5), (0, 0, 0), (0, 0, 0))
        self.assertIsInstance(result, QImage)

    def test_curves(self):
        points = [(0, 0), (0.5, 0.5), (1, 1)]
        result = curves(self.img, points)
        arr = to_array(result)
        orig = to_array(self.img)
        np.testing.assert_array_almost_equal(arr, orig, decimal=0)

    def test_gaussian_blur(self):
        result = gaussian_blur(self.img, 1)
        self.assertIsInstance(result, QImage)
        self.assertEqual(result.width(), self.img.width())
        self.assertEqual(result.height(), self.img.height())

    def test_gaussian_blur_large_radius(self):
        result = gaussian_blur(self.img, 5)
        self.assertIsInstance(result, QImage)

    def test_sharpen(self):
        result = sharpen(self.img, 1.0)
        self.assertIsInstance(result, QImage)

    def test_edge_detect(self):
        result = edge_detect(self.img)
        self.assertIsInstance(result, QImage)

    def test_pixelate(self):
        result = pixelate(self.img, 4)
        self.assertIsInstance(result, QImage)

    def test_pixelate_block_size_2(self):
        result = pixelate(self.img, 2)
        self.assertIsInstance(result, QImage)

    def test_posterize(self):
        result = posterize(self.img, 4)
        self.assertIsInstance(result, QImage)
        arr = to_array(result)
        self.assertTrue(np.all(arr[:, :, :3] % 64 == 0))

    def test_posterize_levels_2(self):
        result = posterize(self.img, 2)
        arr = to_array(result)
        self.assertTrue(np.all(arr[:, :, :3] % 128 == 0))

    def test_sepia(self):
        result = sepia(self.img)
        self.assertIsInstance(result, QImage)

    def test_adjustment_brightness_contrast(self):
        result = adjustment_brightness_contrast(self.img, {"brightness": 20, "contrast": 120})
        self.assertIsInstance(result, QImage)

    def test_adjustment_hsl(self):
        result = adjustment_hsl(self.img, {"hue": 30, "saturation": 150, "lightness": 10})
        self.assertIsInstance(result, QImage)

    def test_adjustment_levels(self):
        result = adjustment_levels(self.img, {"shadow": 20, "mid": 100, "highlight": 235})
        self.assertIsInstance(result, QImage)

    def test_noise_reduce(self):
        result = noise_reduce(self.img, 1)
        self.assertIsInstance(result, QImage)

    def test_heal_patch(self):
        src = np.full((4, 4, 4), 200, dtype=np.uint8)
        dst = np.full((4, 4, 4), 50, dtype=np.uint8)
        result = heal_patch(src, dst, 2)
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (4, 4, 4))

    def test_heal_patch_minimal_size(self):
        src = np.full((2, 2, 4), 200, dtype=np.uint8)
        dst = np.full((2, 2, 4), 50, dtype=np.uint8)
        result = heal_patch(src, dst, 1)
        self.assertEqual(result.shape, (2, 2, 4))


class TestFilterEdgeCases(unittest.TestCase):
    def test_single_pixel_image(self):
        img = QImage(1, 1, QImage.Format_ARGB32)
        img.fill(QColor(50, 100, 150))
        for f in [grayscale, invert, sepia]:
            result = f(img)
            self.assertEqual(result.width(), 1)
            self.assertEqual(result.height(), 1)

    def test_transparent_image(self):
        img = QImage(8, 8, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        result = grayscale(img)
        self.assertFalse(result.isNull())

    def test_white_image(self):
        img = QImage(8, 8, QImage.Format_ARGB32)
        img.fill(Qt.white)
        result = invert(img)
        arr = to_array(result)
        self.assertTrue(np.all(arr[:, :, :3] == 0))

    def test_black_image_brightness(self):
        img = QImage(8, 8, QImage.Format_ARGB32)
        img.fill(Qt.black)
        result = brightness(img, 255)
        arr = to_array(result)
        self.assertTrue(np.all(arr[:, :, :3] == 255))


if __name__ == "__main__":
    unittest.main()
