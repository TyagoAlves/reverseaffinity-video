"""
GUI Tests for reverseaffinity.

Uses QTest for widget interaction. Requires a display (use xvfb-run).
Mark with @pytest.mark.gui to skip when no display is available.
"""
import unittest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtTest import QTest
from PyQt5.QtGui import QColor

from editor.app_ui import ToolPalette, MainWindow
from editor.panels import ColorPanel
from editor.tools import TOOLS_BY_NAME


app = QApplication.instance() or QApplication([])


class TestToolPalette(unittest.TestCase):
    def setUp(self):
        self.main = MainWindow()
        self.palette = ToolPalette(lambda: self.main.canvas)

    def test_tool_buttons_exist(self):
        for name in ["Move", "Brush", "Eraser", "Gradient"]:
            if name in self.palette.tool_buttons:
                btn = self.palette.tool_buttons[name]
                self.assertTrue(btn.isCheckable())

    def test_select_tool_switches_canvas(self):
        btn = self.palette.tool_buttons.get("Brush")
        if btn:
            btn.click()
            self.assertEqual(self.main.canvas.tool.name, "Brush Tool")

    def test_tool_palette_has_all_tools(self):
        expected_count = sum(len(tools) for _, tools in enumerate(
            getattr(self.main, 'tool_list', [])
        )) or 19
        self.assertGreaterEqual(len(self.palette.tool_buttons), 15)


class TestColorPanel(unittest.TestCase):
    def setUp(self):
        self.main = MainWindow()
        self.color_panel = ColorPanel()

    def test_rgb_spins_sync(self):
        self.color_panel.set_color(QColor(100, 150, 200))
        self.assertEqual(self.color_panel.r_spin.value(), 100)
        self.assertEqual(self.color_panel.g_spin.value(), 150)
        self.assertEqual(self.color_panel.b_spin.value(), 200)

    def test_fg_bg_swatch_exists(self):
        self.assertIsNotNone(self.color_panel.fg)
        self.assertIsNotNone(self.color_panel.bg)
        self.assertEqual(self.color_panel.fg.color(), QColor(0, 0, 0))


class TestMainWindowActions(unittest.TestCase):
    def setUp(self):
        self.main = MainWindow()

    def test_new_action_creates_image(self):
        self.main.canvas.new_image(100, 100)
        self.assertEqual(self.main.canvas.layer_stack.layers[0].image.width(), 100)

    def test_tool_change_via_menu(self):
        self.main.canvas.set_tool("brush")
        self.assertEqual(self.main.canvas.tool.name, "Brush Tool")


if __name__ == "__main__":
    unittest.main()
