#ifndef GPU_OPS_H
#define GPU_OPS_H

#include <vector>
#include <string>
#include <cstring>
#include <cstdio>
#include <iostream>
#include <sstream>
#include <fstream>
#include <algorithm>

#ifdef __APPLE__
#include <OpenGL/gl3.h>
#else
#include <GL/gl.h>
#include <GL/glext.h>
#ifdef __linux__
#include <GL/glx.h>
#endif
#endif

static const char* BLEND_COMPUTE_SRC = R"glsl(
#version 430 core
layout(local_size_x = 16, local_size_y = 16) in;

layout(std430, binding = 0) buffer Bottom { vec4 bottom[]; };
layout(std430, binding = 1) buffer Top    { vec4 top[]; };
layout(std430, binding = 2) buffer Output { vec4 output_img[]; };

uniform int mode;
uniform float opacity;
uniform int img_w;
uniform int img_h;

vec4 blend_normal(vec4 b, vec4 t) { return t; }
vec4 blend_multiply(vec4 b, vec4 t) { return vec4(b.rgb * t.rgb, 1.0); }
vec4 blend_screen(vec4 b, vec4 t) { return vec4(1.0 - (1.0 - b.rgb) * (1.0 - t.rgb), 1.0); }
vec4 blend_overlay(vec4 b, vec4 t) {
    vec3 c;
    c.r = b.r < 0.5 ? 2.0 * b.r * t.r : 1.0 - 2.0 * (1.0 - b.r) * (1.0 - t.r);
    c.g = b.g < 0.5 ? 2.0 * b.g * t.g : 1.0 - 2.0 * (1.0 - b.g) * (1.0 - t.g);
    c.b = b.b < 0.5 ? 2.0 * b.b * t.b : 1.0 - 2.0 * (1.0 - b.b) * (1.0 - t.b);
    return vec4(c, 1.0);
}
vec4 blend_darken(vec4 b, vec4 t) { return vec4(min(b.rgb, t.rgb), 1.0); }
vec4 blend_lighten(vec4 b, vec4 t) { return vec4(max(b.rgb, t.rgb), 1.0); }
vec4 blend_difference(vec4 b, vec4 t) { return vec4(abs(b.rgb - t.rgb), 1.0); }
vec4 blend_add(vec4 b, vec4 t) { return vec4(min(b.rgb + t.rgb, vec3(1.0)), 1.0); }
vec4 blend_subtract(vec4 b, vec4 t) { return vec4(max(b.rgb - t.rgb, vec3(0.0)), 1.0); }
vec4 blend_dodge(vec4 b, vec4 t) { return vec4(min(b.rgb / max(1.0 - t.rgb, 0.001), vec3(1.0)), 1.0); }
vec4 blend_burn(vec4 b, vec4 t) { return vec4(1.0 - min((1.0 - b.rgb) / max(t.rgb, 0.001), vec3(1.0)), 1.0); }
vec4 blend_softlight(vec4 b, vec4 t) {
    vec3 c;
    c.r = t.r < 0.5 ? b.r - (1.0 - 2.0 * t.r) * b.r * (1.0 - b.r) : b.r + (2.0 * t.r - 1.0) * (sqrt(b.r) - b.r);
    c.g = t.g < 0.5 ? b.g - (1.0 - 2.0 * t.g) * b.g * (1.0 - b.g) : b.g + (2.0 * t.g - 1.0) * (sqrt(b.g) - b.g);
    c.b = t.b < 0.5 ? b.b - (1.0 - 2.0 * t.b) * b.b * (1.0 - b.b) : b.b + (2.0 * t.b - 1.0) * (sqrt(b.b) - b.b);
    return vec4(c, 1.0);
}

void main() {
    uint x = gl_GlobalInvocationID.x;
    uint y = gl_GlobalInvocationID.y;
    if (x >= img_w || y >= img_h) return;
    
    uint idx = y * img_w + x;
    vec4 b = bottom[idx];
    vec4 t = top[idx] * opacity;
    
    vec4 result;
    switch (mode) {
        case 1:  result = blend_multiply(b, t);  break;
        case 2:  result = blend_screen(b, t);    break;
        case 3:  result = blend_overlay(b, t);   break;
        case 4:  result = blend_darken(b, t);    break;
        case 5:  result = blend_lighten(b, t);   break;
        case 6:  result = blend_difference(b, t); break;
        case 7:  result = blend_add(b, t);       break;
        case 8:  result = blend_subtract(b, t);  break;
        case 9:  result = blend_dodge(b, t);     break;
        case 10: result = blend_burn(b, t);      break;
        case 11: result = blend_softlight(b, t); break;
        default: result = blend_normal(b, t);    break;
    }
    
    float out_a = b.a * (1.0 - t.a) + t.a;
    if (out_a > 0.0) {
        result.rgb = (b.rgb * b.a * (1.0 - t.a) + result.rgb * t.a) / out_a;
    }
    result.a = out_a;
    
    output_img[idx] = result;
}
)glsl";

static const char* FILTER_COMPUTE_SRC = R"glsl(
#version 430 core
layout(local_size_x = 16, local_size_y = 16) in;

layout(std430, binding = 0) buffer Input  { vec4 input_img[]; };
layout(std430, binding = 1) buffer Output { vec4 output_img[]; };

uniform int filter_type;
uniform float param0;
uniform float param1;
uniform int img_w;
uniform int img_h;

void main() {
    uint x = gl_GlobalInvocationID.x;
    uint y = gl_GlobalInvocationID.y;
    if (x >= img_w || y >= img_h) return;
    
    uint idx = y * img_w + x;
    vec4 c = input_img[idx];
    vec4 result = c;
    
    if (filter_type == 0) {
        vec4 sum = vec4(0.0);
        float total = 0.0;
        int r = int(param0);
        for (int dy = -r; dy <= r; dy++) {
            for (int dx = -r; dx <= r; dx++) {
                int sx = int(x) + dx;
                int sy = int(y) + dy;
                if (sx >= 0 && sx < img_w && sy >= 0 && sy < img_h) {
                    float weight = exp(-float(dx*dx + dy*dy) / (2.0 * param0 * param0));
                    sum += input_img[sy * img_w + sx] * weight;
                    total += weight;
                }
            }
        }
        result = sum / total;
    }
    else if (filter_type == 1) {
        vec4 sum = vec4(0.0);
        int kx[9] = int[9](-1,-1,-1, 0,0,0, 1,1,1);
        int ky[9] = int[9](-1,0,1, -1,0,1, -1,0,1);
        float kernel[9] = float[9](-1,-1,-1, -1,9,-1, -1,-1,-1);
        for (int i = 0; i < 9; i++) {
            int sx = int(x) + kx[i];
            int sy = int(y) + ky[i];
            if (sx >= 0 && sx < img_w && sy >= 0 && sy < img_h) {
                sum += input_img[sy * img_w + sx] * kernel[i];
            } else {
                sum += c * kernel[i];
            }
        }
        result = mix(c, clamp(sum, 0.0, 1.0), param0);
    }
    else if (filter_type == 2) {
        vec4 gx = vec4(0.0), gy = vec4(0.0);
        int sx[9] = int[9](-1,-1,-1, 0,0,0, 1,1,1);
        int sy[9] = int[9](-1,0,1, -1,0,1, -1,0,1);
        float kx[9] = float[9](-1,0,1, -2,0,2, -1,0,1);
        float ky[9] = float[9](-1,-2,-1, 0,0,0, 1,2,1);
        for (int i = 0; i < 9; i++) {
            int px = int(x) + sx[i];
            int py = int(y) + sy[i];
            if (px >= 0 && px < img_w && py >= 0 && py < img_h) {
                vec4 p = input_img[py * img_w + px];
                gx += p * kx[i];
                gy += p * ky[i];
            }
        }
        float mag = min(length(vec2(length(gx.rgb), length(gy.rgb))), 1.0);
        result = vec4(vec3(mag), c.a);
    }
    else if (filter_type == 3) {
        float gray = dot(c.rgb, vec3(0.299, 0.587, 0.114));
        result = vec4(vec3(gray), c.a);
    }
    else if (filter_type == 4) {
        result = vec4(1.0 - c.rgb, c.a);
    }
    else if (filter_type == 5) {
        vec3 sepia;
        sepia.r = dot(c.rgb, vec3(0.393, 0.769, 0.189));
        sepia.g = dot(c.rgb, vec3(0.349, 0.686, 0.168));
        sepia.b = dot(c.rgb, vec3(0.272, 0.534, 0.131));
        result = vec4(clamp(sepia, 0.0, 1.0), c.a);
    }
    else if (filter_type == 6) {
        int bs = max(1, int(param0));
        int px = (int(x) / bs) * bs + bs / 2;
        int py = (int(y) / bs) * bs + bs / 2;
        px = min(px, img_w - 1);
        py = min(py, img_h - 1);
        result = input_img[py * img_w + px];
    }
    else if (filter_type == 7) {
        float levels = max(2.0, param0);
        result = vec4(floor(c.rgb * levels) / levels, c.a);
    }
    
    output_img[idx] = result;
}
)glsl";

class GPUOps {
public:
    GPUOps() : m_initialized(false), m_blend_program(0), m_filter_program(0) {}
    
    ~GPUOps() {
        cleanup();
    }
    
    bool init() {
        if (m_initialized) return true;
        
        // Check OpenGL version
        const char* version = (const char*)glGetString(GL_VERSION);
        int major = 0, minor = 0;
        if (version) {
            sscanf(version, "%d.%d", &major, &minor);
        }
        
        if (major < 4 || (major == 4 && minor < 3)) {
            std::cerr << "[GPU] OpenGL " << (version ? version : "unknown")
                      << " < 4.3, compute shaders not available" << std::endl;
            return false;
        }
        
        m_glCreateProgram = (PFNGLCREATEPROGRAMPROC)getProc("glCreateProgram");
        m_glCreateShader = (PFNGLCREATESHADERPROC)getProc("glCreateShader");
        m_glShaderSource = (PFNGLSHADERSOURCEPROC)getProc("glShaderSource");
        m_glCompileShader = (PFNGLCOMPILESHADERPROC)getProc("glCompileShader");
        m_glAttachShader = (PFNGLATTACHSHADERPROC)getProc("glAttachShader");
        m_glLinkProgram = (PFNGLLINKPROGRAMPROC)getProc("glLinkProgram");
        m_glUseProgram = (PFNGLUSEPROGRAMPROC)getProc("glUseProgram");
        m_glGetShaderiv = (PFNGLGETSHADERIVPROC)getProc("glGetShaderiv");
        m_glGetProgramiv = (PFNGLGETPROGRAMIVPROC)getProc("glGetProgramiv");
        m_glGetShaderInfoLog = (PFNGLGETSHADERINFOLOGPROC)getProc("glGetShaderInfoLog");
        m_glGetProgramInfoLog = (PFNGLGETPROGRAMINFOLOGPROC)getProc("glGetProgramInfoLog");
        m_glGenBuffers = (PFNGLGENBUFFERSPROC)getProc("glGenBuffers");
        m_glBindBuffer = (PFNGLBINDBUFFERPROC)getProc("glBindBuffer");
        m_glBufferData = (PFNGLBUFFERDATAPROC)getProc("glBufferData");
        m_glBufferSubData = (PFNGLBUFFERSUBDATAPROC)getProc("glBufferSubData");
        m_glGetBufferSubData = (PFNGLGETBUFFERSUBDATAPROC)getProc("glGetBufferSubData");
        m_glBindBufferBase = (PFNGLBINDBUFFERBASEPROC)getProc("glBindBufferBase");
        m_glGetUniformLocation = (PFNGLGETUNIFORMLOCATIONPROC)getProc("glGetUniformLocation");
        m_glUniform1i = (PFNGLUNIFORM1IPROC)getProc("glUniform1i");
        m_glUniform1f = (PFNGLUNIFORM1FPROC)getProc("glUniform1f");
        m_glDispatchCompute = (PFNGLDISPATCHCOMPUTEPROC)getProc("glDispatchCompute");
        m_glMemoryBarrier = (PFNGLMEMORYBARRIERPROC)getProc("glMemoryBarrier");
        m_glDeleteProgram = (PFNGLDELETEPROGRAMSPROC)getProc("glDeleteProgram");
        m_glDeleteShader = (PFNGLDELETESHADERSPROC)getProc("glDeleteShader");
        m_glDeleteBuffers = (PFNGLDELETEBUFFERSPROC)getProc("glDeleteBuffers");
        m_glFinish = (PFNGLFINISHPROC)getProc("glFinish");
        
        if (!m_glCreateProgram || !m_glCreateShader || !m_glDispatchCompute) {
            std::cerr << "[GPU] OpenGL compute shaders not available" << std::endl;
            return false;
        }
        
        m_blend_program = buildProgram(BLEND_COMPUTE_SRC);
        m_filter_program = buildProgram(FILTER_COMPUTE_SRC);
        
        if (!m_blend_program || !m_filter_program) {
            cleanup();
            return false;
        }
        
        m_initialized = true;
        std::cout << "[GPU] OpenGL compute shaders initialized (GL " << version << ")" << std::endl;
        return true;
    }
    
    bool isAvailable() const { return m_initialized; }
    
    struct ImageData {
        std::vector<float> pixels;
        int width, height;
    };
    
    ImageData blend(const ImageData& bottom, const ImageData& top, int mode, float opacity) {
        if (!m_initialized) return {};
        
        int w = bottom.width, h = bottom.height;
        int size = w * h * 4;
        
        GLuint ssbo[3];
        m_glGenBuffers(3, ssbo);
        
        m_glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo[0]);
        m_glBufferData(GL_SHADER_STORAGE_BUFFER, size * sizeof(float), bottom.pixels.data(), GL_STATIC_DRAW);
        m_glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, ssbo[0]);
        
        m_glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo[1]);
        m_glBufferData(GL_SHADER_STORAGE_BUFFER, size * sizeof(float), top.pixels.data(), GL_STATIC_DRAW);
        m_glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, ssbo[1]);
        
        std::vector<float> output(size, 0.0f);
        m_glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo[2]);
        m_glBufferData(GL_SHADER_STORAGE_BUFFER, size * sizeof(float), output.data(), GL_STATIC_DRAW);
        m_glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, ssbo[2]);
        
        m_glUseProgram(m_blend_program);
        m_glUniform1i(m_glGetUniformLocation(m_blend_program, "mode"), mode);
        m_glUniform1f(m_glGetUniformLocation(m_blend_program, "opacity"), opacity);
        m_glUniform1i(m_glGetUniformLocation(m_blend_program, "img_w"), w);
        m_glUniform1i(m_glGetUniformLocation(m_blend_program, "img_h"), h);
        
        m_glDispatchCompute((w + 15) / 16, (h + 15) / 16, 1);
        m_glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT);
        
        m_glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo[2]);
        m_glGetBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, size * sizeof(float), output.data());
        
        m_glDeleteBuffers(3, ssbo);
        
        return {output, w, h};
    }
    
    ImageData filter(const ImageData& input, int filter_type, float param0) {
        if (!m_initialized) return {};
        
        int w = input.width, h = input.height;
        int size = w * h * 4;
        
        GLuint ssbo[2];
        m_glGenBuffers(2, ssbo);
        
        m_glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo[0]);
        m_glBufferData(GL_SHADER_STORAGE_BUFFER, size * sizeof(float), input.pixels.data(), GL_STATIC_DRAW);
        m_glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, ssbo[0]);
        
        std::vector<float> output(size, 0.0f);
        m_glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo[1]);
        m_glBufferData(GL_SHADER_STORAGE_BUFFER, size * sizeof(float), output.data(), GL_STATIC_DRAW);
        m_glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, ssbo[1]);
        
        m_glUseProgram(m_filter_program);
        m_glUniform1i(m_glGetUniformLocation(m_filter_program, "filter_type"), filter_type);
        m_glUniform1f(m_glGetUniformLocation(m_filter_program, "param0"), param0);
        m_glUniform1i(m_glGetUniformLocation(m_filter_program, "img_w"), w);
        m_glUniform1i(m_glGetUniformLocation(m_filter_program, "img_h"), h);
        
        m_glDispatchCompute((w + 15) / 16, (h + 15) / 16, 1);
        m_glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT);
        
        m_glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo[1]);
        m_glGetBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, size * sizeof(float), output.data());
        
        m_glDeleteBuffers(2, ssbo);
        
        return {output, w, h};
    }
    
    static std::vector<float> imageToFloats(const void* data, int w, int h) {
        std::vector<float> pixels(w * h * 4);
        const unsigned char* src = static_cast<const unsigned char*>(data);
        for (int i = 0; i < w * h; i++) {
            pixels[i * 4 + 0] = src[i * 4 + 0] / 255.0f;
            pixels[i * 4 + 1] = src[i * 4 + 1] / 255.0f;
            pixels[i * 4 + 2] = src[i * 4 + 2] / 255.0f;
            pixels[i * 4 + 3] = src[i * 4 + 3] / 255.0f;
        }
        return pixels;
    }
    
    static std::vector<unsigned char> floatsToBytes(const std::vector<float>& pixels) {
        std::vector<unsigned char> result(pixels.size());
        for (size_t i = 0; i < pixels.size(); i++) {
            result[i] = static_cast<unsigned char>(std::max(0.0f, std::min(255.0f, pixels[i] * 255.0f)));
        }
        return result;
    }

private:
    bool m_initialized;
    GLuint m_blend_program;
    GLuint m_filter_program;
    
    PFNGLCREATEPROGRAMPROC m_glCreateProgram;
    PFNGLCREATESHADERPROC m_glCreateShader;
    PFNGLSHADERSOURCEPROC m_glShaderSource;
    PFNGLCOMPILESHADERPROC m_glCompileShader;
    PFNGLATTACHSHADERPROC m_glAttachShader;
    PFNGLLINKPROGRAMPROC m_glLinkProgram;
    PFNGLUSEPROGRAMPROC m_glUseProgram;
    PFNGLGETSHADERIVPROC m_glGetShaderiv;
    PFNGLGETPROGRAMIVPROC m_glGetProgramiv;
    PFNGLGETSHADERINFOLOGPROC m_glGetShaderInfoLog;
    PFNGLGETPROGRAMINFOLOGPROC m_glGetProgramInfoLog;
    PFNGLGENBUFFERSPROC m_glGenBuffers;
    PFNGLBINDBUFFERPROC m_glBindBuffer;
    PFNGLBUFFERDATAPROC m_glBufferData;
    PFNGLBUFFERSUBDATAPROC m_glBufferSubData;
    PFNGLGETBUFFERSUBDATAPROC m_glGetBufferSubData;
    PFNGLBINDBUFFERBASEPROC m_glBindBufferBase;
    PFNGLGETUNIFORMLOCATIONPROC m_glGetUniformLocation;
    PFNGLUNIFORM1IPROC m_glUniform1i;
    PFNGLUNIFORM1FPROC m_glUniform1f;
    PFNGLDISPATCHCOMPUTEPROC m_glDispatchCompute;
    PFNGLMEMORYBARRIERPROC m_glMemoryBarrier;
    PFNGLDELETEPROGRAMSPROC m_glDeleteProgram;
    PFNGLDELETESHADERPROC m_glDeleteShader;
    PFNGLDELETEBUFFERSPROC m_glDeleteBuffers;
    PFNGLFINISHPROC m_glFinish;
    
    void* getProc(const char* name) {
#ifdef _WIN32
        return (void*)wglGetProcAddress(name);
#elif defined(__APPLE__)
        (void)name;
        return (void*)glGetString(GL_VERSION);
#else
        return (void*)glXGetProcAddress((const GLubyte*)name);
#endif
    }
    
    GLuint compileShader(const char* source) {
        GLuint shader = m_glCreateShader(GL_COMPUTE_SHADER);
        m_glShaderSource(shader, 1, &source, nullptr);
        m_glCompileShader(shader);
        
        GLint compiled = 0;
        m_glGetShaderiv(shader, GL_COMPILE_STATUS, &compiled);
        if (!compiled) {
            char log[1024] = {0};
            m_glGetShaderInfoLog(shader, sizeof(log), nullptr, log);
            std::cerr << "[GPU] Shader compilation error: " << log << std::endl;
            m_glDeleteShader(shader);
            return 0;
        }
        return shader;
    }
    
    GLuint buildProgram(const char* source) {
        GLuint shader = compileShader(source);
        if (!shader) return 0;
        
        GLuint program = m_glCreateProgram();
        m_glAttachShader(program, shader);
        m_glLinkProgram(program);
        
        GLint linked = 0;
        m_glGetProgramiv(program, GL_LINK_STATUS, &linked);
        if (!linked) {
            char log[1024] = {0};
            m_glGetProgramInfoLog(program, sizeof(log), nullptr, log);
            std::cerr << "[GPU] Program link error: " << log << std::endl;
            m_glDeleteProgram(program);
            m_glDeleteShader(shader);
            return 0;
        }
        
        m_glDeleteShader(shader);
        return program;
    }
    
    void cleanup() {
        if (m_blend_program) m_glDeleteProgram(m_blend_program);
        if (m_filter_program) m_glDeleteProgram(m_filter_program);
        m_blend_program = 0;
        m_filter_program = 0;
        m_initialized = false;
    }
};

#endif
