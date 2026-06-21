"""
GPU Acceleration Module for reverseaffinity.
Auto-detects available GPU (CUDA > OpenCL > CPU fallback).
Provides accelerated blend modes and filters.
"""

import numpy as np
from enum import Enum


class GpuBackend(Enum):
    CPU = 0
    CUDA = 1
    OPENCL = 2


class GPUAccel:
    """
    Singleton GPU accelerator. Detects best available backend.
    Usage:
        accel = GPUAccel.get_instance()
        result = accel.blend(bottom, top, mode)
        result = accel.filter_gaussian_blur(img, radius)
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.backend = GpuBackend.CPU
        self._detect_backend()
        self._init_backend()

    def _detect_backend(self):
        """Detect best available GPU backend."""
        try:
            import cupy as cp
            self._cupy = cp
            test = cp.array([1, 2, 3])
            del test
            self.backend = GpuBackend.CUDA
            print("[GPU] CUDA backend detected via CuPy")
            return
        except ImportError:
            pass
        except Exception:
            pass

        try:
            import pyopencl as cl
            platforms = cl.get_platforms()
            if platforms:
                for plat in platforms:
                    devices = plat.get_devices(device_type=cl.device_type.GPU)
                    if devices:
                        self._cl_ctx = cl.Context([devices[0]])
                        self._cl_queue = cl.CommandQueue(self._cl_ctx)
                        self._cl_mf = cl.mem_flags
                        self.backend = GpuBackend.OPENCL
                        print(f"[GPU] OpenCL backend: {devices[0].name}")
                        return
        except ImportError:
            pass
        except Exception:
            pass

        print("[GPU] No GPU backend found, using CPU (NumPy)")

    def _init_backend(self):
        """Initialize backend-specific resources."""
        if self.backend == GpuBackend.CUDA:
            if not hasattr(self, '_cupy'):
                import cupy as cp
                self._cupy = cp
        elif self.backend == GpuBackend.OPENCL:
            self._build_opencl_kernels()

    def _build_opencl_kernels(self):
        """Build OpenCL kernels for blend modes."""
        import pyopencl as cl

        blend_kernel_source = """
        __kernel void blend_normal(__global const uchar4 *bottom,
                                    __global const uchar4 *top,
                                    __global uchar4 *output,
                                    const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + t.x * a) / out_a);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + t.y * a) / out_a);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + t.z * a) / out_a);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_multiply(__global const uchar4 *bottom,
                                      __global const uchar4 *top,
                                      __global uchar4 *output,
                                      const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended = b.xyz * t.xyz;
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_screen(__global const uchar4 *bottom,
                                    __global const uchar4 *top,
                                    __global uchar4 *output,
                                    const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended = 1.0f - (1.0f - b.xyz) * (1.0f - t.xyz);
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_overlay(__global const uchar4 *bottom,
                                     __global const uchar4 *top,
                                     __global uchar4 *output,
                                     const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended;
            blended.x = (b.x < 0.5f) ? (2.0f * b.x * t.x) : (1.0f - 2.0f * (1.0f - b.x) * (1.0f - t.x));
            blended.y = (b.y < 0.5f) ? (2.0f * b.y * t.y) : (1.0f - 2.0f * (1.0f - b.y) * (1.0f - t.y));
            blended.z = (b.z < 0.5f) ? (2.0f * b.z * t.z) : (1.0f - 2.0f * (1.0f - b.z) * (1.0f - t.z));
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_darken(__global const uchar4 *bottom,
                                    __global const uchar4 *top,
                                    __global uchar4 *output,
                                    const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended = fmin(b.xyz, t.xyz);
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_lighten(__global const uchar4 *bottom,
                                     __global const uchar4 *top,
                                     __global uchar4 *output,
                                     const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended = fmax(b.xyz, t.xyz);
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_difference(__global const uchar4 *bottom,
                                        __global const uchar4 *top,
                                        __global uchar4 *output,
                                        const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended = fabs(b.xyz - t.xyz);
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_add(__global const uchar4 *bottom,
                                 __global const uchar4 *top,
                                 __global uchar4 *output,
                                 const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended = fmin(b.xyz + t.xyz, 1.0f);
            float out_a = fmin(b.w * (1.0f - a) + a, 1.0f);
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_subtract(__global const uchar4 *bottom,
                                      __global const uchar4 *top,
                                      __global uchar4 *output,
                                      const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended = fmax(b.xyz - t.xyz, 0.0f);
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_color_dodge(__global const uchar4 *bottom,
                                         __global const uchar4 *top,
                                         __global uchar4 *output,
                                         const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended;
            blended.x = (t.x < 1.0f) ? fmin(b.x / (1.0f - t.x), 1.0f) : 1.0f;
            blended.y = (t.y < 1.0f) ? fmin(b.y / (1.0f - t.y), 1.0f) : 1.0f;
            blended.z = (t.z < 1.0f) ? fmin(b.z / (1.0f - t.z), 1.0f) : 1.0f;
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_color_burn(__global const uchar4 *bottom,
                                        __global const uchar4 *top,
                                        __global uchar4 *output,
                                        const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended;
            blended.x = (t.x > 0.0f) ? (1.0f - fmin((1.0f - b.x) / t.x, 1.0f)) : 0.0f;
            blended.y = (t.y > 0.0f) ? (1.0f - fmin((1.0f - b.y) / t.y, 1.0f)) : 0.0f;
            blended.z = (t.z > 0.0f) ? (1.0f - fmin((1.0f - b.z) / t.z, 1.0f)) : 0.0f;
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }

        __kernel void blend_soft_light(__global const uchar4 *bottom,
                                        __global const uchar4 *top,
                                        __global uchar4 *output,
                                        const float opacity) {
            int i = get_global_id(0);
            float4 b = convert_float4(bottom[i]) / 255.0f;
            float4 t = convert_float4(top[i]) / 255.0f;
            float a = t.w * opacity;
            float3 blended;
            blended.x = (t.x < 0.5f) ?
                (b.x - (1.0f - 2.0f * t.x) * b.x * (1.0f - b.x)) :
                (b.x + (2.0f * t.x - 1.0f) * (sqrt(b.x) - b.x));
            blended.y = (t.y < 0.5f) ?
                (b.y - (1.0f - 2.0f * t.y) * b.y * (1.0f - b.y)) :
                (b.y + (2.0f * t.y - 1.0f) * (sqrt(b.y) - b.y));
            blended.z = (t.z < 0.5f) ?
                (b.z - (1.0f - 2.0f * t.z) * b.z * (1.0f - b.z)) :
                (b.z + (2.0f * t.z - 1.0f) * (sqrt(b.z) - b.z));
            float out_a = b.w * (1.0f - a) + a;
            if (out_a > 0.0f) {
                output[i].x = (uchar)((b.x * b.w * (1.0f - a) + blended.x * a) / out_a * 255.0f);
                output[i].y = (uchar)((b.y * b.w * (1.0f - a) + blended.y * a) / out_a * 255.0f);
                output[i].z = (uchar)((b.z * b.w * (1.0f - a) + blended.z * a) / out_a * 255.0f);
            }
            output[i].w = (uchar)(out_a * 255.0f);
        }
        """

        self._cl_prg = cl.Program(self._cl_ctx, blend_kernel_source).build()

    def _to_gpu(self, img_np):
        """Transfer numpy array to GPU memory."""
        if self.backend == GpuBackend.CUDA:
            return self._cupy.asarray(img_np)
        elif self.backend == GpuBackend.OPENCL:
            import pyopencl as cl
            if img_np.dtype != np.uint8 or img_np.ndim != 3 or img_np.shape[2] != 4:
                if img_np.ndim == 2:
                    img_np = np.stack([img_np] * 3 + [np.ones_like(img_np) * 255], axis=2)
                elif img_np.shape[2] == 3:
                    alpha = np.full((img_np.shape[0], img_np.shape[1], 1), 255, dtype=np.uint8)
                    img_np = np.concatenate([img_np, alpha], axis=2)
                img_np = img_np.astype(np.uint8)
            buf = cl.Buffer(
                self._cl_ctx,
                self._cl_mf.READ_ONLY | self._cl_mf.COPY_HOST_PTR,
                hostbuf=np.ascontiguousarray(img_np),
            )
            return buf, img_np.shape
        return img_np

    def _from_gpu(self, gpu_data, shape=None):
        """Transfer GPU memory back to numpy array."""
        if self.backend == GpuBackend.CUDA:
            return self._cupy.asnumpy(gpu_data)
        elif self.backend == GpuBackend.OPENCL:
            import pyopencl as cl
            buf, s = gpu_data
            result = np.empty(s, dtype=np.uint8)
            cl.enqueue_copy(self._cl_queue, result, buf)
            return result
        return gpu_data

    def blend(self, bottom_np, top_np, mode, opacity=1.0):
        """
        GPU-accelerated blend mode.
        Accepts uint8 or float32 arrays, 3 or 4 channels.
        Returns same dtype and channel count as input.
        """
        if self.backend == GpuBackend.CPU:
            return self._blend_cpu(bottom_np, top_np, mode, opacity)

        # Normalize to uint8 RGBA for GPU processing
        orig_dtype = bottom_np.dtype
        orig_has_alpha = bottom_np.ndim == 3 and bottom_np.shape[2] == 4
        is_float = orig_dtype in (np.float32, np.float64)

        b = self._ensure_uint8_rgba(bottom_np)
        t = self._ensure_uint8_rgba(top_np)

        result = self._blend_gpu(b, t, mode, opacity)

        return self._restore_format(result, is_float, orig_has_alpha)

    def _ensure_uint8_rgba(self, arr):
        """Convert any array to uint8 HxWx4."""
        if arr.dtype in (np.float32, np.float64):
            arr = np.clip(arr * 255, 0, 255).astype(np.uint8)
        if arr.ndim == 2:
            arr = np.stack([arr] * 3 + [np.ones_like(arr) * 255], axis=2)
        elif arr.shape[2] == 3:
            alpha = np.full((*arr.shape[:2], 1), 255, dtype=np.uint8)
            arr = np.concatenate([arr, alpha], axis=2)
        return np.ascontiguousarray(arr)

    def _restore_format(self, arr, was_float, had_alpha):
        """Convert uint8 RGBA back to original format."""
        if was_float:
            if had_alpha:
                return arr.astype(np.float32) / 255.0
            else:
                return arr[:, :, :3].astype(np.float32) / 255.0
        if had_alpha:
            return arr
        return arr[:, :, :3]

    def _blend_cpu(self, bottom_np, top_np, mode, opacity):
        """Simple CPU fallback — copies top with alpha composite."""
        is_float = bottom_np.dtype in (np.float32, np.float64)
        if not is_float:
            b = bottom_np.astype(np.float32) / 255.0
            t = top_np.astype(np.float32) / 255.0
        else:
            b = bottom_np
            t = top_np

        if b.ndim == 3 and b.shape[2] >= 4:
            b_alpha = b[:, :, 3:4]
            t_alpha = t[:, :, 3:4] * opacity
        else:
            b_alpha = np.ones((b.shape[0], b.shape[1], 1), dtype=b.dtype)
            t_alpha = np.ones((t.shape[0], t.shape[1], 1), dtype=b.dtype) * opacity

        out_a = b_alpha * (1.0 - t_alpha) + t_alpha
        mask = out_a > 0

        result = np.zeros_like(b)
        for c in range(min(3, b.shape[2])):
            result[:, :, c] = np.where(
                mask[:, :, 0],
                (b[:, :, c] * b_alpha[:, :, 0] * (1.0 - t_alpha[:, :, 0]) +
                 t[:, :, c] * t_alpha[:, :, 0]) / out_a[:, :, 0],
                0,
            )

        if b.shape[2] >= 4:
            result[:, :, 3] = out_a[:, :, 0]
        else:
            result = result[:, :, :3]

        if not is_float:
            result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return result

    def _blend_gpu(self, bottom_np, top_np, mode, opacity):
        """GPU blend mode implementation."""
        if self.backend == GpuBackend.CUDA:
            return self._blend_cuda(bottom_np, top_np, mode, opacity)
        elif self.backend == GpuBackend.OPENCL:
            return self._blend_opencl(bottom_np, top_np, mode, opacity)
        return bottom_np

    def _blend_cuda(self, bottom_np, top_np, mode, opacity):
        """CUDA blend using CuPy."""
        cp = self._cupy
        b = cp.asarray(bottom_np, dtype=cp.float32) / 255.0
        t = cp.asarray(top_np, dtype=cp.float32) / 255.0

        mode_lower = mode.lower().replace('_', ' ')

        if mode_lower == 'normal':
            blended = t
        elif mode_lower == 'multiply':
            blended = b * t
        elif mode_lower == 'screen':
            blended = 1.0 - (1.0 - b) * (1.0 - t)
        elif mode_lower == 'overlay':
            blended = cp.where(b < 0.5, 2 * b * t, 1 - 2 * (1 - b) * (1 - t))
        elif mode_lower == 'darken':
            blended = cp.minimum(b, t)
        elif mode_lower == 'lighten':
            blended = cp.maximum(b, t)
        elif mode_lower == 'difference':
            blended = cp.abs(b - t)
        elif mode_lower == 'add':
            blended = cp.clip(b + t, 0, 1)
        elif mode_lower == 'subtract':
            blended = cp.clip(b - t, 0, 1)
        elif mode_lower in ('dodge', 'color dodge'):
            blended = cp.where(t < 1, cp.clip(b / (1 - t), 0, 1), 1.0)
        elif mode_lower in ('burn', 'color burn'):
            blended = cp.where(t > 0, 1 - cp.clip((1 - b) / t, 0, 1), 0.0)
        elif mode_lower in ('soft light', 'softlight'):
            blended = cp.where(
                t < 0.5,
                b - (1 - 2 * t) * b * (1 - b),
                b + (2 * t - 1) * (cp.sqrt(b) - b),
            )
        elif mode_lower == 'hard light':
            blended = cp.where(t < 0.5, 2 * b * t, 1 - 2 * (1 - b) * (1 - t))
        elif mode_lower == 'exclusion':
            blended = b + t - 2 * b * t
        else:
            blended = t

        a = opacity
        top_alpha = t[:, :, 3:4]
        bot_alpha = b[:, :, 3:4]
        out_a = bot_alpha * (1 - a * top_alpha) + a * top_alpha
        out_a = cp.clip(out_a, 0, 1)
        mask = out_a > 0

        result = cp.zeros_like(b)
        for c in range(3):
            result[:, :, c] = cp.where(
                mask[:, :, 0],
                (b[:, :, c] * bot_alpha[:, :, 0] * (1 - a * top_alpha[:, :, 0]) +
                 blended[:, :, c] * a * top_alpha[:, :, 0]) / out_a[:, :, 0],
                0,
            )
        result[:, :, 3] = out_a[:, :, 0]

        return cp.clip(result * 255, 0, 255).astype(cp.uint8).get()

    def _blend_opencl(self, bottom_np, top_np, mode, opacity):
        """OpenCL blend using PyOpenCL."""
        import pyopencl as cl
        h, w = bottom_np.shape[:2]

        bottom_np = np.ascontiguousarray(bottom_np, dtype=np.uint8)
        top_np = np.ascontiguousarray(top_np, dtype=np.uint8)

        mf = self._cl_mf
        b_buf = cl.Buffer(self._cl_ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=bottom_np)
        t_buf = cl.Buffer(self._cl_ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=top_np)
        out_buf = cl.Buffer(self._cl_ctx, mf.WRITE_ONLY, bottom_np.nbytes)

        kernel_map = {
            'normal': 'blend_normal',
            'multiply': 'blend_multiply',
            'screen': 'blend_screen',
            'overlay': 'blend_overlay',
            'darken': 'blend_darken',
            'lighten': 'blend_lighten',
            'difference': 'blend_difference',
            'add': 'blend_add',
            'subtract': 'blend_subtract',
            'dodge': 'blend_color_dodge',
            'color dodge': 'blend_color_dodge',
            'burn': 'blend_color_burn',
            'color burn': 'blend_color_burn',
            'soft light': 'blend_soft_light',
            'softlight': 'blend_soft_light',
        }

        kn = kernel_map.get(mode.lower().replace('_', ' '), 'blend_normal')

        try:
            kernel = getattr(self._cl_prg, kn)
            kernel(self._cl_queue, (h * w,), None, b_buf, t_buf, out_buf, np.float32(opacity))
            result = np.empty_like(bottom_np)
            cl.enqueue_copy(self._cl_queue, result, out_buf)
            return result
        except Exception as e:
            print(f"[GPU] OpenCL blend error: {e}, falling back to CPU")
            return self._blend_cpu(bottom_np, top_np, mode, opacity)

    def filter_gaussian_blur(self, img_np, radius):
        """Gaussian blur (uses scipy, CPU-only fallback)."""
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(img_np, sigma=radius, mode='reflect')

    def filter_sharpen(self, img_np, amount):
        """Sharpen image."""
        from scipy.ndimage import gaussian_filter
        blurred = gaussian_filter(img_np, sigma=1.0, mode='reflect')
        sharpened = img_np.astype(np.float32) + amount * (img_np.astype(np.float32) - blurred)
        return np.clip(sharpened, 0, 255).astype(np.uint8)

    def filter_edge_detect(self, img_np):
        """Edge detection using Sobel operator."""
        from scipy.ndimage import sobel
        gray = np.mean(img_np[:, :, :3], axis=2)
        edges = np.sqrt(sobel(gray, axis=0) ** 2 + sobel(gray, axis=1) ** 2)
        edges = np.clip(edges * 4, 0, 255).astype(np.uint8)
        result = np.stack([edges, edges, edges, img_np[:, :, 3]], axis=2)
        return result

    @property
    def is_active(self):
        return self.backend != GpuBackend.CPU

    @property
    def backend_name(self):
        return self.backend.name
