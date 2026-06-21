import numpy as np


def rgb_to_hsl(r, g, b):
    r, g, b = r / 255.0 * 100, g / 255.0 * 100, b / 255.0 * 100
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    l = (mx + mn) / 2
    d = mx - mn
    s = np.zeros_like(r)
    h = np.zeros_like(r)

    mask = d > 0
    s = np.where(mask & (l > 50), d / (200 - mx - mn) * 100, s)
    s = np.where(mask & (l <= 50), d / (mx + mn) * 100, s)

    h = np.where(mask & (mx == r), 60 * ((g - b) / d % 6), h)
    h = np.where(mask & (mx == g), 60 * ((b - r) / d + 2), h)
    h = np.where(mask & (mx == b), 60 * ((r - g) / d + 4), h)
    h = (h + 360) % 360
    return h, s, l


def hsl_to_rgb(h, s, l):
    h, s, l = h / 360.0, s / 100.0, l / 100.0

    def hue2rgb(p, q, t):
        t = t % 1.0
        return np.where(t < 1/6, p + (q - p) * 6 * t,
               np.where(t < 1/2, q,
               np.where(t < 2/3, p + (q - p) * (2/3 - t) * 6, p)))

    q = np.where(l < 0.5, l * (1 + s), l + s - l * s)
    p = 2 * l - q

    r = hue2rgb(p, q, h + 1/3)
    g = hue2rgb(p, q, h)
    b = hue2rgb(p, q, h - 1/3)

    return r * 255, g * 255, b * 255

