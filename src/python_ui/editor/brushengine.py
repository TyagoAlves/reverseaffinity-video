"""
Brush engine: tip types, stroke rendering with spacing/opacity/flow.
"""
import math
import json
import os

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QImage, QPixmap,
    QRadialGradient, QLinearGradient,
)


PRESET_DIR = os.path.join(os.path.dirname(__file__), "..", "presets")


class BrushTip:
    """Base class. Subclasses draw a white/grayscale mask in apply()."""

    def apply(self, painter, x, y, pressure, size):
        pass

    def make_preview(self, size):
        pix = QPixmap(int(size * 2 + 4), int(size * 2 + 4))
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        self.apply(p, size / 2 + 2, size / 2 + 2, 1.0, size)
        p.end()
        return pix


class CircleTip(BrushTip):
    def __init__(self, hardness=1.0):
        self.hardness = max(0.0, min(1.0, hardness))

    def apply(self, painter, x, y, pressure, size):
        r = size / 2.0
        alpha = min(255, int(255 * pressure))
        if self.hardness >= 1.0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, alpha)))
            painter.drawEllipse(QPointF(x, y), r, r)
        else:
            grad = QRadialGradient(x, y, r)
            inner = r * self.hardness
            grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            grad.setColorAt(inner / r if r > 0 else 1.0, QColor(255, 255, 255, alpha))
            grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(x, y), r, r)


class SquareTip(BrushTip):
    def __init__(self, hardness=1.0):
        self.hardness = max(0.0, min(1.0, hardness))

    def apply(self, painter, x, y, pressure, size):
        half = size / 2.0
        alpha = min(255, int(255 * pressure))
        if self.hardness >= 1.0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, alpha)))
            painter.drawRect(x - half, y - half, size, size)
        else:
            inner = half * self.hardness
            grad = QLinearGradient(x - half, y - half, x + half, y + half)
            grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            grad.setColorAt(inner / half if half > 0 else 1.0, QColor(255, 255, 255, alpha))
            grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRect(x - half, y - half, size, size)


class TextureTip(BrushTip):
    def __init__(self, texture_image):
        self.texture = texture_image

    def apply(self, painter, x, y, pressure, size):
        if self.texture.isNull():
            return
        scaled = self.texture.scaled(int(size), int(size),
                                     Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        ox = int(x - size / 2.0)
        oy = int(y - size / 2.0)
        painter.setOpacity(pressure)
        painter.drawImage(ox, oy, scaled)


def _interpolate_points(points, spacing):
    if len(points) < 2:
        return points[:]
    result = [points[0]]
    for i in range(1, len(points)):
        p1 = points[i - 1]
        p2 = points[i]
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            continue
        step = max(spacing, 0.01)
        steps = int(dist / step)
        for s in range(1, steps + 1):
            t = s / steps
            result.append(QPointF(p1.x() + dx * t, p1.y() + dy * t))
    return result


def render_stroke(painter, points, tip, size, color, opacity=1.0, flow=1.0, spacing=0.25):
    if not points or not tip:
        return
    interp = _interpolate_points(points, spacing * size)
    painter.save()
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    for pt in interp:
        flow_alpha = min(1.0, flow)
        dab_alpha = opacity * flow_alpha
        # Build dab mask onto a temp image, then composite in color
        dab_size = max(1, int(size) + 2)
        dab_img = QImage(dab_size, dab_size, QImage.Format_ARGB32_Premultiplied)
        dab_img.fill(Qt.transparent)
        dp = QPainter(dab_img)
        dp.setRenderHint(QPainter.Antialiasing)
        tip.apply(dp, dab_size / 2.0, dab_size / 2.0, 1.0, size)
        dp.end()
        # Colorize the mask
        cp = QPainter(dab_img)
        cp.setCompositionMode(QPainter.CompositionMode_SourceIn)
        c = QColor(color)
        c.setAlpha(int(255 * dab_alpha))
        cp.fillRect(dab_img.rect(), c)
        cp.end()
        ox = int(pt.x() - dab_size / 2.0)
        oy = int(pt.y() - dab_size / 2.0)
        painter.drawImage(ox, oy, dab_img)
    painter.restore()


class BrushEngine:
    def __init__(self):
        self.tip = CircleTip(hardness=1.0)
        self.size = 10
        self.opacity = 1.0
        self.flow = 1.0
        self.spacing = 0.25

    def set_tip(self, tip):
        self.tip = tip

    def set_circle_tip(self, hardness=1.0):
        self.tip = CircleTip(hardness)

    def set_square_tip(self, hardness=1.0):
        self.tip = SquareTip(hardness)

    def set_texture_tip(self, image):
        self.tip = TextureTip(image)

    def render(self, painter, points, color):
        render_stroke(painter, points, self.tip, self.size,
                      color, self.opacity, self.flow, self.spacing)

    def make_preview(self, preview_size=60):
        pix = QPixmap(preview_size, preview_size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        render_stroke(p, [QPointF(preview_size / 2, preview_size / 2)],
                      self.tip, min(preview_size * 0.8, self.size),
                      QColor(0, 0, 0), 1.0, 1.0, 0.25)
        p.end()
        return pix


def load_preset(name):
    path = os.path.join(PRESET_DIR, name + ".json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_preset(name, data):
    os.makedirs(PRESET_DIR, exist_ok=True)
    path = os.path.join(PRESET_DIR, name + ".json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def list_presets():
    os.makedirs(PRESET_DIR, exist_ok=True)
    presets = []
    for fn in os.listdir(PRESET_DIR):
        if fn.endswith(".json"):
            presets.append(fn[:-5])
    return sorted(presets)
