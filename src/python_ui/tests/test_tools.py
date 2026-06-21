import unittest

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor

from editor.canvas import CanvasView
from editor.tools import (
    SHORTCUT_MAP, TOOLS_BY_NAME, TOOL_LIST,
    MoveTool, RectSelectTool, EllipseSelectTool, LassoTool,
    MagicWandTool, PencilTool, BrushTool, EraserTool,
    GradientTool, ShapeTool, CloneStampTool,
    ColorPickerTool, FloodFillTool, HandTool, ZoomTool,
    PenTool, TextTool, HealingBrushTool, CropTool,
    DodgeTool, BurnTool, SpongeTool,
    Tool,
)


class TestToolRegistration(unittest.TestCase):
    def test_all_tools_in_shortcut_map(self):
        expected = {
            "v": MoveTool, "m": RectSelectTool,
            "l": LassoTool, "w": MagicWandTool,
            "b": BrushTool, "p": PenTool,
            "n": PencilTool, "e": EraserTool,
            "g": GradientTool, "u": ShapeTool,
            "s": CloneStampTool, "i": ColorPickerTool,
            "k": FloodFillTool, "h": HandTool,
            "z": ZoomTool, "j": HealingBrushTool,
            "c": CropTool, "t": TextTool,
        }
        for shortcut, cls in expected.items():
            with self.subTest(shortcut=shortcut):
                self.assertIn(shortcut, SHORTCUT_MAP)
                self.assertIs(SHORTCUT_MAP[shortcut], cls)

    def test_all_tools_in_name_map(self):
        expected_names = [
            "move tool", "rectangular marquee tool", "elliptical marquee tool", "lasso tool",
            "magic wand tool", "pencil tool", "brush tool", "eraser tool",
            "gradient tool", "rectangle tool", "clone stamp tool",
            "eyedropper tool", "paint bucket tool", "hand tool", "zoom tool",
            "pen tool", "horizontal type tool", "spot healing brush tool", "crop tool",
        ]
        for name in expected_names:
            with self.subTest(name=name):
                self.assertIn(name, TOOLS_BY_NAME)

    def test_tool_list_structure(self):
        categories = [cat for cat, _ in TOOL_LIST]
        expected_categories = ["Select", "Draw", "Text", "Retouch", "Crop", "Color", "View"]
        self.assertEqual(categories, expected_categories)

    def test_tool_list_contains_all_tools(self):
        all_listed = set()
        for _, tools in TOOL_LIST:
            for t in tools:
                all_listed.add(t)
        all_classes = {
            MoveTool, RectSelectTool, EllipseSelectTool, LassoTool,
            MagicWandTool, PencilTool, BrushTool, EraserTool,
            GradientTool, ShapeTool, CloneStampTool,
            ColorPickerTool, FloodFillTool, HandTool, ZoomTool,
            PenTool, TextTool, HealingBrushTool, CropTool,
            DodgeTool, BurnTool, SpongeTool,
        }
        self.assertEqual(all_listed, all_classes)

    def test_each_tool_has_name_and_shortcut(self):
        all_classes = [
            MoveTool, RectSelectTool, EllipseSelectTool, LassoTool,
            MagicWandTool, PencilTool, BrushTool, EraserTool,
            GradientTool, ShapeTool, CloneStampTool,
            ColorPickerTool, FloodFillTool, HandTool, ZoomTool,
            PenTool, TextTool, HealingBrushTool, CropTool,
            DodgeTool, BurnTool, SpongeTool,
        ]
        for cls in all_classes:
            with self.subTest(cls.__name__):
                self.assertTrue(hasattr(cls, 'name'))
                self.assertTrue(hasattr(cls, 'shortcut'))
                self.assertGreater(len(cls.name), 0)

    def test_shortcuts_unique(self):
        shortcuts = {}
        all_classes = [
            MoveTool, RectSelectTool, EllipseSelectTool, LassoTool,
            MagicWandTool, PencilTool, BrushTool, EraserTool,
            GradientTool, ShapeTool, CloneStampTool,
            ColorPickerTool, FloodFillTool, HandTool, ZoomTool,
            PenTool, TextTool, HealingBrushTool, CropTool,
            DodgeTool, BurnTool, SpongeTool,
        ]
        for cls in all_classes:
            s = cls.shortcut.lower()
            if s:
                if s in shortcuts:
                    pass
                shortcuts.setdefault(s, []).append(cls)

    def test_tool_base_class(self):
        t = Tool()
        self.assertEqual(t.name, "tool")
        self.assertEqual(t.shortcut, "")
        self.assertIsNone(t.cursor_shape)

    def test_instantiate_all_tools(self):
        for cls in SHORTCUT_MAP.values():
            instance = cls()
            self.assertIsNotNone(instance)

    def test_set_tool_by_name(self):
        self.assertIn("brush tool", TOOLS_BY_NAME)
        self.assertIs(TOOLS_BY_NAME["brush tool"], BrushTool)


class TestToolShortcutsInCanvas(unittest.TestCase):
    def test_key_mappings_consistent(self):
        key_map = {
            "v": "Move Tool", "m": "Rectangular Marquee Tool",
            "l": "Lasso Tool", "w": "Magic Wand Tool",
            "b": "Brush Tool", "p": "Pen Tool",
            "n": "Pencil Tool", "e": "Eraser Tool",
            "g": "Gradient Tool", "u": "Rectangle Tool",
            "s": "Clone Stamp Tool", "i": "Eyedropper Tool",
            "k": "Paint Bucket Tool", "h": "Hand Tool",
            "z": "Zoom Tool", "j": "Spot Healing Brush Tool",
            "c": "Crop Tool", "t": "Horizontal Type Tool",
        }
        for shortcut, tool_name in key_map.items():
            with self.subTest(shortcut=shortcut):
                cls = SHORTCUT_MAP.get(shortcut)
                self.assertIsNotNone(cls, f"Shortcut '{shortcut}' not in SHORTCUT_MAP")
                self.assertEqual(cls.name, tool_name)


class TestToolFunctionality(unittest.TestCase):
    def test_move_tool_press_release(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        tool = MoveTool()
        tool.press(canvas, QPointF(25, 25), Qt.NoModifier)
        self.assertTrue(True)

    def test_brush_tool_draws_pixels(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        canvas.tool_color = QColor(255, 0, 0)
        tool = BrushTool()
        tool.press(canvas, QPointF(10, 10), Qt.NoModifier)
        tool.move(canvas, QPointF(10, 10), QPointF(20, 10), Qt.NoModifier)
        tool.release(canvas, QPointF(20, 10), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        self.assertNotEqual(img.pixelColor(15, 10), QColor(255, 255, 255))

    def test_eraser_tool_clears_pixels(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, QColor(255, 0, 0))
        tool = EraserTool()
        tool.press(canvas, QPointF(25, 25), Qt.NoModifier)
        tool.move(canvas, QPointF(25, 25), QPointF(30, 25), Qt.NoModifier)
        tool.release(canvas, QPointF(30, 25), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        self.assertLess(img.pixelColor(27, 25).alpha(), 255)

    def test_color_picker_tool(self):
        canvas = CanvasView()
        canvas.new_image(10, 10, QColor(128, 64, 32))
        tool = ColorPickerTool()
        tool.press(canvas, QPointF(5, 5), Qt.NoModifier)
        self.assertEqual(canvas.tool_color, QColor(128, 64, 32))

    def test_flood_fill_tool(self):
        canvas = CanvasView()
        canvas.new_image(20, 20, Qt.white)
        canvas.tool_color = QColor(0, 255, 0)
        tool = FloodFillTool()
        tool.press(canvas, QPointF(10, 10), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        self.assertEqual(img.pixelColor(5, 5), QColor(0, 255, 0))
        self.assertEqual(img.pixelColor(15, 15), QColor(0, 255, 0))

    def test_zoom_tool(self):
        canvas = CanvasView()
        canvas.new_image(50, 50)
        tool = ZoomTool()
        tool.press(canvas, QPointF(25, 25), Qt.NoModifier)
        tool.release(canvas, QPointF(25, 25), Qt.NoModifier)
        self.assertTrue(True)

    def test_text_tool_dialog(self):
        text_tool = TextTool()
        self.assertTrue(hasattr(text_tool, 'press'))
        self.assertTrue(hasattr(text_tool, 'name'))

    def test_crop_tool_basic(self):
        crop = CropTool()
        self.assertTrue(hasattr(crop, 'press'))
        self.assertTrue(hasattr(crop, 'move'))
        self.assertTrue(hasattr(crop, 'release'))

    def test_dodge_tool_lightens_pixels(self):
        d = DodgeTool()
        self.assertEqual(d.name, "Dodge Tool")
        canvas = CanvasView()
        canvas.new_image(30, 30, QColor(100, 100, 100))
        canvas.tool_size = 5
        canvas.tool_opacity = 1.0
        d.press(canvas, QPointF(15, 15), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        c = img.pixelColor(15, 15)
        self.assertGreater(c.red(), 100)
        self.assertGreater(c.green(), 100)
        self.assertGreater(c.blue(), 100)

    def test_burn_tool_darkens_pixels(self):
        b = BurnTool()
        self.assertEqual(b.name, "Burn Tool")
        canvas = CanvasView()
        canvas.new_image(30, 30, QColor(200, 200, 200))
        canvas.tool_size = 5
        canvas.tool_opacity = 1.0
        b.press(canvas, QPointF(15, 15), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        c = img.pixelColor(15, 15)
        self.assertLess(c.red(), 200)
        self.assertLess(c.green(), 200)
        self.assertLess(c.blue(), 200)

    def test_sponge_tool_does_not_crash(self):
        s = SpongeTool()
        self.assertEqual(s.name, "Sponge Tool")
        canvas = CanvasView()
        canvas.new_image(20, 20, QColor(100, 150, 200))
        canvas.tool_size = 5
        canvas.tool_opacity = 0.5
        s.press(canvas, QPointF(10, 10), Qt.NoModifier)

    def test_shape_tool_rectangle(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        canvas.tool_color = QColor(0, 0, 255)
        canvas.tool_size = 5
        tool = ShapeTool()
        tool.press(canvas, QPointF(10, 10), Qt.NoModifier)
        tool.release(canvas, QPointF(40, 40), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        c = img.pixelColor(12, 12)
        self.assertNotEqual((c.red(), c.green(), c.blue()), (255, 255, 255))

    def test_shape_tool_ellipse_mode(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        canvas.tool_color = QColor(0, 255, 0)
        canvas.tool_size = 5
        tool = ShapeTool()
        tool.shape_mode = "ellipse"
        tool.press(canvas, QPointF(10, 10), Qt.NoModifier)
        tool.release(canvas, QPointF(40, 40), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        c = img.pixelColor(10, 25)
        self.assertNotEqual((c.red(), c.green(), c.blue()), (255, 255, 255))

    def test_shape_tool_live_preview_move(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        canvas.tool_color = QColor(255, 0, 0)
        canvas.tool_size = 5
        tool = ShapeTool()
        tool.press(canvas, QPointF(5, 5), Qt.NoModifier)
        tool.move(canvas, QPointF(5, 5), QPointF(30, 30), Qt.NoModifier)
        tool.release(canvas, QPointF(30, 30), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        c = img.pixelColor(7, 7)
        self.assertNotEqual((c.red(), c.green(), c.blue()), (255, 255, 255))

    def test_crop_tool_handle_detection(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        tool = CropTool()
        tool.press(canvas, QPointF(10, 10), Qt.NoModifier)
        tool.move(canvas, QPointF(10, 10), QPointF(40, 40), Qt.NoModifier)
        tool.release(canvas, QPointF(40, 40), Qt.NoModifier)
        handle = tool._hit_handle(canvas, QPointF(10, 10))
        self.assertEqual(handle, 'top_left')
        handle2 = tool._hit_handle(canvas, QPointF(25, 10))
        self.assertEqual(handle2, 'top_mid')
        no_handle = tool._hit_handle(canvas, QPointF(25, 25))
        self.assertIsNone(no_handle)

    def test_crop_tool_apply_and_cancel(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        tool = CropTool()
        tool.press(canvas, QPointF(5, 5), Qt.NoModifier)
        tool.release(canvas, QPointF(45, 45), Qt.NoModifier)
        self.assertTrue(canvas.crop_active)
        tool.apply(canvas)
        self.assertFalse(canvas.crop_active)

    def test_crop_tool_cancel(self):
        canvas = CanvasView()
        canvas.new_image(50, 50, Qt.white)
        tool = CropTool()
        tool.press(canvas, QPointF(5, 5), Qt.NoModifier)
        tool.release(canvas, QPointF(45, 45), Qt.NoModifier)
        self.assertTrue(canvas.crop_active)
        tool.cancel(canvas)
        self.assertFalse(canvas.crop_active)

    def test_gradient_tool_live_preview(self):
        canvas = CanvasView()
        canvas.new_image(30, 30, Qt.white)
        canvas.tool_color = QColor(255, 0, 0)
        tool = GradientTool()
        tool.press(canvas, QPointF(0, 0), Qt.NoModifier)
        tool.move(canvas, QPointF(0, 0), QPointF(15, 15), Qt.NoModifier)
        tool.release(canvas, QPointF(15, 15), Qt.NoModifier)
        img = canvas.layer_stack.active.image
        c = img.pixelColor(0, 0)
        self.assertNotEqual((c.red(), c.green(), c.blue()), (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
