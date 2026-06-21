import numpy as np
from PyQt5.QtGui import QImage, QColor


def to_array(img):
    if img.format() != QImage.Format_RGBA8888:
        img = img.convertToFormat(QImage.Format_RGBA8888)
    w, h = img.width(), img.height()
    if w < 1 or h < 1:
        return np.zeros((0, 0, 4), dtype=np.uint8)
    ptr = img.constBits()
    ptr.setsize(h * w * 4)
    return np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4)).copy()


def from_array(arr):
    if arr.size == 0:
        return QImage()
    h, w = arr.shape[:2]
    arr = np.ascontiguousarray(arr)
    qimg = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
    return qimg.copy()


def _convolve(ch, kernel):
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    p = np.pad(ch, ((ph, ph), (pw, pw)), mode='edge')
    h, w = ch.shape
    r = np.zeros_like(ch, dtype=np.float32)
    for y in range(h):
        for x in range(w):
            r[y, x] = np.sum(p[y:y+kh, x:x+kw] * kernel)
    return r


def grayscale(img):
    a = to_array(img).astype(np.float32)
    g = np.dot(a[..., :3], [0.299, 0.587, 0.114])
    a[..., 0] = a[..., 1] = a[..., 2] = g
    return from_array(a.astype(np.uint8))


def invert(img):
    a = to_array(img)
    a[..., :3] = 255 - a[..., :3]
    return from_array(a)


def brightness(img, val):
    a = to_array(img).astype(np.int32)
    a = np.clip(a + val, 0, 255).astype(np.uint8)
    return from_array(a)


def contrast(img, factor):
    a = to_array(img).astype(np.float32)
    a[..., :3] = np.clip(128 + (a[..., :3] - 128) * factor, 0, 255)
    return from_array(a.astype(np.uint8))


def levels(img, shadow=0, mid=1.0, highlight=255):
    a = to_array(img).astype(np.float32)
    d = highlight - shadow
    if d < 1: d = 1
    a[..., :3] = np.clip(((a[..., :3] - shadow) / d) ** mid * 255, 0, 255)
    return from_array(a.astype(np.uint8))


def hue_saturation(img, h_rot=0, sat=1.0, light=0):
    from ._colorspace import rgb_to_hsl, hsl_to_rgb
    a = to_array(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h, s, l = rgb_to_hsl(r, g, b)
    h = (h + h_rot) % 360
    s = np.clip(s * sat, 0, 100)
    l = np.clip(l + light, 0, 100)
    nr, ng, nb = hsl_to_rgb(h, s, l)
    a[..., 0] = np.clip(nr, 0, 255)
    a[..., 1] = np.clip(ng, 0, 255)
    a[..., 2] = np.clip(nb, 0, 255)
    return from_array(a.astype(np.uint8))


def color_balance(img, shadows=(0,0,0), mids=(0,0,0), highlights=(0,0,0)):
    a = to_array(img).astype(np.float32)
    for c in range(3):
        a[..., c] = np.clip(a[..., c] + shadows[c] + mids[c] + highlights[c], 0, 255)
    return from_array(a.astype(np.uint8))


def curves(img, points):
    """points: [(x,y), ...] normalized 0-1"""
    a = to_array(img).astype(np.float32)
    x_vals = np.array([p[0] for p in points]) * 255
    y_vals = np.array([p[1] for p in points]) * 255
    for c in range(3):
        flat = a[..., c].ravel()
        mapped = np.interp(flat, x_vals, y_vals)
        a[..., c] = mapped.reshape(a.shape[:2])
    return from_array(np.clip(a, 0, 255).astype(np.uint8))


def gaussian_blur(img, radius=3):
    k = radius * 2 + 1
    ax = np.linspace(-(k // 2), k // 2, k)
    g = np.exp(-0.5 * (ax / max(1, radius * 0.5)) ** 2)
    kernel = np.outer(g, g)
    kernel /= kernel.sum()
    a = to_array(img).astype(np.float32)
    for c in range(4):
        a[..., c] = _convolve(a[..., c], kernel)
    return from_array(np.clip(a, 0, 255).astype(np.uint8))


def sharpen(img, amount=1.0):
    k = np.array([
        [0, -1, 0],
        [-1, 4+amount, -1],
        [0, -1, 0],
    ], dtype=np.float32)
    a = to_array(img).astype(np.float32)
    for c in range(3):
        a[..., c] = _convolve(a[..., c], k)
    return from_array(np.clip(a, 0, 255).astype(np.uint8))


def edge_detect(img):
    a = to_array(img).astype(np.float32)
    g = np.dot(a[..., :3], [0.299, 0.587, 0.114])
    kx = np.array([[-1,0,1],[-2,0,2],[-1,0,1]], dtype=np.float32)
    ky = np.array([[-1,-2,-1],[0,0,0],[1,2,1]], dtype=np.float32)
    gx = _convolve(g, kx)
    gy = _convolve(g, ky)
    mag = np.clip(np.sqrt(gx**2 + gy**2), 0, 255).astype(np.uint8)
    a[..., 0] = a[..., 1] = a[..., 2] = mag
    return from_array(a.astype(np.uint8))


def pixelate(img, block=8):
    a = to_array(img)
    h, w = a.shape[:2]
    bs = max(2, block)
    for y in range(0, h, bs):
        for x in range(0, w, bs):
            blk = a[y:min(y+bs, h), x:min(x+bs, w)]
            m = blk.mean(axis=(0,1)).astype(np.uint8)
            a[y:min(y+bs, h), x:min(x+bs, w)] = m
    return from_array(a)


def posterize(img, levels=4):
    a = to_array(img).astype(np.float32)
    f = 256 / levels
    a[..., :3] = np.floor(a[..., :3] / f) * f
    return from_array(np.clip(a, 0, 255).astype(np.uint8))


def sepia(img):
    a = to_array(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    a[..., 0] = np.clip(r*0.393 + g*0.769 + b*0.189, 0, 255)
    a[..., 1] = np.clip(r*0.349 + g*0.686 + b*0.168, 0, 255)
    a[..., 2] = np.clip(r*0.272 + g*0.534 + b*0.131, 0, 255)
    return from_array(a.astype(np.uint8))


def adjustment_brightness_contrast(img, params):
    b = params.get('brightness', 0)
    c = params.get('contrast', 100) / 100.0
    a = to_array(img).astype(np.float32)
    a[..., :3] = np.clip(128 + (a[..., :3] - 128) * c + b, 0, 255)
    return from_array(a.astype(np.uint8))


def adjustment_hsl(img, params):
    h_rot = params.get('hue', 0)
    sat = params.get('saturation', 100) / 100.0
    light = params.get('lightness', 0)
    from ._colorspace import rgb_to_hsl, hsl_to_rgb
    a = to_array(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h, s, l = rgb_to_hsl(r, g, b)
    h = (h + h_rot) % 360
    s = np.clip(s * sat, 0, 100)
    l = np.clip(l + light, 0, 100)
    nr, ng, nb = hsl_to_rgb(h, s, l)
    a[..., 0] = np.clip(nr, 0, 255)
    a[..., 1] = np.clip(ng, 0, 255)
    a[..., 2] = np.clip(nb, 0, 255)
    return from_array(a.astype(np.uint8))


def adjustment_levels(img, params):
    shadow = params.get('shadow', 0)
    mid = params.get('mid', 100) / 100.0
    highlight = params.get('highlight', 255)
    a = to_array(img).astype(np.float32)
    d = highlight - shadow
    if d < 1:
        d = 1
    a[..., :3] = np.clip(((a[..., :3] - shadow) / d) ** mid * 255, 0, 255)
    return from_array(a.astype(np.uint8))


def adjustment_curves(img, params):
    points = params.get('points')
    if not points or len(points) < 2:
        return img
    return curves(img, points)


def heal_patch(src_arr, dst_arr, radius):
    """Blend source texture into destination with color matching."""
    src = src_arr.astype(np.float32)
    dst = dst_arr.astype(np.float32)
    src_mean = src.mean(axis=(0, 1))
    dst_mean = dst.mean(axis=(0, 1))
    corrected = src + (dst_mean - src_mean)
    corrected = np.clip(corrected, 0, 255)
    hh, ww = src.shape[:2]
    cy, cx = hh // 2, ww // 2
    Y, X = np.ogrid[:hh, :ww]
    dist = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2)
    max_dist = np.sqrt(cy ** 2 + cx ** 2) + 1
    weight = np.clip(1 - dist / max_dist, 0, 1)
    for c in range(3):
        dst_arr[..., c] = (dst[..., c] * (1 - weight) + corrected[..., c] * weight).astype(np.uint8)
    dst_arr[..., 3] = 255
    return dst_arr


def noise_reduce(img, strength=3):
    a = to_array(img).astype(np.float32)
    k = strength * 2 + 1
    ax = np.linspace(-(k // 2), k // 2, k)
    g = np.exp(-0.5 * (ax / max(1, strength * 0.5)) ** 2)
    kernel = np.outer(g, g)
    kernel /= kernel.sum()
    median = a.copy()
    for c in range(4):
        median[..., c] = _convolve(a[..., c], kernel)
    diff = a - median
    threshold = 20
    mask = np.abs(diff) < threshold
    a = np.where(mask, median, a)
    return from_array(np.clip(a, 0, 255).astype(np.uint8))
