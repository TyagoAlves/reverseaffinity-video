#!/usr/bin/env python3
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_layers import TestBlendFunctions, TestLayer, TestAdjustmentLayer, \
    TestGroupLayer, TestLayerStack, TestFloatArrayConversion
from tests.test_filters import TestArrayConversion, TestFilters, TestFilterEdgeCases
from tests.test_tools import TestToolRegistration, TestToolShortcutsInCanvas
from tests.test_history import TestHistoryEntry, TestHistoryManager
from tests.test_canvas import TestCanvasComposite, TestCanvasSelection, \
    TestCanvasFileIO, TestCanvasZoomPan, TestCanvasDrawing, TestCanvasMoveLayer


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestBlendFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestLayer))
    suite.addTests(loader.loadTestsFromTestCase(TestAdjustmentLayer))
    suite.addTests(loader.loadTestsFromTestCase(TestGroupLayer))
    suite.addTests(loader.loadTestsFromTestCase(TestLayerStack))
    suite.addTests(loader.loadTestsFromTestCase(TestFloatArrayConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestArrayConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestFilters))
    suite.addTests(loader.loadTestsFromTestCase(TestFilterEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestToolRegistration))
    suite.addTests(loader.loadTestsFromTestCase(TestToolShortcutsInCanvas))
    suite.addTests(loader.loadTestsFromTestCase(TestHistoryEntry))
    suite.addTests(loader.loadTestsFromTestCase(TestHistoryManager))
    suite.addTests(loader.loadTestsFromTestCase(TestCanvasComposite))
    suite.addTests(loader.loadTestsFromTestCase(TestCanvasSelection))
    suite.addTests(loader.loadTestsFromTestCase(TestCanvasFileIO))
    suite.addTests(loader.loadTestsFromTestCase(TestCanvasZoomPan))
    suite.addTests(loader.loadTestsFromTestCase(TestCanvasDrawing))
    suite.addTests(loader.loadTestsFromTestCase(TestCanvasMoveLayer))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
