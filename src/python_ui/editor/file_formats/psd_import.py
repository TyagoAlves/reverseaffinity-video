import numpy as np
from PIL import Image as PILImage
from psd_tools import PSDImage
from psd_tools.constants import BlendMode, ColorMode
from PyQt5.QtGui import QImage

from ..layers import LayerStack, Layer
from . import pil_to_qimage


PSD_BLEND_MAP = {
    BlendMode.NORMAL: 'Normal',
    BlendMode.MULTIPLY: 'Multiply',
    BlendMode.SCREEN: 'Screen',
    BlendMode.OVERLAY: 'Overlay',
    BlendMode.DARKEN: 'Darken',
    BlendMode.LIGHTEN: 'Lighten',
    BlendMode.COLOR_DODGE: 'Color Dodge',
    BlendMode.COLOR_BURN: 'Color Burn',
    BlendMode.HARD_LIGHT: 'Hard Light',
    BlendMode.SOFT_LIGHT: 'Soft Light',
    BlendMode.DIFFERENCE: 'Difference',
    BlendMode.EXCLUSION: 'Exclusion',
    BlendMode.HUE: 'Hue',
    BlendMode.SATURATION: 'Saturation',
    BlendMode.COLOR: 'Color',
    BlendMode.LUMINOSITY: 'Luminosity',
}


def _extract_layers(psd_layers, width, height, parent=None):
    result = []
    for psd_layer in psd_layers:
        if psd_layer.is_group():
            result.extend(_extract_layers(psd_layer, width, height, psd_layer))
        else:
            try:
                if not psd_layer.has_pixels():
                    continue
                pil_img = psd_layer.composite()
                if pil_img is None:
                    continue
                if pil_img.mode not in ('RGBA', 'RGB', 'L', 'P'):
                    pil_img = pil_img.convert('RGBA')
                if pil_img.mode == 'P':
                    pil_img = pil_img.convert('RGBA')
                elif pil_img.mode in ('RGB', 'L'):
                    pil_img = pil_img.convert('RGBA')

                qimg = pil_to_qimage(pil_img)
                if qimg.width() != width or qimg.height() != height:
                    scaled = qimg.scaled(width, height, 0, 1)
                    qimg = scaled

                layer = Layer(width, height, psd_layer.name or f"Layer {len(result)}")
                layer.image = qimg
                layer.visible = psd_layer.visible
                layer.opacity = psd_layer.opacity / 255.0
                layer.blend_mode = PSD_BLEND_MAP.get(psd_layer.blend_mode, 'Normal')
                result.append(layer)
            except Exception:
                continue
    return result


def import_psd(path):
    try:
        psd = PSDImage.open(path)
    except Exception:
        return None

    width, height = psd.width, psd.height

    extracted = _extract_layers(psd, width, height)

    if not extracted:
        pil_img = psd.composite()
        if pil_img is None:
            return None
        if pil_img.mode not in ('RGBA', 'RGB'):
            pil_img = pil_img.convert('RGBA')
        qimg = pil_to_qimage(pil_img)
        layer_stack = LayerStack(width, height)
        layer_stack.layers[0].image = qimg
        layer_stack.active_index = 0
        return layer_stack

    layer_stack = LayerStack(width, height)
    layer_stack.layers.clear()
    layer_stack.layers = extracted
    layer_stack.active_index = 0
    return layer_stack
