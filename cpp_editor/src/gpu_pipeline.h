#ifndef GPU_PIPELINE_H
#define GPU_PIPELINE_H

#include "gpu_ops.h"
#include <cstring>
#include <vector>

class GPUPipeline {
public:
    static GPUPipeline& instance() {
        static GPUPipeline inst;
        return inst;
    }
    
    bool init() { return m_ops.init(); }
    bool available() const { return m_ops.isAvailable(); }
    
    bool applyBlend(unsigned char* bottom, unsigned char* top,
                    int w, int h, int mode, float opacity) {
        if (!m_ops.isAvailable()) return false;
        
        auto b_float = GPUOps::imageToFloats(bottom, w, h);
        auto t_float = GPUOps::imageToFloats(top, w, h);
        
        GPUOps::ImageData b_data{b_float, w, h};
        GPUOps::ImageData t_data{t_float, w, h};
        
        auto result = m_ops.blend(b_data, t_data, mode, opacity);
        auto bytes = GPUOps::floatsToBytes(result.pixels);
        
        std::memcpy(bottom, bytes.data(), bytes.size());
        return true;
    }
    
    bool applyFilter(unsigned char* data, int w, int h,
                     int filter_type, float param0) {
        if (!m_ops.isAvailable()) return false;
        
        auto in_float = GPUOps::imageToFloats(data, w, h);
        GPUOps::ImageData in_data{in_float, w, h};
        
        auto result = m_ops.filter(in_data, filter_type, param0);
        auto bytes = GPUOps::floatsToBytes(result.pixels);
        
        std::memcpy(data, bytes.data(), bytes.size());
        return true;
    }

private:
    GPUPipeline() {}
    GPUOps m_ops;
};

#endif
