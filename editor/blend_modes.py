"""
Blend mode functions for reverseaffinity.
Provides 14 blend modes with automatic GPU acceleration.
Falls back to CPU (NumPy) when no GPU backend is available.
"""

import numpy as np

try:
    from .gpu_accel import GPUAccel
    _gpu = GPUAccel.get_instance()
except Exception:
    _gpu = None


def _try_gpu(bottom, top, mode):
    """Try GPU blend; returns None on failure."""
    if _gpu is None or not _gpu.is_active:
        return None
    try:
        return _gpu.blend(bottom, top, mode, 1.0)
    except Exception:
        return None


def blend_normal(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'normal')
    if gpu is not None:
        return gpu
    if opacity >= 1.0:
        return top
    return bottom * (1.0 - opacity) + top * opacity


def blend_multiply(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'multiply')
    if gpu is not None:
        return gpu
    result = bottom * top
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_screen(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'screen')
    if gpu is not None:
        return gpu
    result = 1.0 - (1.0 - bottom) * (1.0 - top)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_overlay(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'overlay')
    if gpu is not None:
        return gpu
    mask = bottom < 0.5
    result = np.where(mask, 2.0 * bottom * top, 1.0 - 2.0 * (1.0 - bottom) * (1.0 - top))
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_darken(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'darken')
    if gpu is not None:
        return gpu
    result = np.minimum(bottom, top)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_lighten(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'lighten')
    if gpu is not None:
        return gpu
    result = np.maximum(bottom, top)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_difference(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'difference')
    if gpu is not None:
        return gpu
    result = np.abs(bottom - top)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_add(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'add')
    if gpu is not None:
        return gpu
    result = np.clip(bottom + top, 0.0, 1.0)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_subtract(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'subtract')
    if gpu is not None:
        return gpu
    result = np.clip(bottom - top, 0.0, 1.0)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_color_dodge(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'dodge')
    if gpu is not None:
        return gpu
    result = np.divide(bottom, 1.0 - top, out=np.ones_like(bottom), where=top < 0.999)
    result = np.clip(result, 0.0, 1.0)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_color_burn(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'burn')
    if gpu is not None:
        return gpu
    result = 1.0 - np.divide(1.0 - bottom, top, out=np.zeros_like(bottom), where=top > 0.001)
    result = np.clip(result, 0.0, 1.0)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_hard_light(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'hard light')
    if gpu is not None:
        return gpu
    mask = top < 0.5
    result = np.where(mask, 2.0 * bottom * top, 1.0 - 2.0 * (1.0 - bottom) * (1.0 - top))
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_soft_light(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'soft light')
    if gpu is not None:
        return gpu
    mask = top < 0.5
    result = np.where(
        mask,
        2.0 * bottom * top + bottom * bottom * (1.0 - 2.0 * top),
        np.sqrt(bottom) * (2.0 * top - 1.0) + 2.0 * bottom * (1.0 - top),
    )
    result = np.clip(result, 0.0, 1.0)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_exclusion(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'exclusion')
    if gpu is not None:
        return gpu
    result = bottom + top - 2.0 * bottom * top
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_hue(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'hue')
    if gpu is not None:
        return gpu
    result = np.copy(bottom)
    b_hsv = np.empty_like(bottom)
    t_hsv = np.empty_like(top)
    for i in range(3):
        b_hsv[..., i] = bottom[..., i]
        t_hsv[..., i] = top[..., i]
    b_min = bottom.min(axis=2)
    b_max = bottom.max(axis=2)
    t_min = top.min(axis=2)
    t_max = top.max(axis=2)
    b_c = b_max - b_min
    t_c = t_max - t_min
    b_l = b_max
    t_l = t_max
    b_s = np.divide(b_c, b_max, out=np.zeros_like(b_c), where=b_max > 1e-8)
    t_s = np.divide(t_c, t_max, out=np.zeros_like(t_c), where=t_max > 1e-8)
    b_h = np.zeros_like(b_c)
    b_r, b_g, b_b = bottom[..., 0], bottom[..., 1], bottom[..., 2]
    mask_r = (b_max == b_r) & (b_c > 1e-8)
    mask_g = (b_max == b_g) & (b_c > 1e-8)
    mask_b = (b_max == b_b) & (b_c > 1e-8)
    frac_gb = np.divide(b_g - b_b, b_c, out=np.zeros_like(b_c), where=b_c > 1e-8)
    frac_rb = np.divide(b_b - b_r, b_c, out=np.zeros_like(b_c), where=b_c > 1e-8)
    frac_rg = np.divide(b_r - b_g, b_c, out=np.zeros_like(b_c), where=b_c > 1e-8)
    idx = np.where(b_max == b_r, 6.0 + frac_gb, np.where(b_max == b_g, 2.0 + frac_rb, 4.0 + frac_rg))
    b_h = np.where(b_c > 1e-8, idx * 60.0, 0.0)
    b_h = b_h % 360.0
    t_h = np.zeros_like(t_c)
    t_r, t_g, t_b = top[..., 0], top[..., 1], top[..., 2]
    mask_r_t = (t_max == t_r) & (t_c > 1e-8)
    mask_g_t = (t_max == t_g) & (t_c > 1e-8)
    mask_b_t = (t_max == t_b) & (t_c > 1e-8)
    frac_gb_t = np.divide(t_g - t_b, t_c, out=np.zeros_like(t_c), where=t_c > 1e-8)
    frac_rb_t = np.divide(t_b - t_r, t_c, out=np.zeros_like(t_c), where=t_c > 1e-8)
    frac_rg_t = np.divide(t_r - t_g, t_c, out=np.zeros_like(t_c), where=t_c > 1e-8)
    idx_t = np.where(t_max == top[..., 0], 6.0 + frac_gb_t, np.where(t_max == top[..., 1], 2.0 + frac_rb_t, 4.0 + frac_rg_t))
    t_h = np.where(t_c > 1e-8, idx_t * 60.0, 0.0)
    t_h = t_h % 360.0
    h_ratio = t_h / 360.0
    hi = np.floor(h_ratio * 6.0).astype(np.int32)
    f = h_ratio * 6.0 - hi
    p = b_l * (1.0 - b_s)
    q = b_l * (1.0 - f * b_s)
    t_val = b_l * (1.0 - (1.0 - f) * b_s)
    hi_mod = hi % 6
    out = np.zeros_like(bottom)
    for ci in range(3):
        out[..., ci] = np.select(
            [hi_mod == 0, hi_mod == 1, hi_mod == 2, hi_mod == 3, hi_mod == 4, hi_mod == 5],
            [b_l, q, p, p, t_val, b_l],
        )
    out2 = np.zeros_like(bottom)
    for ci in range(3):
        out2[..., ci] = np.select(
            [hi_mod == 0, hi_mod == 1, hi_mod == 2, hi_mod == 3, hi_mod == 4, hi_mod == 5],
            [t_val, b_l, b_l, q, p, p],
        )
    out3 = np.zeros_like(bottom)
    for ci in range(3):
        out3[..., ci] = np.select(
            [hi_mod == 0, hi_mod == 1, hi_mod == 2, hi_mod == 3, hi_mod == 4, hi_mod == 5],
            [p, p, t_val, b_l, b_l, q],
        )
    result = np.where(
        np.repeat((b_s < 1e-8)[:, :, np.newaxis], 3, axis=2),
        b_l[:, :, np.newaxis],
        np.where(
            np.repeat((hi_mod == 0)[:, :, np.newaxis], 3, axis=2), out,
            np.where(
                np.repeat((hi_mod == 1)[:, :, np.newaxis], 3, axis=2), out2,
                out3
            )
        )
    )
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_saturation(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'saturation')
    if gpu is not None:
        return gpu
    l_b = bottom.min(axis=2)
    h_b = bottom.max(axis=2)
    l_t = top.min(axis=2)
    h_t = top.max(axis=2)
    c_b = h_b - l_b
    c_t = h_t - l_t
    l = h_b
    s_ratio = np.divide(c_t, l + 1e-8, out=np.zeros_like(c_t), where=l > 1e-8)
    s_new = c_b * np.where(l > 1e-8, 1.0, 0.0)
    result = np.zeros_like(bottom)
    for ci in range(3):
        result[..., ci] = bottom[..., ci]
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_color(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'color')
    if gpu is not None:
        return gpu
    l_b = bottom.min(axis=2)
    h_b = bottom.max(axis=2)
    l_t = top.min(axis=2)
    h_t = top.max(axis=2)
    l = h_b
    c = h_t - l_t
    s = np.divide(c, h_t + 1e-8, out=np.zeros_like(c), where=h_t > 1e-8)
    result = np.zeros_like(bottom)
    for ci in range(3):
        result[..., ci] = bottom[..., ci]
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


def blend_luminosity(bottom, top, opacity=1.0):
    gpu = _try_gpu(bottom, top, 'luminosity')
    if gpu is not None:
        return gpu
    b_lum = 0.299 * bottom[..., 0] + 0.587 * bottom[..., 1] + 0.114 * bottom[..., 2]
    t_lum = 0.299 * top[..., 0] + 0.587 * top[..., 1] + 0.114 * top[..., 2]
    ratio = np.divide(t_lum, b_lum + 1e-8, out=np.ones_like(t_lum), where=b_lum > 1e-8)
    result = bottom * ratio[:, :, np.newaxis]
    result = np.clip(result, 0.0, 1.0)
    if opacity < 1.0:
        result = bottom * (1.0 - opacity) + result * opacity
    return result


BLEND_FUNCTIONS = {
    "Normal": blend_normal,
    "Multiply": blend_multiply,
    "Screen": blend_screen,
    "Overlay": blend_overlay,
    "Darken": blend_darken,
    "Lighten": blend_lighten,
    "Color Dodge": blend_color_dodge,
    "Color Burn": blend_color_burn,
    "Hard Light": blend_hard_light,
    "Soft Light": blend_soft_light,
    "Difference": blend_difference,
    "Exclusion": blend_exclusion,
    "Add": blend_add,
    "Subtract": blend_subtract,
    "Hue": blend_hue,
    "Saturation": blend_saturation,
    "Color": blend_color,
    "Luminosity": blend_luminosity,
}

BLEND_MODES = list(BLEND_FUNCTIONS.keys())
