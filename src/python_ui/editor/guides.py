import json
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont


class Guide:
    def __init__(self, orientation, position):
        self.orientation = orientation
        self.position = position

    def to_dict(self):
        return {"orientation": self.orientation, "position": self.position}

    @classmethod
    def from_dict(cls, d):
        return cls(d["orientation"], d["position"])


class GuideManager:
    def __init__(self):
        self.guides = []
        self.visible = True
        self.locked = False

    def add_guide(self, orientation, pos):
        self.guides.append(Guide(orientation, pos))

    def remove_guide(self, index):
        if 0 <= index < len(self.guides):
            del self.guides[index]

    def clear_guides(self):
        self.guides.clear()

    def hit_test(self, pos, threshold):
        for i, g in enumerate(self.guides):
            if g.orientation == Qt.Vertical and abs(pos.x() - g.position) <= threshold:
                return i
            if g.orientation == Qt.Horizontal and abs(pos.y() - g.position) <= threshold:
                return i
        return -1

    def draw(self, painter, image_size):
        if not self.visible:
            return
        painter.save()
        pen = QPen(QColor(0, 180, 255, 200), 1)
        painter.setPen(pen)
        w, h = image_size.width(), image_size.height()
        for g in self.guides:
            if g.orientation == Qt.Vertical:
                painter.drawLine(QPointF(g.position, 0), QPointF(g.position, h))
            else:
                painter.drawLine(QPointF(0, g.position), QPointF(w, g.position))
        painter.restore()

    def save_to_file(self, path):
        data = [g.to_dict() for g in self.guides]
        with open(path, "w") as f:
            json.dump(data, f)

    def load_from_file(self, path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.guides = [Guide.from_dict(d) for d in data]
        except (FileNotFoundError, json.JSONDecodeError):
            self.guides = []
