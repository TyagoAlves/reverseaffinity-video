#include "simd_ops.h"
#include <cstdint>
#include <algorithm>
#include <cstring>

#ifdef __SSE2__
#include <emmintrin.h>
#endif

namespace simd {

namespace {

inline uint8_t clamp_u8(int v) {
    return static_cast<uint8_t>(std::max(0, std::min(255, v)));
}

// Division by 255 with rounding: ((x + 128) * 257) >> 16
// Works for x in [0, 65025]
inline uint8_t div255_round(int x) {
    return static_cast<uint8_t>(((x + 128) * 257) >> 16);
}

} // anonymous namespace

// ---- Scalar fallback implementations ----

static void blend_normal_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        int a_src = src[si + 3];
        if (a_src == 255) {
            std::memcpy(dst + si, src + si, 4);
        } else if (a_src > 0) {
            int a_dst = dst[si + 3];
            int out_a = a_src + a_dst * (255 - a_src) / 255;
            if (out_a > 0) {
                dst[si + 0] = clamp_u8((src[si + 0] * a_src + dst[si + 0] * a_dst * (255 - a_src) / 255) / out_a);
                dst[si + 1] = clamp_u8((src[si + 1] * a_src + dst[si + 1] * a_dst * (255 - a_src) / 255) / out_a);
                dst[si + 2] = clamp_u8((src[si + 2] * a_src + dst[si + 2] * a_dst * (255 - a_src) / 255) / out_a);
            }
            dst[si + 3] = static_cast<uint8_t>(out_a);
        }
    }
}

static void blend_multiply_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        dst[si + 0] = div255_round(src[si + 0] * dst[si + 0]);
        dst[si + 1] = div255_round(src[si + 1] * dst[si + 1]);
        dst[si + 2] = div255_round(src[si + 2] * dst[si + 2]);
    }
}

static void blend_screen_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        dst[si + 0] = 255 - div255_round((255 - src[si + 0]) * (255 - dst[si + 0]));
        dst[si + 1] = 255 - div255_round((255 - src[si + 1]) * (255 - dst[si + 1]));
        dst[si + 2] = 255 - div255_round((255 - src[si + 2]) * (255 - dst[si + 2]));
    }
}

static void blend_overlay_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        for (int c = 0; c < 3; ++c) {
            int s = src[si + c], d = dst[si + c];
            dst[si + c] = (d < 128) ? div255_round(2 * s * d) : 255 - div255_round(2 * (255 - s) * (255 - d));
        }
    }
}

static void blend_darken_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        dst[si + 0] = std::min(src[si + 0], dst[si + 0]);
        dst[si + 1] = std::min(src[si + 1], dst[si + 1]);
        dst[si + 2] = std::min(src[si + 2], dst[si + 2]);
    }
}

static void blend_lighten_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        dst[si + 0] = std::max(src[si + 0], dst[si + 0]);
        dst[si + 1] = std::max(src[si + 1], dst[si + 1]);
        dst[si + 2] = std::max(src[si + 2], dst[si + 2]);
    }
}

static void blend_difference_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        dst[si + 0] = abs(src[si + 0] - dst[si + 0]);
        dst[si + 1] = abs(src[si + 1] - dst[si + 1]);
        dst[si + 2] = abs(src[si + 2] - dst[si + 2]);
    }
}

static void blend_add_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        dst[si + 0] = std::min(255, src[si + 0] + dst[si + 0]);
        dst[si + 1] = std::min(255, src[si + 1] + dst[si + 1]);
        dst[si + 2] = std::min(255, src[si + 2] + dst[si + 2]);
    }
}

static void blend_subtract_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        dst[si + 0] = std::max(0, dst[si + 0] - src[si + 0]);
        dst[si + 1] = std::max(0, dst[si + 1] - src[si + 1]);
        dst[si + 2] = std::max(0, dst[si + 2] - src[si + 2]);
    }
}

static void blend_color_dodge_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        for (int c = 0; c < 3; ++c) {
            int s = src[si + c], d = dst[si + c];
            dst[si + c] = (s < 255) ? std::min(255, (d * 255) / (255 - s)) : 255;
        }
    }
}

static void blend_color_burn_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        for (int c = 0; c < 3; ++c) {
            int s = src[si + c], d = dst[si + c];
            dst[si + c] = (s > 0) ? 255 - std::min(255, (255 - d) * 255 / s) : 0;
        }
    }
}

static void blend_soft_light_scalar(const uint8_t* src, uint8_t* dst, int pixels) {
    for (int i = 0; i < pixels; ++i) {
        int si = i * 4;
        for (int c = 0; c < 3; ++c) {
            int s = src[si + c], d = dst[si + c];
            if (s < 128) {
                dst[si + c] = d - div255_round((255 - 2 * s) * d * (255 - d));
            } else {
                int sqrt_d = static_cast<int>(std::sqrt(d * 256.0)) * 16;
                dst[si + c] = d + div255_round((2 * s - 255) * (sqrt_d - d));
            }
        }
    }
}

static void grayscale_scalar(uint8_t* pixels, int count) {
    for (int i = 0; i < count; ++i) {
        int si = i * 4;
        int g = (77 * pixels[si + 0] + 150 * pixels[si + 1] + 29 * pixels[si + 2] + 128) >> 8;
        uint8_t gray = static_cast<uint8_t>(std::min(255, g));
        pixels[si + 0] = gray;
        pixels[si + 1] = gray;
        pixels[si + 2] = gray;
    }
}

static void brightness_scalar(uint8_t* pixels, int count, int delta) {
    for (int i = 0; i < count; ++i) {
        int si = i * 4;
        pixels[si + 0] = clamp_u8(pixels[si + 0] + delta);
        pixels[si + 1] = clamp_u8(pixels[si + 1] + delta);
        pixels[si + 2] = clamp_u8(pixels[si + 2] + delta);
    }
}

static void invert_scalar(uint8_t* pixels, int count) {
    for (int i = 0; i < count; ++i) {
        int si = i * 4;
        pixels[si + 0] = 255 - pixels[si + 0];
        pixels[si + 1] = 255 - pixels[si + 1];
        pixels[si + 2] = 255 - pixels[si + 2];
    }
}

static void composite_over_scalar(const uint8_t* src, uint8_t* dst, int count, float opacity) {
    int op = static_cast<int>(opacity * 255);
    for (int i = 0; i < count; ++i) {
        int si = i * 4;
        int sa = (src[si + 3] * op) / 255;
        if (sa == 0) continue;
        int da = dst[si + 3];
        int out_a = sa + da * (255 - sa) / 255;
        if (out_a > 0) {
            dst[si + 0] = clamp_u8((src[si + 0] * sa + dst[si + 0] * da * (255 - sa) / 255) / out_a);
            dst[si + 1] = clamp_u8((src[si + 1] * sa + dst[si + 1] * da * (255 - sa) / 255) / out_a);
            dst[si + 2] = clamp_u8((src[si + 2] * sa + dst[si + 2] * da * (255 - sa) / 255) / out_a);
        }
        dst[si + 3] = static_cast<uint8_t>(out_a);
    }
}

// ---- Public API ----

void blend_normal(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_normal_scalar(src, dst, pixels);
}

void blend_multiply(const uint8_t* src, uint8_t* dst, int pixels) {
#ifdef __SSE2__
    int i = 0;
    const __m128i k257 = _mm_set1_epi16(257);
    const __m128i k128 = _mm_set1_epi16(128);
    for (; i + 4 <= pixels; i += 4) {
        int si = i * 4;
        __m128i s = _mm_loadu_si128(reinterpret_cast<const __m128i*>(src + si));
        __m128i d = _mm_loadu_si128(reinterpret_cast<const __m128i*>(dst + si));

        __m128i s_lo = _mm_unpacklo_epi8(s, _mm_setzero_si128());
        __m128i s_hi = _mm_unpackhi_epi8(s, _mm_setzero_si128());
        __m128i d_lo = _mm_unpacklo_epi8(d, _mm_setzero_si128());
        __m128i d_hi = _mm_unpackhi_epi8(d, _mm_setzero_si128());

        __m128i r_lo = _mm_mullo_epi16(s_lo, d_lo);
        __m128i r_hi = _mm_mullo_epi16(s_hi, d_hi);

        // Divide by 255 with rounding: ((x + 128) * 257) >> 16
        __m128i t_lo = _mm_add_epi16(r_lo, k128);
        __m128i t_hi = _mm_add_epi16(r_hi, k128);
        __m128i div_lo = _mm_mulhi_epu16(t_lo, k257);
        __m128i div_hi = _mm_mulhi_epu16(t_hi, k257);

        // Preserve destination alpha
        __m128i result = _mm_packus_epi16(div_lo, div_hi);
        __m128i alpha_mask = _mm_set1_epi32(0xFF000000);
        result = _mm_or_si128(_mm_and_si128(result, _mm_set1_epi32(0x00FFFFFF)),
                              _mm_and_si128(d, alpha_mask));

        _mm_storeu_si128(reinterpret_cast<__m128i*>(dst + si), result);
    }
    blend_multiply_scalar(src, dst + i * 4, pixels - i);
#else
    blend_multiply_scalar(src, dst, pixels);
#endif
}

void blend_screen(const uint8_t* src, uint8_t* dst, int pixels) {
#ifdef __SSE2__
    int i = 0;
    const __m128i k255 = _mm_set1_epi16(255);
    const __m128i k257 = _mm_set1_epi16(257);
    const __m128i k128 = _mm_set1_epi16(128);
    for (; i + 4 <= pixels; i += 4) {
        int si = i * 4;
        __m128i s = _mm_loadu_si128(reinterpret_cast<const __m128i*>(src + si));
        __m128i d = _mm_loadu_si128(reinterpret_cast<const __m128i*>(dst + si));

        __m128i s_lo = _mm_unpacklo_epi8(s, _mm_setzero_si128());
        __m128i s_hi = _mm_unpackhi_epi8(s, _mm_setzero_si128());
        __m128i d_lo = _mm_unpacklo_epi8(d, _mm_setzero_si128());
        __m128i d_hi = _mm_unpackhi_epi8(d, _mm_setzero_si128());

        __m128i inv_s_lo = _mm_sub_epi16(k255, s_lo);
        __m128i inv_s_hi = _mm_sub_epi16(k255, s_hi);
        __m128i inv_d_lo = _mm_sub_epi16(k255, d_lo);
        __m128i inv_d_hi = _mm_sub_epi16(k255, d_hi);

        __m128i prod_lo = _mm_mullo_epi16(inv_s_lo, inv_d_lo);
        __m128i prod_hi = _mm_mullo_epi16(inv_s_hi, inv_d_hi);

        // Divide by 255 with rounding
        __m128i t_lo = _mm_add_epi16(prod_lo, k128);
        __m128i t_hi = _mm_add_epi16(prod_hi, k128);
        __m128i div_lo = _mm_mulhi_epu16(t_lo, k257);
        __m128i div_hi = _mm_mulhi_epu16(t_hi, k257);

        __m128i r_lo = _mm_sub_epi16(k255, div_lo);
        __m128i r_hi = _mm_sub_epi16(k255, div_hi);

        __m128i result = _mm_packus_epi16(r_lo, r_hi);
        __m128i alpha_mask = _mm_set1_epi32(0xFF000000);
        result = _mm_or_si128(_mm_and_si128(result, _mm_set1_epi32(0x00FFFFFF)),
                              _mm_and_si128(d, alpha_mask));

        _mm_storeu_si128(reinterpret_cast<__m128i*>(dst + si), result);
    }
    blend_screen_scalar(src, dst + i * 4, pixels - i);
#else
    blend_screen_scalar(src, dst, pixels);
#endif
}

void blend_overlay(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_overlay_scalar(src, dst, pixels);
}

void blend_darken(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_darken_scalar(src, dst, pixels);
}

void blend_lighten(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_lighten_scalar(src, dst, pixels);
}

void blend_difference(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_difference_scalar(src, dst, pixels);
}

void blend_add(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_add_scalar(src, dst, pixels);
}

void blend_subtract(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_subtract_scalar(src, dst, pixels);
}

void blend_color_dodge(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_color_dodge_scalar(src, dst, pixels);
}

void blend_color_burn(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_color_burn_scalar(src, dst, pixels);
}

void blend_soft_light(const uint8_t* src, uint8_t* dst, int pixels) {
    blend_soft_light_scalar(src, dst, pixels);
}

void grayscale(uint8_t* pixels, int count) {
#ifdef __SSE2__
    int i = 0;
    // Luminance weights: gray = (R*77 + G*150 + B*29 + 128) >> 8
    // weights for _mm_madd_epi16: [77, 150, 29, 0] repeated
    const __m128i w = _mm_set_epi16(0, 29, 150, 77, 0, 29, 150, 77);
    const __m128i k128_32 = _mm_set1_epi32(128);
    const __m128i alpha_mask = _mm_set1_epi32(0xFF000000);

    for (; i + 4 <= count; i += 4) {
        int si = i * 4;
        __m128i px = _mm_loadu_si128(reinterpret_cast<const __m128i*>(pixels + si));
        __m128i alpha = _mm_and_si128(px, alpha_mask);

        // Expand to 16-bit
        __m128i lo = _mm_unpacklo_epi8(px, _mm_setzero_si128());
        __m128i hi = _mm_unpackhi_epi8(px, _mm_setzero_si128());

        // _mm_madd_epi16: [77*R0+150*G0, 29*B0+0, 77*R1+150*G1, 29*B1+0]
        __m128i m_lo = _mm_madd_epi16(lo, w);
        __m128i m_hi = _mm_madd_epi16(hi, w);

        // Sum adjacent pairs: total = 77*R + 150*G + 29*B
        // _MM_SHUFFLE(1,0,3,2) swaps pairs: [a,b,c,d] -> [b,a,d,c]
        __m128i s_lo = _mm_add_epi32(m_lo, _mm_shuffle_epi32(m_lo, _MM_SHUFFLE(1,0,3,2)));
        __m128i s_hi = _mm_add_epi32(m_hi, _mm_shuffle_epi32(m_hi, _MM_SHUFFLE(1,0,3,2)));

        // Add rounding (128) and shift right by 8 (divide by 256)
        // s_lo = [total0, total0, total1, total1] as 32-bit
        __m128i g32_lo = _mm_srli_epi32(_mm_add_epi32(s_lo, k128_32), 8);
        __m128i g32_hi = _mm_srli_epi32(_mm_add_epi32(s_hi, k128_32), 8);

        // g32_lo = [g0, g0, g1, g1], g32_hi = [g2, g2, g3, g3]
        // Extract to [g0, g1, g2, g3] as 32-bit lanes:
        // shuffle(g32_lo, 0x08) = _MM_SHUFFLE(0,0,2,0): [g0, g1, g0, g0]
        // shuffle(g32_hi, 0x80) = _MM_SHUFFLE(2,0,0,0): [g2, g2, g2, g3]
        __m128i gl = _mm_shuffle_epi32(g32_lo, 0x08);
        __m128i gh = _mm_shuffle_epi32(g32_hi, 0x80);

        // gl = [g0, g1, g0, g0], gh = [g2, g2, g2, g3]
        // Combine: take lanes 0,1 from gl, lanes 2,3 from gh
        const __m128i mask0 = _mm_setr_epi32(-1, -1, 0, 0);
        const __m128i mask1 = _mm_setr_epi32(0, 0, -1, -1);
        __m128i gray32 = _mm_or_si128(_mm_and_si128(gl, mask0), _mm_and_si128(gh, mask1));
        // gray32 = [g0, g1, g2, g3] as 32-bit, gray value in low byte of each lane

        // Replicate gray to R,G,B: [g,g,g,0] per lane
        __m128i gray_rgb = gray32;
        gray_rgb = _mm_or_si128(gray_rgb, _mm_slli_epi32(gray_rgb, 8));
        gray_rgb = _mm_or_si128(gray_rgb, _mm_slli_epi32(gray_rgb, 16));
        // gray_rgb = [g,g,g,0] per 32-bit lane (byte 0=R=g, 1=G=g, 2=B=g, 3=0)

        // Combine with original alpha
        __m128i result = _mm_or_si128(gray_rgb, alpha);
        _mm_storeu_si128(reinterpret_cast<__m128i*>(pixels + si), result);
    }
    grayscale_scalar(pixels + i * 4, count - i);
#else
    grayscale_scalar(pixels, count);
#endif
}

void brightness(uint8_t* pixels, int count, int delta) {
    brightness_scalar(pixels, count, delta);
}

void invert(uint8_t* pixels, int count) {
#ifdef __SSE2__
    int i = 0;
    const __m128i k255_16 = _mm_set1_epi16(255);
    const __m128i alpha_mask = _mm_set1_epi32(0xFF000000);
    for (; i + 4 <= count; i += 4) {
        int si = i * 4;
        __m128i px = _mm_loadu_si128(reinterpret_cast<const __m128i*>(pixels + si));

        __m128i lo = _mm_unpacklo_epi8(px, _mm_setzero_si128());
        __m128i hi = _mm_unpackhi_epi8(px, _mm_setzero_si128());

        __m128i inv_lo = _mm_sub_epi16(k255_16, lo);
        __m128i inv_hi = _mm_sub_epi16(k255_16, hi);

        __m128i result = _mm_packus_epi16(inv_lo, inv_hi);

        // Restore alpha channel
        result = _mm_or_si128(_mm_and_si128(result, _mm_set1_epi32(0x00FFFFFF)),
                              _mm_and_si128(px, alpha_mask));

        _mm_storeu_si128(reinterpret_cast<__m128i*>(pixels + si), result);
    }
    invert_scalar(pixels + i * 4, count - i);
#else
    invert_scalar(pixels, count);
#endif
}

void composite_over(const uint8_t* src, uint8_t* dst, int count, float opacity) {
    composite_over_scalar(src, dst, count, opacity);
}

} // namespace simd
