from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor, QPainter
import numpy as np

from .blend_modes import BLEND_FUNCTIONS, blend_normal

BLEND_FUNCS = BLEND_FUNCTIONS
BLEND_MODES = list(BLEND_FUNCS.keys())


def _float_array_to_qimage(arr, w, h):
    u8 = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    u8 = np.ascontiguousarray(u8)
    qimg = QImage(u8.data, w, h, 4 * w, QImage.Format_RGBA8888)
    return qimg.copy()


def _qimage_to_float_array(img):
    w, h = img.width(), img.height()
    if img.format() != QImage.Format_RGBA8888:
        img = img.convertToFormat(QImage.Format_RGBA8888)
    ptr = img.constBits()
    ptr.setsize(img.sizeInBytes())
    arr = np.frombuffer(ptr, dtype=np.uint8).copy().reshape(h, w, 4)
    return arr.astype(np.float32) / 255.0


class Layer:
    def __init__(self, width, height, name="Background", fill=None):
        w = max(0, int(width))
        h = max(0, int(height))
        self.name = name
        self.image = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        self.image.fill(fill if fill is not None else (Qt.white if name == "Background" else Qt.transparent))
        self.visible = True
        self.locked = False
        self.opacity = 1.0
        self.fill = 1.0
        self.blend_mode = "Normal"
        self.parent_group = None
        self.mask = None
        self.mask_enabled = True
        self.mask_linked = True

    def copy(self):
        l = Layer(self.image.width(), self.image.height(), self.name + " (copy)")
        l.image = self.image.copy()
        l.visible = self.visible
        l.locked = self.locked
        l.opacity = self.opacity
        l.fill = self.fill
        l.blend_mode = self.blend_mode
        l.parent_group = self.parent_group
        l.mask = self.mask.copy() if self.mask is not None else None
        l.mask_enabled = self.mask_enabled
        l.mask_linked = self.mask_linked
        return l

    def reveal_all_mask(self):
        w, h = self.image.width(), self.image.height()
        self.mask = QImage(w, h, QImage.Format_RGBA8888)
        self.mask.fill(Qt.white)
        self.mask_enabled = True

    def hide_all_mask(self):
        w, h = self.image.width(), self.image.height()
        self.mask = QImage(w, h, QImage.Format_RGBA8888)
        self.mask.fill(Qt.black)
        self.mask_enabled = True

    def delete_mask(self):
        self.mask = None
        self.mask_enabled = True

    def apply_mask(self):
        if self.mask is None:
            return
        w, h = self.image.width(), self.image.height()
        ptr = self.image.constBits()
        ptr.setsize(self.image.sizeInBytes())
        img_arr = np.frombuffer(ptr, dtype=np.uint8).copy().reshape(h, w, 4)
        mask_img = self.mask
        if mask_img.width() != w or mask_img.height() != h:
            mask_img = mask_img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        mptr = mask_img.constBits()
        mptr.setsize(mask_img.sizeInBytes())
        mask_arr = np.frombuffer(mptr, dtype=np.uint8).reshape(h, w, 4)
        mask_gray = mask_arr[:, :, 0].astype(np.float32) / 255.0
        img_arr[:, 3] = (img_arr[:, 3].astype(np.float32) * mask_gray).astype(np.uint8)
        self.image = QImage(img_arr.data, w, h, w * 4, QImage.Format_ARGB32_Premultiplied).copy()
        self.mask = None

    def toggle_mask(self):
        self.mask_enabled = not self.mask_enabled


class AdjustmentLayer(Layer):
    def __init__(self, width, height, name="Adjustment", filter_func=None, params=None):
        super().__init__(width, height, name, Qt.transparent)
        self.filter_func = filter_func
        self.params = params or {}
        self.image.fill(Qt.transparent)

    def copy(self):
        adj = AdjustmentLayer(self.image.width(), self.image.height(),
                              self.name + " (copy)", self.filter_func, self.params.copy())
        adj.image = self.image.copy()
        adj.visible = self.visible
        adj.locked = self.locked
        adj.opacity = self.opacity
        adj.fill = self.fill
        adj.blend_mode = self.blend_mode
        return adj


class GroupLayer:
    def __init__(self, name="Group"):
        self.name = name
        self.visible = True
        self.locked = False
        self.opacity = 1.0
        self.fill = 1.0
        self.blend_mode = "Normal"
        self.children = []
        self.expanded = True

    def add_child(self, child):
        self.children.append(child)

    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)


class LayerStack:
    def __init__(self, width=800, height=600):
        self.layers = [Layer(width, height, "Background")]
        self.active_index = 0
        self._cache = None
        self._cache_dirty = True

    def invalidate_cache(self):
        self._cache_dirty = True
        self._cache = None

    @property
    def active(self):
        return self._get(self.active_index)

    def _get(self, idx):
        if 0 <= idx < len(self.layers):
            return self.layers[idx]
        return None

    def add_layer(self, name=None):
        if not self.layers:
            return None
        w, h = self.layers[0].image.width(), self.layers[0].image.height()
        idx = len(self.layers)
        layer = Layer(w, h, name or f"Layer {idx}", Qt.transparent)
        self.layers.append(layer)
        self.active_index = idx
        self.invalidate_cache()
        return layer

    def add_background(self, color=QColor(Qt.white)):
        if not self.layers:
            return
        w, h = self.layers[0].image.width(), self.layers[0].image.height()
        idx = len(self.layers)
        layer = Layer(w, h, f"Background", color)
        self.layers.insert(0, layer)
        self.active_index = idx + 1
        self.invalidate_cache()

    def add_group(self, name=None):
        idx = len(self.layers)
        group = GroupLayer(name or f"Group {idx}")
        self.layers.append(group)
        self.active_index = idx
        self.invalidate_cache()
        return group

    def is_group(self, index):
        return 0 <= index < len(self.layers) and isinstance(self.layers[index], GroupLayer)

    def get_child_count(self, index):
        if self.is_group(index):
            return len(self.layers[index].children)
        return 0

    def group_layers(self, indices):
        if not indices:
            return None
        sorted_idx = sorted(indices)
        first_idx = sorted_idx[0]
        to_group = [self.layers[i] for i in sorted_idx if 0 <= i < len(self.layers)]
        if not to_group:
            return None
        group = GroupLayer(f"Group")
        for l in to_group:
            self._remove_child_ref(l)
        for i in reversed(sorted_idx):
            if 0 <= i < len(self.layers):
                self.layers.pop(i)
        if first_idx >= len(self.layers):
            first_idx = len(self.layers)
        group.children = list(to_group)
        self.layers.insert(first_idx, group)
        self.active_index = first_idx
        self.invalidate_cache()
        return group

    def ungroup(self, index):
        if not self.is_group(index):
            return
        group = self.layers[index]
        children = list(group.children)
        group.children.clear()
        self.layers[index:index + 1] = children
        if self.active_index > index:
            self.active_index += len(children) - 1
        elif self.active_index == index:
            self.active_index = index
        self.invalidate_cache()

    def move_to_group(self, layer_idx, group_idx):
        if layer_idx == group_idx:
            return
        if not self.is_group(group_idx):
            return
        if layer_idx < 0 or layer_idx >= len(self.layers):
            return
        layer = self.layers[layer_idx]
        if isinstance(layer, GroupLayer):
            return
        self._remove_child_ref(layer)
        self.layers.pop(layer_idx)
        if group_idx > layer_idx:
            group_idx -= 1
        group = self.layers[group_idx]
        insert_pos = group_idx + 1
        self.layers.insert(insert_pos, layer)
        group.children.append(layer)
        self.active_index = insert_pos
        self.invalidate_cache()

    def _remove_child_ref(self, layer):
        for l in self.layers:
            if isinstance(l, GroupLayer) and layer in l.children:
                l.children.remove(layer)
                break

    def _collect_child_ids(self, group, id_set):
        for child in group.children:
            id_set.add(id(child))
            if isinstance(child, GroupLayer):
                self._collect_child_ids(child, id_set)

    def _get_removal_indices(self, index):
        layer = self.layers[index]
        indices = {index}
        if isinstance(layer, GroupLayer):
            for child in layer.children:
                for i, l in enumerate(self.layers):
                    if l is child:
                        indices.update(self._get_removal_indices(i))
                        break
        return indices

    def remove_layer(self, index):
        if len(self.layers) <= 1:
            return
        if not (0 <= index < len(self.layers)):
            return
        to_remove = self._get_removal_indices(index)
        for idx in sorted(to_remove, reverse=True):
            l = self.layers[idx]
            if not isinstance(l, GroupLayer):
                self._remove_child_ref(l)
        for idx in sorted(to_remove, reverse=True):
            self.layers.pop(idx)
        if self.active_index in to_remove:
            if self.active_index >= len(self.layers):
                self.active_index = max(0, len(self.layers) - 1)
        else:
            removed_before = sum(1 for idx in to_remove if idx < self.active_index)
            self.active_index -= removed_before
        self.invalidate_cache()

    def clear(self):
        self.layers.clear()
        self.active_index = 0
        self.invalidate_cache()

    def move_layer(self, from_idx, to_idx):
        if not (0 <= from_idx < len(self.layers) and 0 <= to_idx < len(self.layers)):
            return
        if from_idx == to_idx:
            return
        layer = self.layers[from_idx]
        if isinstance(layer, GroupLayer):
            self.layers.insert(to_idx, self.layers.pop(from_idx))
            self.active_index = to_idx - (1 if to_idx > from_idx else 0)
            return
        parent = self._find_parent_group(layer)
        if parent is not None:
            parent.children.remove(layer)
        self.layers.insert(to_idx, self.layers.pop(from_idx))
        new_parent = self._find_parent_group_at(to_idx)
        if new_parent is not None:
            new_parent.children.append(layer)
        self.active_index = to_idx
        self.invalidate_cache()

    def _find_parent_group(self, layer):
        for l in self.layers:
            if isinstance(l, GroupLayer) and layer in l.children:
                return l
        return None

    def _find_parent_group_at(self, flat_idx):
        for i in range(flat_idx - 1, -1, -1):
            l = self.layers[i]
            if isinstance(l, GroupLayer):
                return l
        return None

    def duplicate_layer(self, index):
        if not (0 <= index < len(self.layers)):
            return
        layer = self.layers[index]
        if isinstance(layer, GroupLayer):
            new_group = self._deep_copy_group(layer)
            new_group.name = f"{layer.name} (copy)"
            self.layers.insert(index + 1, new_group)
            self.active_index = index + 1
        else:
            new_layer = layer.copy()
            self.layers.insert(index + 1, new_layer)
            self.active_index = index + 1
        self.invalidate_cache()

    def _deep_copy_group(self, group):
        new_group = GroupLayer(group.name)
        new_group.visible = group.visible
        new_group.locked = group.locked
        new_group.opacity = group.opacity
        new_group.fill = group.fill
        new_group.blend_mode = group.blend_mode
        new_group.expanded = group.expanded
        for child in group.children:
            if isinstance(child, GroupLayer):
                new_child = self._deep_copy_group(child)
            else:
                new_child = child.copy()
            new_group.children.append(new_child)
        return new_group

    def flatten(self):
        if len(self.layers) == 1:
            return
        composite = self.composite()
        self.layers = [Layer(composite.width(), composite.height(), "Flattened")]
        self.layers[0].image = composite
        self.active_index = 0

    def merge_visible(self):
        self.invalidate_cache()
        composite = self.composite()
        self.layers = [Layer(composite.width(), composite.height(), "Merged")]
        self.layers[0].image = composite
        self.active_index = 0

    def composite(self):
        if not self._cache_dirty and self._cache is not None and not self._cache.isNull():
            return self._cache
        if not self.layers:
            return QImage()
        w, h = 800, 600
        for l in self.layers:
            if isinstance(l, Layer):
                w, h = l.image.width(), l.image.height()
                break
        result = np.zeros((h, w, 4), dtype=np.float32)
        child_ids = set()
        for l in self.layers:
            if isinstance(l, GroupLayer):
                self._collect_child_ids(l, child_ids)
        for layer in self.layers:
            if id(layer) in child_ids:
                continue
            if isinstance(layer, GroupLayer):
                if layer.visible:
                    self._composite_group_into(layer, result, w, h)
            elif layer.visible:
                self._composite_layer_into(layer, result, w, h)
        self._cache = _float_array_to_qimage(result, w, h)
        self._cache_dirty = False
        return self._cache

    def _composite_layer_into(self, layer, result, w, h):
        if isinstance(layer, AdjustmentLayer):
            if layer.filter_func:
                qimg = _float_array_to_qimage(result, w, h)
                result_qimg = layer.filter_func(qimg, layer.params)
                adjusted = _qimage_to_float_array(result_qimg)
                blend_func = BLEND_FUNCS.get(layer.blend_mode, blend_normal)
                blend_rgb = blend_func(result[:, :, :3], adjusted[:, :, :3])
                alpha = layer.opacity
                a = alpha
                result[:, :, :3] = blend_rgb * a + result[:, :, :3] * (1.0 - a)
                result[:, :, 3] = adjusted[:, :, 3] * a + result[:, :, 3] * (1.0 - a)
            return
        img = layer.image
        iw, ih = img.width(), img.height()
        if iw != w or ih != h:
            img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        if img.format() != QImage.Format_RGBA8888:
            img = img.convertToFormat(QImage.Format_RGBA8888)
        ptr = img.constBits()
        ptr.setsize(img.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).copy().reshape(ih, iw, 4)
        layer_arr = arr.astype(np.float32) / 255.0
        if layer.mask is not None and layer.mask_enabled:
            mw, mh = layer.mask.width(), layer.mask.height()
            mptr = layer.mask.constBits()
            mptr.setsize(layer.mask.sizeInBytes())
            m_arr = np.frombuffer(mptr, dtype=np.uint8).copy().reshape(mh, mw, 4)
            if mw != w or mh != h:
                mask_img = layer.mask.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                mptr2 = mask_img.constBits()
                mptr2.setsize(mask_img.sizeInBytes())
                m_arr = np.frombuffer(mptr2, dtype=np.uint8).copy().reshape(h, w, 4)
            mask_alpha = m_arr[:, :, 0].astype(np.float32) / 255.0
            layer_arr[:, :, 3] = layer_arr[:, :, 3] * mask_alpha
        blend_func = BLEND_FUNCS.get(layer.blend_mode, blend_normal)
        blend_rgb = blend_func(result[:, :, :3], layer_arr[:, :, :3])
        layer_arr[:, :, 3] = layer_arr[:, :, 3] * layer.fill
        alpha = layer_arr[:, :, 3] * layer.opacity
        a = alpha[:, :, np.newaxis]
        result[:, :, :3] = blend_rgb * a + result[:, :, :3] * (1.0 - a)
        result[:, :, 3] = alpha + result[:, :, 3] * (1.0 - alpha)

    def _composite_group_into(self, group, result, w, h):
        if not group.visible:
            return
        group_result = np.zeros((h, w, 4), dtype=np.float32)
        for child in group.children:
            if isinstance(child, GroupLayer):
                self._composite_group_into(child, group_result, w, h)
            elif child.visible:
                self._composite_layer_into(child, group_result, w, h)
        blend_func = BLEND_FUNCS.get(group.blend_mode, blend_normal)
        blend_rgb = blend_func(result[:, :, :3], group_result[:, :, :3])
        alpha = group_result[:, :, 3] * group.opacity
        a = alpha[:, :, np.newaxis]
        result[:, :, :3] = blend_rgb * a + result[:, :, :3] * (1.0 - a)
        result[:, :, 3] = alpha + result[:, :, 3] * (1.0 - alpha)
