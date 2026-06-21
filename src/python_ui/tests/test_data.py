import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor, QPainter

from editor.layers import Layer, LayerStack


def checkerboard(w, h, size=32, color1=QColor(255, 255, 255), color2=QColor(128, 128, 128)):
    img = QImage(w, h, QImage.Format_ARGB32)
    p = QPainter(img)
    for y in range(0, h, size):
        for x in range(0, w, size):
            c = color1 if ((x // size) + (y // size)) % 2 == 0 else color2
            p.fillRect(x, y, size, size, c)
    p.end()
    return img


def gradient_image(w, h):
    img = QImage(w, h, QImage.Format_ARGB32)
    for y in range(h):
        for x in range(w):
            r = int(255 * x / max(w - 1, 1))
            g = int(255 * y / max(h - 1, 1))
            img.setPixel(x, y, QColor(r, g, 128).rgba())
    return img


def solid_image(w, h, color=QColor(128, 64, 32)):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(color)
    return img


def random_image(w, h, seed=None):
    if seed is not None:
        np.random.seed(seed)
    arr = np.random.randint(0, 256, (h, w, 4), dtype=np.uint8)
    arr[:, :, 3] = 255
    img = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
    return img.copy()


def layered_image(w=200, h=200):
    stack = LayerStack(w, h)
    stack.layers[0].image.fill(QColor(100, 150, 200))
    stack.add_layer("Red Stripe")
    p = QPainter(stack.layers[1].image)
    p.fillRect(0, 0, w // 2, h, QColor(255, 0, 0, 128))
    p.end()
    stack.layers[1].opacity = 0.8
    stack.layers[1].blend_mode = "Multiply"
    stack.add_layer("Green Dot")
    p = QPainter(stack.layers[2].image)
    p.setBrush(QColor(0, 255, 0))
    p.drawEllipse(w // 4, h // 4, w // 2, h // 2)
    p.end()
    stack.add_layer("Blue Border")
    p = QPainter(stack.layers[3].image)
    p.setPen(QPen(QColor(0, 0, 255), 4))
    p.drawRect(4, 4, w - 8, h - 8)
    p.end()
    return stack
