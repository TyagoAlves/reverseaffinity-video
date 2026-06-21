#ifndef SIMD_OPS_H
#define SIMD_OPS_H

#include <cstdint>

namespace simd {

void blend_normal(const uint8_t* src, uint8_t* dst, int pixels);
void blend_multiply(const uint8_t* src, uint8_t* dst, int pixels);
void blend_screen(const uint8_t* src, uint8_t* dst, int pixels);
void blend_overlay(const uint8_t* src, uint8_t* dst, int pixels);
void blend_darken(const uint8_t* src, uint8_t* dst, int pixels);
void blend_lighten(const uint8_t* src, uint8_t* dst, int pixels);
void blend_difference(const uint8_t* src, uint8_t* dst, int pixels);
void blend_add(const uint8_t* src, uint8_t* dst, int pixels);
void blend_subtract(const uint8_t* src, uint8_t* dst, int pixels);
void blend_color_dodge(const uint8_t* src, uint8_t* dst, int pixels);
void blend_color_burn(const uint8_t* src, uint8_t* dst, int pixels);
void blend_soft_light(const uint8_t* src, uint8_t* dst, int pixels);
void grayscale(uint8_t* pixels, int count);
void brightness(uint8_t* pixels, int count, int delta);
void invert(uint8_t* pixels, int count);
void composite_over(const uint8_t* src, uint8_t* dst, int count, float opacity);

} // namespace simd

#endif
