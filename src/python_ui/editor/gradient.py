"""
Gradient data model for gradient editor.
"""

import json
import math
from PyQt5.QtCore import QPointF, QLineF
from PyQt5.QtGui import (
    QColor, QLinearGradient, QRadialGradient, QConicalGradient, QGradient,
)


class GradientStop:
    def __init__(self, position, color, midpoint=0.5):
        self.position = max(0.0, min(1.0, position))
        self.color = QColor(color) if not isinstance(color, QColor) else QColor(color)
        self.midpoint = max(0.0, min(1.0, midpoint))

    def to_dict(self):
        return {
            "position": self.position,
            "color": self.color.name(),
            "alpha": self.color.alpha(),
            "midpoint": self.midpoint,
        }

    @classmethod
    def from_dict(cls, data):
        c = QColor(data["color"])
        c.setAlpha(data.get("alpha", 255))
        return cls(data["position"], c, data.get("midpoint", 0.5))


class Gradient:
    def __init__(self, gtype="linear"):
        self.type = gtype
        self.stops = []
        self.repeat = "none"

    def add_stop(self, position, color):
        stop = GradientStop(position, color)
        self.stops.append(stop)
        self.sort_stops()
        return stop

    def remove_stop(self, index):
        if 0 <= index < len(self.stops):
            self.stops.pop(index)

    def sort_stops(self):
        self.stops.sort(key=lambda s: s.position)

    def to_qgradient(self, start, end):
        if self.type == "linear":
            g = QLinearGradient(start, end)
        elif self.type == "radial":
            radius = QLineF(start, end).length()
            g = QRadialGradient(start, radius) if radius > 0 else QRadialGradient(start, 1)
        elif self.type == "conical":
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            angle = math.degrees(math.atan2(-dy, dx)) if dx != 0 or dy != 0 else 0
            g = QConicalGradient(start, angle)
        else:
            g = QLinearGradient(start, end)

        spread_map = {
            "none": QGradient.SpreadPad,
            "repeat": QGradient.SpreadRepeat,
            "reflect": QGradient.SpreadReflect,
        }
        g.setSpread(spread_map.get(self.repeat, QGradient.SpreadPad))

        for stop in self.stops:
            g.setColorAt(stop.position, stop.color)

        return g

    def to_dict(self):
        return {
            "type": self.type,
            "repeat": self.repeat,
            "stops": [s.to_dict() for s in self.stops],
        }

    @classmethod
    def from_dict(cls, data):
        g = cls(data.get("type", "linear"))
        g.repeat = data.get("repeat", "none")
        for sd in data.get("stops", []):
            g.stops.append(GradientStop.from_dict(sd))
        return g


DEFAULT_PRESETS = [
    {
        "name": "Black to White",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#000000", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#ffffff", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Foreground to Background",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#000000", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#ffffff", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Foreground to Transparent",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#000000", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#000000", "alpha": 0, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "White to Transparent",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#ffffff", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#ffffff", "alpha": 0, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Rainbow",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.00, "color": "#ff0000", "alpha": 255, "midpoint": 0.5},
                {"position": 0.17, "color": "#ffff00", "alpha": 255, "midpoint": 0.5},
                {"position": 0.33, "color": "#00ff00", "alpha": 255, "midpoint": 0.5},
                {"position": 0.50, "color": "#00ffff", "alpha": 255, "midpoint": 0.5},
                {"position": 0.67, "color": "#0000ff", "alpha": 255, "midpoint": 0.5},
                {"position": 0.83, "color": "#ff00ff", "alpha": 255, "midpoint": 0.5},
                {"position": 1.00, "color": "#ff0000", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Transparent",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#000000", "alpha": 0, "midpoint": 0.5},
                {"position": 1.0, "color": "#000000", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Copper",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#000000", "alpha": 255, "midpoint": 0.5},
                {"position": 0.4, "color": "#804020", "alpha": 255, "midpoint": 0.5},
                {"position": 0.8, "color": "#c08040", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#ffffff", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Gold",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#000000", "alpha": 255, "midpoint": 0.5},
                {"position": 0.3, "color": "#806020", "alpha": 255, "midpoint": 0.5},
                {"position": 0.6, "color": "#c0a040", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#ffffff", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Warm",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#ff0000", "alpha": 255, "midpoint": 0.5},
                {"position": 0.5, "color": "#ff8800", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#ffff00", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
    {
        "name": "Cool",
        "gradient": {
            "type": "linear",
            "repeat": "none",
            "stops": [
                {"position": 0.0, "color": "#0000ff", "alpha": 255, "midpoint": 0.5},
                {"position": 0.5, "color": "#00aaff", "alpha": 255, "midpoint": 0.5},
                {"position": 1.0, "color": "#00ffff", "alpha": 255, "midpoint": 0.5},
            ],
        },
    },
]
