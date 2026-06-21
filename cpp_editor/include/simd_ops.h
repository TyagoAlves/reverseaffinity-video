#ifndef SIMD_OPS_H
#define SIMD_OPS_H

#include <cstdint>

namespace simd {

void blend_normal(const uint8_t* src, uint8_t* dst, int pixels);
void blend_multiply(const uint8_t* src, uint8_t* dst, int pixels);
void blend_screen(const uint8_t* src, uint8_t* dst, int pixels);
void grayscale(uint8_t* pixels, int count);
void brightness(uint8_t* pixels, int count, int delta);
void invert(uint8_t* pixels, int count);
void composite_over(const uint8_t* src, uint8_t* dst, int count, float opacity);

} // namespace simd

#endif
