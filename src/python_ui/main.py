#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from reverseaffinity.i18n import _
from reverseaffinity.shared.resources import apply_dark_theme

def main():
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)
    app.setApplicationName("reverseaffinity")
    app.setOrganizationName("reverseaffinity")
    icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    app.setApplicationDisplayName("reverseaffinity Video")
    apply_dark_theme(app)
    from reverseaffinity.video.video_app import VideoMainWindow
    win = VideoMainWindow()
    win.setWindowTitle(_("reverseaffinity Video - [Untitled]"))
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
