from PyQt5.QtCore import Qt, QPointF, QRectF


class SnappingEngine:
    def __init__(self):
        self.enabled = True
        self.snap_to_grid = True
        self.snap_to_guides = True
        self.snap_to_layer = True
        self.snap_to_document = True
        self.snap_threshold = 8.0

        self.last_snap_info = None

    def snap_point(self, pos, active_layer_rect=None, other_layer_rects=None, guides=None, grid_spacing=None):
        if not self.enabled:
            return pos, None

        snapped = QPointF(pos)
        snap_info = None
        best_dist = self.snap_threshold
        snap_source = None

        def check_snap(val, target, axis):
            nonlocal best_dist, snap_info, snap_source
            d = abs(val - target)
            if d < best_dist:
                best_dist = d
                if axis == "x":
                    return QPointF(target, snapped.y())
                else:
                    return QPointF(snapped.x(), target)
            return None

        def apply_if_better(new_pos, source):
            nonlocal snapped, snap_info, snap_source
            if new_pos is None:
                return
            d = (new_pos - pos).manhattanLength()
            if d < best_dist:
                best_dist = d
                snapped = new_pos
                snap_info = (new_pos, source)
                snap_source = source

        # Grid snap
        if self.snap_to_grid and grid_spacing and grid_spacing > 0:
            sx = round(snapped.x() / grid_spacing) * grid_spacing
            sy = round(snapped.y() / grid_spacing) * grid_spacing
            if abs(sx - pos.x()) < best_dist:
                snapped.setX(sx)
                best_dist = abs(sx - pos.x())
                snap_info = (QPointF(sx, snapped.y()), "Grid")
                snap_source = "Grid"
            if abs(sy - pos.y()) < best_dist:
                snapped.setY(sy)
                best_dist = abs(sy - pos.y())
                snap_info = (QPointF(snapped.x(), sy), "Grid")
                snap_source = "Grid"

        # Guide snap
        if self.snap_to_guides and guides:
            for g in guides:
                if g.orientation == Qt.Vertical:
                    apply_if_better(check_snap(pos.x(), g.position, "x"), "Guide")
                else:
                    apply_if_better(check_snap(pos.y(), g.position, "y"), "Guide")

        # Document bounds snap
        if self.snap_to_document:
            img_w = 800
            img_h = 600
            doc_edges_x = [0, img_w / 2, img_w]
            doc_edges_y = [0, img_h / 2, img_h]
            for ex in doc_edges_x:
                apply_if_better(check_snap(pos.x(), ex, "x"), "Document Bounds")
            for ey in doc_edges_y:
                apply_if_better(check_snap(pos.y(), ey, "y"), "Document Bounds")

        # Layer edges snap
        if self.snap_to_layer and other_layer_rects:
            for lr in other_layer_rects:
                layer_edges_x = [lr.left(), lr.center().x(), lr.right()]
                layer_edges_y = [lr.top(), lr.center().y(), lr.bottom()]
                for ex in layer_edges_x:
                    apply_if_better(check_snap(pos.x(), ex, "x"), "Layer")
                for ey in layer_edges_y:
                    apply_if_better(check_snap(pos.y(), ey, "y"), "Layer")

        return snapped, snap_info

    def snap_rect(self, rect, grid_spacing=None, guides=None, other_layer_rects=None):
        if not self.enabled:
            return rect, None

        snapped_info = None

        corners = [(rect.left(), rect.top()), (rect.right(), rect.top()),
                   (rect.left(), rect.bottom()), (rect.right(), rect.bottom())]
        snapped_corners = [QPointF(*c) for c in corners]

        for i, (cx, cy) in enumerate(corners):
            sp, info = self.snap_point(
                QPointF(cx, cy), grid_spacing=grid_spacing,
                guides=guides, other_layer_rects=other_layer_rects
            )
            snapped_corners[i] = sp
            if info:
                snapped_info = info

        snapped = QRectF(snapped_corners[0], snapped_corners[3])
        return snapped.normalized(), snapped_info
