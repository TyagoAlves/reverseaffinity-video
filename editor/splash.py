import os
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QPen
from PyQt5.QtWidgets import QSplashScreen

from .i18n import _


class SplashScreen(QSplashScreen):
    def __init__(self, app_version="0.1.0"):
        self.app_version = app_version
        pixmap = self._render_pixmap()
        super().__init__(pixmap)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

    def _render_pixmap(self):
        size = 480, 280
        pix = QPixmap(*size)
        pix.fill(QColor(0, 0, 0))

        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)

        p.setPen(QPen(QColor(34, 34, 34), 1))
        p.setBrush(QColor(0, 0, 0))
        p.drawRoundedRect(0, 0, size[0] - 1, size[1] - 1, 12, 12)

        p.setPen(QColor(58, 138, 196))
        p.drawLine(20, size[1] - 50, size[0] - 20, size[1] - 50)

        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.svg")
        if os.path.exists(icon_path):
            icon_pix = QIcon(icon_path).pixmap(64, 64)
            p.drawPixmap((size[0] - 64) // 2, 30, 64, 64, icon_pix)

        p.setPen(QColor(224, 224, 224))
        title_font = QFont("Segoe UI", 22, QFont.Bold)
        p.setFont(title_font)
        p.drawText(QRect(0, 100, size[0], 40), Qt.AlignCenter, _("reverseaffinity"))

        p.setPen(QColor(150, 150, 150))
        ver_font = QFont("Segoe UI", 11)
        p.setFont(ver_font)
        p.drawText(QRect(0, 140, size[0], 24), Qt.AlignCenter, _("Version ") + f"{self.app_version}")

        p.setPen(QColor(106, 170, 74))
        subtitle_font = QFont("Segoe UI", 10)
        p.setFont(subtitle_font)
        p.drawText(QRect(0, 170, size[0], 20), Qt.AlignCenter, _("Photo Editor"))

        self._message = _("Loading...")
        p.setPen(QColor(180, 180, 180))
        msg_font = QFont("Segoe UI", 9)
        p.setFont(msg_font)
        p.drawText(QRect(20, size[1] - 42, size[0] - 40, 20), Qt.AlignLeft, self._message)

        p.end()
        return pix

    def show_loading(self, message):
        self._message = message
        pix = self._render_pixmap()
        self.setPixmap(pix)
        self.show()
        self.repaint()


def show_splash_then_main(app, main_window, duration_ms=2000):
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    timer = QTimer()
    timer.setSingleShot(True)

    def finish():
        main_window.show()
        splash.finish(main_window)

    timer.timeout.connect(finish)
    timer.start(duration_ms)

    return splash
