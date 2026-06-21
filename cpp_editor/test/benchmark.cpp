#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <chrono>
#include <cstring>
#include <simd_ops.h>

static double now_ms() {
    using clock = std::chrono::high_resolution_clock;
    return std::chrono::duration<double, std::milli>(
        clock::now().time_since_epoch()).count();
}

static uint8_t* alloc_4k_image() {
    uint8_t* buf = new uint8_t[3840 * 2160 * 4];
    for (int i = 0; i < 3840 * 2160; ++i) {
        int idx = i * 4;
        buf[idx + 0] = static_cast<uint8_t>(rand() & 0xFF);
        buf[idx + 1] = static_cast<uint8_t>(rand() & 0xFF);
        buf[idx + 2] = static_cast<uint8_t>(rand() & 0xFF);
        buf[idx + 3] = 255;
    }
    return buf;
}

static void run_benchmark(const char* name, void (*func)(), int iterations) {
    double start = now_ms();
    for (int i = 0; i < iterations; ++i) {
        func();
    }
    double elapsed = now_ms() - start;
    printf("%-25s %6d iterations  %8.2f ms  %8.3f ms/iter\n",
           name, iterations, elapsed, elapsed / iterations);
}

int main() {
    printf("=== SIMD Performance Benchmarks (4K image: 3840x2160 = %d pixels) ===\n\n",
           3840 * 2160);

    int total_pixels = 3840 * 2160;

    uint8_t* src = alloc_4k_image();
    uint8_t* dst = alloc_4k_image();

    // Verify correctness
    uint8_t* dst_copy = new uint8_t[total_pixels * 4];
    std::memcpy(dst_copy, dst, total_pixels * 4);

    // Warm up
    simd::blend_multiply(src, dst, total_pixels);
    simd::blend_screen(src, dst_copy, total_pixels);

    int iterations = 5;

    printf("Blend Operations:\n");
    printf("-----------------------------------------------------------------\n");

    run_benchmark("blend_multiply", [&]() {
        std::memcpy(dst, dst_copy, total_pixels * 4);
        simd::blend_multiply(src, dst, total_pixels);
    }, 5);

    run_benchmark("blend_screen", [&]() {
        std::memcpy(dst, dst_copy, total_pixels * 4);
        simd::blend_screen(src, dst, total_pixels);
    }, 5);

    printf("\nPixel Operations:\n");
    printf("-----------------------------------------------------------------\n");

    // Make a copy for grayscale/invert tests
    uint8_t* work = new uint8_t[total_pixels * 4];
    std::memcpy(work, src, total_pixels * 4);

    run_benchmark("grayscale", [&]() {
        std::memcpy(work, src, total_pixels * 4);
        simd::grayscale(work, total_pixels);
    }, 5);

    run_benchmark("invert", [&]() {
        std::memcpy(work, src, total_pixels * 4);
        simd::invert(work, total_pixels);
    }, 5);

    run_benchmark("brightness (+50)", [&]() {
        std::memcpy(work, src, total_pixels * 4);
        simd::brightness(work, total_pixels, 50);
    }, 5);

    run_benchmark("composite_over (0.5)", [&]() {
        std::memcpy(dst, dst_copy, total_pixels * 4);
        simd::composite_over(src, dst, total_pixels, 0.5f);
    }, 5);

    printf("\nDone.\n");

    delete[] src;
    delete[] dst;
    delete[] dst_copy;
    delete[] work;

    return 0;
}
