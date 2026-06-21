from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPainterPath, QColor
import math


class AnchorPoint:
    __slots__ = ('position', 'handle_in', 'handle_out', 'type')

    def __init__(self, position, handle_in=None, handle_out=None, type="corner"):
        self.position = QPointF(position)
        ih = handle_in if handle_in is not None else position
        oh = handle_out if handle_out is not None else position
        self.handle_in = QPointF(ih)
        self.handle_out = QPointF(oh)
        self.type = type

    def copy(self):
        return AnchorPoint(
            QPointF(self.position),
            QPointF(self.handle_in),
            QPointF(self.handle_out),
            self.type
        )

    def __repr__(self):
        return f"Anchor({self.position.x():.1f},{self.position.y():.1f},{self.type})"


SNAP_ANGLES = list(range(0, 360, 15))


def snap_angle_15(offset):
    length = math.sqrt(offset.x()**2 + offset.y()**2)
    if length < 0.5:
        return QPointF(offset)
    angle = math.degrees(math.atan2(offset.y(), offset.x())) % 360
    snapped = min(SNAP_ANGLES, key=lambda a: abs(a - angle))
    rad = math.radians(snapped)
    return QPointF(length * math.cos(rad), length * math.sin(rad))


class Path:
    def __init__(self):
        self.anchors = []
        self.closed = False
        self.fill = True
        self.stroke = False
        self.stroke_width = 1.0
        self.stroke_color = QColor(0, 0, 0)
        self.visible = True

    def add_anchor(self, pos, handle_in=None, handle_out=None, type="corner"):
        self.anchors.append(AnchorPoint(pos, handle_in, handle_out, type))
        return len(self.anchors) - 1

    def move_anchor(self, index, new_pos):
        if 0 <= index < len(self.anchors):
            delta = QPointF(
                new_pos.x() - self.anchors[index].position.x(),
                new_pos.y() - self.anchors[index].position.y()
            )
            self.anchors[index].position = QPointF(new_pos)
            self.anchors[index].handle_in += delta
            self.anchors[index].handle_out += delta

    def delete_anchor(self, index):
        if 0 <= index < len(self.anchors):
            del self.anchors[index]

    def insert_anchor_at(self, index, pos, handle_in=None, handle_out=None, type="corner"):
        self.anchors.insert(index, AnchorPoint(pos, handle_in, handle_out, type))
        return index

    def add_anchor_at_segment(self, t, seg_index):
        if seg_index < 0 or seg_index >= len(self.anchors) - 1:
            return None
        a, b = self.anchors[seg_index], self.anchors[seg_index + 1]
        has_cubic = (
            (a.handle_out - a.position).manhattanLength() > 0.5 or
            (b.handle_in - b.position).manhattanLength() > 0.5
        )
        if has_cubic:
            p0, p1, p2, p3 = a.position, a.handle_out, b.handle_in, b.position
            def lerp(p, q, s):
                return QPointF(p.x() + (q.x() - p.x()) * s, p.y() + (q.y() - p.y()) * s)
            q0 = lerp(p0, p1, t)
            q1 = lerp(p1, p2, t)
            q2 = lerp(p2, p3, t)
            r0 = lerp(q0, q1, t)
            r1 = lerp(q1, q2, t)
            mid = lerp(r0, r1, t)
            a.handle_out = q0
            b.handle_in = q2
            self.anchors.insert(seg_index + 1, AnchorPoint(mid, r0, r1, "smooth"))
            return seg_index + 1
        else:
            mid = QPointF(
                a.position.x() + (b.position.x() - a.position.x()) * t,
                a.position.y() + (b.position.y() - a.position.y()) * t
            )
            self.anchors.insert(seg_index + 1, AnchorPoint(mid))
            return seg_index + 1

    def to_qpainterpath(self):
        path = QPainterPath()
        if not self.anchors:
            return path
        path.moveTo(self.anchors[0].position)
        for i in range(1, len(self.anchors)):
            prev = self.anchors[i - 1]
            curr = self.anchors[i]
            has_handle = (
                (prev.handle_out - prev.position).manhattanLength() > 0.5 or
                (curr.handle_in - curr.position).manhattanLength() > 0.5
            )
            if has_handle:
                path.cubicTo(prev.handle_out, curr.handle_in, curr.position)
            else:
                path.lineTo(curr.position)
        if self.closed and len(self.anchors) > 2:
            prev = self.anchors[-1]
            curr = self.anchors[0]
            has_handle = (
                (prev.handle_out - prev.position).manhattanLength() > 0.5 or
                (curr.handle_in - curr.position).manhattanLength() > 0.5
            )
            if has_handle:
                path.cubicTo(prev.handle_out, curr.handle_in, curr.position)
            else:
                path.closeSubpath()
        return path

    def hit_test(self, pos, tolerance=5.0):
        tol_sq = tolerance * tolerance
        for i, anchor in enumerate(self.anchors):
            if (anchor.position - pos).manhattanLength() <= tol_sq:
                return ('anchor', i)
            if (anchor.handle_in - pos).manhattanLength() <= tol_sq:
                return ('handle_in', i)
            if (anchor.handle_out - pos).manhattanLength() <= tol_sq:
                return ('handle_out', i)
        return None

    def segment_hit_test(self, pos, tolerance=5.0):
        if len(self.anchors) < 2:
            return None
        best = None
        best_dist = tolerance
        segments = []
        for i in range(len(self.anchors) - 1):
            segments.append((i, self.anchors[i].position, self.anchors[i + 1].position))
        if self.closed and len(self.anchors) > 2:
            segments.append((len(self.anchors) - 1, self.anchors[-1].position, self.anchors[0].position))
        for idx, a, b in segments:
            ab = b - a
            ap = pos - a
            denom = ab.x()**2 + ab.y()**2
            if denom < 1e-10:
                continue
            t = (ap.x() * ab.x() + ap.y() * ab.y()) / denom
            t = max(0, min(1, t))
            closest = QPointF(a.x() + t * ab.x(), a.y() + t * ab.y())
            d = (closest - pos).manhattanLength()
            if d < best_dist:
                best_dist = d
                best = idx + 1
        return best

    def move_handle(self, index, handle_type, new_pos):
        if 0 <= index < len(self.anchors):
            if handle_type == 'handle_in':
                self.anchors[index].handle_in = QPointF(new_pos)
            elif handle_type == 'handle_out':
                self.anchors[index].handle_out = QPointF(new_pos)

    def rasterize_to(self, image, fill_color=None, stroke_color=None, stroke_width=1.0, aa=True):
        p = QPainter(image)
        if aa:
            p.setRenderHint(QPainter.Antialiasing)
        path = self.to_qpainterpath()
        if self.fill and fill_color:
            p.fillPath(path, QBrush(fill_color))
        elif self.fill:
            p.fillPath(path, QBrush(QColor(0, 0, 0, 0)))
        if self.stroke or stroke_color:
            col = stroke_color or self.stroke_color
            sw = stroke_width if stroke_width else self.stroke_width
            p.setPen(QPen(col, sw))
            p.drawPath(path)
        p.end()

    def to_svg(self):
        if not self.anchors:
            return ""
        parts = [f"M {self.anchors[0].position.x():.3f},{self.anchors[0].position.y():.3f}"]
        for i in range(1, len(self.anchors)):
            prev = self.anchors[i - 1]
            curr = self.anchors[i]
            if ((prev.handle_out - prev.position).manhattanLength() > 0.5 or
                    (curr.handle_in - curr.position).manhattanLength() > 0.5):
                parts.append(
                    f"C {prev.handle_out.x():.3f},{prev.handle_out.y():.3f} "
                    f"{curr.handle_in.x():.3f},{curr.handle_in.y():.3f} "
                    f"{curr.position.x():.3f},{curr.position.y():.3f}"
                )
            else:
                parts.append(f"L {curr.position.x():.3f},{curr.position.y():.3f}")
        if self.closed:
            parts.append("Z")
        return " ".join(parts)

    def copy(self):
        new = Path()
        new.anchors = [a.copy() for a in self.anchors]
        new.closed = self.closed
        new.fill = self.fill
        new.stroke = self.stroke
        new.stroke_width = self.stroke_width
        new.stroke_color = QColor(self.stroke_color)
        new.visible = self.visible
        return new
