import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication


_app = None

def pytest_configure():
    global _app
    if QApplication.instance() is None:
        _app = QApplication(sys.argv)
