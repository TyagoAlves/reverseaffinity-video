import os
import numpy as np
from PIL import Image as PILImage
from PyQt5.QtGui import QImage


def qimage_to_pil(qimage):
    if qimage.format() != QImage.Format_RGBA8888:
        qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
    ptr = qimage.constBits()
    ptr.setsize(qimage.sizeInBytes())
    arr = np.frombuffer(ptr, dtype=np.uint8).copy().reshape(qimage.height(), qimage.width(), 4)
    return PILImage.fromarray(arr, 'RGBA')


def pil_to_qimage(pil_image):
    if pil_image.mode != 'RGBA':
        pil_image = pil_image.convert('RGBA')
    arr = np.array(pil_image)
    arr = np.ascontiguousarray(arr)
    qimg = QImage(arr.data, arr.shape[1], arr.shape[0], 4 * arr.shape[1], QImage.Format_RGBA8888)
    return qimg.copy()


from .psd_import import import_psd
from .psd_export import export_psd

FORMAT_REGISTRY = {
    '.psd': {
        'name': 'Photoshop Document',
        'importer': import_psd,
        'exporter': export_psd,
        'export_options': {},
    },
    '.png': {
        'name': 'PNG',
        'native': True,
        'export_options': {'compression': (0, 9, 6)},
    },
    '.jpg': {
        'name': 'JPEG',
        'native': True,
        'export_options': {'quality': (1, 100, 95)},
    },
    '.jpeg': {
        'name': 'JPEG',
        'native': True,
        'export_options': {'quality': (1, 100, 95)},
        'alias': True,
    },
    '.bmp': {
        'name': 'BMP',
        'native': True,
        'export_options': {},
    },
    '.tiff': {
        'name': 'TIFF',
        'native': True,
        'export_options': {'compression': ['none', 'lzw', 'zip']},
    },
    '.tif': {
        'name': 'TIFF',
        'native': True,
        'alias': True,
    },
    '.webp': {
        'name': 'WebP',
        'native': True,
        'export_options': {'quality': (1, 100, 80)},
    },
}


def get_open_filter():
    filters = []
    for ext, info in FORMAT_REGISTRY.items():
        if info.get('alias'):
            continue
        if info.get('importer') or info.get('native'):
            filters.append(f"{info['name']} (*{ext})")
    filters.append("All Files (*)")
    return ";;".join(filters)


def get_save_filter():
    filters = []
    for ext, info in FORMAT_REGISTRY.items():
        if info.get('alias'):
            continue
        if info.get('exporter') or info.get('native'):
            filters.append(f"{info['name']} (*{ext})")
    return ";;".join(filters)


def get_export_options_for_format(ext):
    info = FORMAT_REGISTRY.get(ext)
    if info:
        return info.get('export_options', {})
    return {}


def get_format_for_filename(path):
    _, ext = os.path.splitext(path)
    return ext.lower()
