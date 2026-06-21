from PyQt5.QtCore import Qt, QPoint, QPointF, QRect, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF, QFont, QIcon, QLinearGradient
import math


def _make_painter(size=24):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(1, 1)
    return pix, p


def _end_painter(p):
    p.end()


def _draw_stroked_path(p, path, color=QColor(200, 200, 200), width=1.5):
    p.setPen(QPen(color, width))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)


def _draw_filled_path(p, path, color=QColor(200, 200, 200)):
    p.setPen(QPen(color, 1.2))
    p.setBrush(QBrush(color))
    p.drawPath(path)


def icon_move():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    cx, cy = 12, 12
    s = 5
    # Up
    p.drawLine(cx, cy - s - 3, cx, cy - 3)
    p.drawLine(cx - 2, cy - s - 1, cx, cy - s - 3)
    p.drawLine(cx + 2, cy - s - 1, cx, cy - s - 3)
    # Down
    p.drawLine(cx, cy + s + 3, cx, cy + 3)
    p.drawLine(cx - 2, cy + s + 1, cx, cy + s + 3)
    p.drawLine(cx + 2, cy + s + 1, cx, cy + s + 3)
    # Left
    p.drawLine(cx - s - 3, cy, cx - 3, cy)
    p.drawLine(cx - s - 1, cy - 2, cx - s - 3, cy)
    p.drawLine(cx - s - 1, cy + 2, cx - s - 3, cy)
    # Right
    p.drawLine(cx + s + 3, cy, cx + 3, cy)
    p.drawLine(cx + s + 1, cy - 2, cx + s + 3, cy)
    p.drawLine(cx + s + 1, cy + 2, cx + s + 3, cy)
    _end_painter(p)
    return QIcon(pix)


def icon_rect_marquee():
    pix, p = _make_painter()
    p.setPen(QPen(QColor(200, 200, 200), 1.5))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.addRect(3, 3, 18, 18)
    p.drawPath(path)
    # corner marks
    for x, y in [(3, 3), (21, 3), (3, 21), (21, 21)]:
        p.drawRect(x - 1, y - 1, 3, 3)
    _end_painter(p)
    return QIcon(pix)


def icon_ellipse_marquee():
    pix, p = _make_painter()
    p.setPen(QPen(QColor(200, 200, 200), 1.5))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.addEllipse(3, 4, 18, 16)
    p.drawPath(path)
    _end_painter(p)
    return QIcon(pix)


def icon_lasso():
    pix, p = _make_painter()
    p.setPen(QPen(QColor(200, 200, 200), 1.5))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(20, 4)
    path.cubicTo(16, 2, 6, 4, 4, 10)
    path.cubicTo(2, 16, 6, 20, 10, 18)
    path.cubicTo(12, 17, 12, 20, 10, 22)
    p.drawPath(path)
    _end_painter(p)
    return QIcon(pix)


def icon_magic_wand():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # star shape
    cx, cy = 12, 10
    sz = 7
    pts = []
    for i in range(5):
        angle = -math.pi / 2 + i * 2 * math.pi / 5
        pts.append(QPointF(cx + sz * math.cos(angle), cy + sz * math.sin(angle)))
        angle += math.pi / 5
        pts.append(QPointF(cx + sz * 0.4 * math.cos(angle), cy + sz * 0.4 * math.sin(angle)))
    poly = QPolygonF(pts)
    p.drawPolygon(poly)
    # sparkles
    for x, y in [(18, 2), (22, 4), (20, 8)]:
        p.drawLine(x, y - 2, x, y + 2)
        p.drawLine(x - 2, y, x + 2, y)
    _end_painter(p)
    return QIcon(pix)


def icon_crop():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # crop corners
    p.drawLine(3, 3, 3, 18)
    p.drawLine(3, 3, 18, 3)
    p.drawLine(21, 6, 21, 21)
    p.drawLine(6, 21, 21, 21)
    # cross diagonal
    p.setPen(QPen(c, 1.0))
    p.drawLine(3, 21, 21, 3)
    _end_painter(p)
    return QIcon(pix)


def icon_healing():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    # bandage cross
    p.drawLine(6, 12, 18, 12)
    p.drawLine(12, 6, 12, 18)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(c))
    p.drawEllipse(QPoint(12, 12), 10, 10)
    _end_painter(p)
    return QIcon(pix)


def icon_brush():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # brush handle
    p.drawLine(5, 20, 10, 12)
    # brush tip
    path = QPainterPath()
    path.moveTo(10, 12)
    path.lineTo(18, 3)
    path.lineTo(20, 5)
    path.lineTo(12, 14)
    path.closeSubpath()
    p.drawPath(path)
    # bristle lines
    p.setPen(QPen(c, 0.8))
    p.drawLine(18, 3, 19, 1)
    p.drawLine(19, 4, 21, 3)
    _end_painter(p)
    return QIcon(pix)


def icon_pencil():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # pencil body
    path = QPainterPath()
    path.moveTo(4, 20)
    path.lineTo(14, 8)
    path.lineTo(16, 10)
    path.lineTo(6, 22)
    path.closeSubpath()
    p.drawPath(path)
    # tip
    p.drawLine(14, 8, 18, 3)
    p.drawLine(18, 3, 20, 5)
    p.drawLine(20, 5, 16, 10)
    _end_painter(p)
    return QIcon(pix)


def icon_clone_stamp():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # stamp body
    p.drawRect(5, 8, 14, 12)
    # stamp handle
    p.drawRect(9, 2, 6, 6)
    # stamp bottom
    p.drawLine(5, 8, 19, 8)
    _end_painter(p)
    return QIcon(pix)


def icon_eraser():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # eraser block
    path = QPainterPath()
    path.moveTo(4, 6)
    path.lineTo(18, 6)
    path.lineTo(20, 14)
    path.lineTo(6, 14)
    path.closeSubpath()
    p.drawPath(path)
    # eraser top
    p.drawLine(4, 10, 20, 10)
    _end_painter(p)
    return QIcon(pix)


def icon_gradient():
    pix, p = _make_painter()
    rect = QRect(3, 4, 18, 16)
    grad = QLinearGradient(3, 10, 21, 10)
    grad.setColorAt(0.0, Qt.white)
    grad.setColorAt(0.5, QColor(128, 128, 128))
    grad.setColorAt(1.0, Qt.black)
    p.setPen(QPen(QColor(200, 200, 200), 1.2))
    p.setBrush(QBrush(grad))
    p.drawRect(rect)
    _end_painter(p)
    return QIcon(pix)


def icon_pen():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # pen nib
    path = QPainterPath()
    path.moveTo(12, 2)
    path.lineTo(4, 20)
    path.lineTo(8, 22)
    path.lineTo(14, 18)
    path.closeSubpath()
    p.drawPath(path)
    # nib tip circle
    p.setBrush(QBrush(c))
    p.drawEllipse(QPoint(12, 2), 2, 2)
    _end_painter(p)
    return QIcon(pix)


def icon_type():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.8))
    # letter T
    p.drawLine(4, 4, 20, 4)
    p.drawLine(12, 4, 12, 20)
    p.drawLine(8, 20, 16, 20)
    _end_painter(p)
    return QIcon(pix)


def icon_shape():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # rectangle with rounded corners
    path = QPainterPath()
    path.addRoundedRect(3, 5, 18, 14, 3, 3)
    p.drawPath(path)
    # small circle inside
    p.drawEllipse(QPoint(12, 12), 3, 3)
    _end_painter(p)
    return QIcon(pix)


def icon_hand():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # palm
    path = QPainterPath()
    path.moveTo(8, 14)
    path.lineTo(8, 6)
    path.lineTo(6, 6)
    path.lineTo(6, 16)
    path.lineTo(4, 16)
    path.lineTo(4, 8)
    path.lineTo(2, 8)
    path.lineTo(2, 16)
    path.lineTo(8, 22)
    path.lineTo(18, 22)
    path.lineTo(22, 18)
    path.lineTo(22, 14)
    path.lineTo(20, 14)
    path.lineTo(16, 14)
    path.lineTo(16, 4)
    path.lineTo(14, 4)
    path.lineTo(14, 14)
    path.lineTo(12, 14)
    path.lineTo(12, 2)
    path.lineTo(10, 2)
    path.lineTo(10, 14)
    path.closeSubpath()
    p.drawPath(path)
    _end_painter(p)
    return QIcon(pix)


def icon_zoom():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # magnifier glass
    p.drawEllipse(3, 3, 12, 12)
    # handle
    p.drawLine(13, 13, 21, 21)
    # plus inside
    cx, cy = 9, 9
    p.drawLine(cx - 3, cy, cx + 3, cy)
    p.drawLine(cx, cy - 3, cx, cy + 3)
    _end_painter(p)
    return QIcon(pix)


def icon_eyedropper():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # dropper body
    p.drawLine(3, 21, 10, 8)
    p.drawLine(12, 8, 20, 5)
    p.drawLine(20, 5, 19, 3)
    p.drawLine(19, 3, 17, 4)
    p.drawLine(17, 4, 10, 12)
    # tip
    p.drawLine(10, 8, 12, 8)
    # droplet
    path = QPainterPath()
    path.addEllipse(QPoint(3, 21), 2, 2)
    p.setBrush(QBrush(c))
    p.drawPath(path)
    _end_painter(p)
    return QIcon(pix)


def icon_paint_bucket():
    pix, p = _make_painter()
    c = QColor(200, 200, 200)
    p.setPen(QPen(c, 1.5))
    p.setBrush(Qt.NoBrush)
    # bucket body
    path = QPainterPath()
    path.moveTo(5, 6)
    path.lineTo(4, 18)
    path.lineTo(20, 18)
    path.lineTo(19, 6)
    path.closeSubpath()
    p.drawPath(path)
    # bucket rim
    p.drawLine(3, 6, 21, 6)
    # paint drip
    p.drawLine(12, 18, 12, 22)
    p.drawEllipse(QPoint(12, 22), 2, 2)
    _end_painter(p)
    return QIcon(pix)


TOOL_ICONS = {
    "Move Tool": icon_move,
    "Rectangular Marquee Tool": icon_rect_marquee,
    "Elliptical Marquee Tool": icon_ellipse_marquee,
    "Lasso Tool": icon_lasso,
    "Magic Wand Tool": icon_magic_wand,
    "Crop Tool": icon_crop,
    "Spot Healing Brush Tool": icon_healing,
    "Brush Tool": icon_brush,
    "Pencil Tool": icon_pencil,
    "Clone Stamp Tool": icon_clone_stamp,
    "Eraser Tool": icon_eraser,
    "Gradient Tool": icon_gradient,
    "Pen Tool": icon_pen,
    "Horizontal Type Tool": icon_type,
    "Rectangle Tool": icon_shape,
    "Hand Tool": icon_hand,
    "Zoom Tool": icon_zoom,
    "Eyedropper Tool": icon_eyedropper,
    "Paint Bucket Tool": icon_paint_bucket,
}


def get_tool_icon(tool_name):
    fn = TOOL_ICONS.get(tool_name)
    if fn:
        return fn()
    return QIcon()
