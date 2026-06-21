from psd_tools import PSDImage
from psd_tools.constants import BlendMode
from PIL import Image as PILImage

from . import qimage_to_pil


US_BLEND_TO_PSD = {
    'Normal': BlendMode.NORMAL,
    'Multiply': BlendMode.MULTIPLY,
    'Screen': BlendMode.SCREEN,
    'Overlay': BlendMode.OVERLAY,
    'Darken': BlendMode.DARKEN,
    'Lighten': BlendMode.LIGHTEN,
    'Color Dodge': BlendMode.COLOR_DODGE,
    'Color Burn': BlendMode.COLOR_BURN,
    'Hard Light': BlendMode.HARD_LIGHT,
    'Soft Light': BlendMode.SOFT_LIGHT,
    'Difference': BlendMode.DIFFERENCE,
    'Exclusion': BlendMode.EXCLUSION,
    'Hue': BlendMode.HUE,
    'Saturation': BlendMode.SATURATION,
    'Color': BlendMode.COLOR,
    'Luminosity': BlendMode.LUMINOSITY,
}


def export_psd(path, layer_stack):
    try:
        layers = layer_stack.layers
        if not layers:
            return False

        w = layers[0].image.width()
        h = layers[0].image.height()

        psd = PSDImage.new('RGBA', (w, h), (0, 0, 0, 0))

        for layer in layers:
            if not layer.visible:
                continue
            try:
                pil_img = qimage_to_pil(layer.image)
                opacity = max(0, min(255, int(layer.opacity * 255)))
                blend = US_BLEND_TO_PSD.get(layer.blend_mode, BlendMode.NORMAL)
                psd.create_pixel_layer(pil_img, name=layer.name,
                                       opacity=opacity, blend_mode=blend)
            except Exception:
                continue

        psd.save(path)
        return True
    except Exception:
        return False
