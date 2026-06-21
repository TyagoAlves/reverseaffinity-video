import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QOpenGLShader, QOpenGLShaderProgram
from PyQt5.QtWidgets import QOpenGLWidget


class VideoShaderProgram:
    def __init__(self):
        self.program = QOpenGLShaderProgram()
        self._vs = None
        self._fs = None

    def compile_vertex_shader(self, source):
        self._vs = QOpenGLShader(QOpenGLShader.Vertex, self.program)
        if not self._vs.compileSourceCode(source):
            raise RuntimeError(f"Vertex shader error: {self._vs.log()}")
        return self._vs

    def compile_fragment_shader(self, source):
        self._fs = QOpenGLShader(QOpenGLShader.Fragment, self.program)
        if not self._fs.compileSourceCode(source):
            raise RuntimeError(f"Fragment shader error: {self._fs.log()}")
        return self._fs

    def link_program(self, vs=None, fs=None):
        if vs is not None:
            self.program.addShader(vs)
        if fs is not None:
            self.program.addShader(fs)
        if not self.program.link():
            raise RuntimeError(f"Program link error: {self.program.log()}")
        return self.program

    def bind(self):
        self.program.bind()

    def unbind(self):
        self.program.release()

    def set_uniform(self, name, value):
        loc = self.program.uniformLocation(name)
        if loc < 0:
            return
        if isinstance(value, (int, bool)):
            self.program.setUniformValue(loc, int(value))
        elif isinstance(value, float):
            self.program.setUniformValue(loc, float(value))
        elif isinstance(value, (list, tuple)):
            if len(value) == 2:
                self.program.setUniformValue(loc, float(value[0]), float(value[1]))
            elif len(value) == 3:
                self.program.setUniformValue(
                    loc, float(value[0]), float(value[1]), float(value[2])
                )
            elif len(value) == 4:
                self.program.setUniformValue(
                    loc,
                    float(value[0]),
                    float(value[1]),
                    float(value[2]),
                    float(value[3]),
                )
        elif isinstance(value, np.ndarray):
            self.program.setUniformValue(loc, value)
        else:
            self.program.setUniformValue(loc, value)


class GLTexture:
    def __init__(self):
        self.texture_id = 0
        self.width = 0
        self.height = 0
        self._initialized = False

    def create_from_frame(self, np_array):
        from PyQt5.QtGui import QOpenGLContext
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return False
        gl = ctx.versionFunctions()
        if gl is None:
            from OpenGL import GL
            gl = GL

        h, w = np_array.shape[:2]
        self.width = w
        self.height = h

        if not self._initialized:
            textures = gl.glGenTextures(1)
            self.texture_id = textures if hasattr(textures, '__len__') else textures
            if isinstance(textures, (list, tuple)):
                self.texture_id = textures[0]
            self._initialized = True

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        data = np_array.astype(np.uint8)
        if data.flags['C_CONTIGUOUS']:
            data = np.ascontiguousarray(data)

        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, gl.GL_RGB, w, h, 0,
            gl.GL_RGB, gl.GL_UNSIGNED_BYTE, data
        )
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        return True

    def bind(self, unit=0):
        from PyQt5.QtGui import QOpenGLContext
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return
        gl = ctx.versionFunctions()
        if gl is None:
            from OpenGL import GL
            gl = GL
        gl.glActiveTexture(gl.GL_TEXTURE0 + unit)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

    def release(self):
        from PyQt5.QtGui import QOpenGLContext
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return
        gl = ctx.versionFunctions()
        if gl is None:
            from OpenGL import GL
            gl = GL
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def destroy(self):
        if self._initialized:
            from PyQt5.QtGui import QOpenGLContext
            ctx = QOpenGLContext.currentContext()
            if ctx is not None:
                gl = ctx.versionFunctions()
                if gl is None:
                    from OpenGL import GL
                    gl = GL
                gl.glDeleteTextures(1, [self.texture_id])
            self._initialized = False
            self.texture_id = 0


VERTEX_SHADER_SRC = """
#version 130
in vec4 vertex;
in vec2 texcoord;
out vec2 v_texcoord;
void main() {
    gl_Position = vertex;
    v_texcoord = texcoord;
}
"""

FRAGMENT_SHADER_SRC = """
#version 130
uniform sampler2D texture;
uniform float brightness;
uniform float contrast;
uniform float saturation;
in vec2 v_texcoord;
out vec4 fragColor;

vec3 rgb2hsv(vec3 c) {
    vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec4 col = texture2D(texture, v_texcoord);
    col.rgb = col.rgb * brightness;
    col.rgb = (col.rgb - 0.5) * contrast + 0.5;
    vec3 hsv = rgb2hsv(col.rgb);
    hsv.y = clamp(hsv.y * saturation, 0.0, 1.0);
    col.rgb = hsv2rgb(hsv);
    fragColor = col;
}
"""


class VideoGLPlayer(QOpenGLWidget):
    frame_ready = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shader_program = None
        self._texture = GLTexture()
        self._aspect_ratio = 16.0 / 9.0
        self._timecode = "00:00:00.00"
        self._brightness = 1.0
        self._contrast = 1.0
        self._saturation = 1.0
        self._has_frame = False
        self._bg_color_1 = QColor(25, 25, 28)
        self._bg_color_2 = QColor(18, 18, 20)
        self._checker_size = 16
        self._frame_data = None
        self._pending_frame = None

        self.setMinimumSize(160, 90)
        self.setFocusPolicy(Qt.StrongFocus)

    def initializeGL(self):
        from PyQt5.QtGui import QOpenGLContext
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return
        gl = ctx.versionFunctions()
        if gl is None:
            from OpenGL import GL as gl_mod
            gl = gl_mod
        gl.glClearColor(0.09, 0.09, 0.10, 1.0)
        gl.glEnable(gl.GL_TEXTURE_2D)

        self._shader_program = VideoShaderProgram()
        vs = self._shader_program.compile_vertex_shader(VERTEX_SHADER_SRC)
        fs = self._shader_program.compile_fragment_shader(FRAGMENT_SHADER_SRC)
        self._shader_program.link_program(vs, fs)

    def resizeGL(self, w, h):
        from PyQt5.QtGui import QOpenGLContext
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return
        gl = ctx.versionFunctions()
        if gl is None:
            from OpenGL import GL as gl_mod
            gl = gl_mod
        gl.glViewport(0, 0, w, h)

    def paintGL(self):
        from PyQt5.QtGui import QOpenGLContext
        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            return
        gl = ctx.versionFunctions()
        if gl is None:
            from OpenGL import GL as gl_mod
            gl = gl_mod

        gl.glClearColor(0.09, 0.09, 0.10, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        self._draw_checkerboard(gl)

        if self._has_frame:
            self._render_video_frame(gl)

        self._draw_timecode()

    def _draw_checkerboard(self, gl):
        w = self.width()
        h = self.height()

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, w, h, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_TEXTURE_2D)

        cols = (w // self._checker_size) + 2
        rows = (h // self._checker_size) + 2

        for y in range(rows):
            for x in range(cols):
                is_dark = (x + y) % 2 == 0
                color = self._bg_color_1 if is_dark else self._bg_color_2
                rx = x * self._checker_size
                ry = y * self._checker_size
                gl.glColor4f(
                    color.redF(), color.greenF(), color.blueF(), 1.0
                )
                gl.glBegin(gl.GL_QUADS)
                gl.glVertex2f(rx, ry)
                gl.glVertex2f(rx + self._checker_size, ry)
                gl.glVertex2f(rx + self._checker_size, ry + self._checker_size)
                gl.glVertex2f(rx, ry + self._checker_size)
                gl.glEnd()

    def _compute_video_rect(self):
        w = self.width()
        h = self.height()
        vw = float(w)
        vh = float(h)
        ar = self._aspect_ratio

        if vw / vh > ar:
            vw = vh * ar
        else:
            vh = vw / ar

        ox = (w - vw) * 0.5
        oy = (h - vh) * 0.5
        return ox, oy, vw, vh

    def _render_video_frame(self, gl):
        ox, oy, vw, vh = self._compute_video_rect()

        gl.glEnable(gl.GL_TEXTURE_2D)
        self._texture.bind(0)

        vertices = [
            ox, oy + vh,
            ox + vw, oy + vh,
            ox + vw, oy,
            ox, oy,
        ]
        texcoords = [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]

        self._shader_program.bind()
        self._shader_program.set_uniform("texture", 0)
        self._shader_program.set_uniform("brightness", self._brightness)
        self._shader_program.set_uniform("contrast", self._contrast)
        self._shader_program.set_uniform("saturation", self._saturation)

        gl.glBegin(gl.GL_QUADS)
        for i in range(4):
            gl.glTexCoord2f(texcoords[i * 2], texcoords[i * 2 + 1])
            gl.glVertex2f(vertices[i * 2], vertices[i * 2 + 1])
        gl.glEnd()

        self._shader_program.unbind()
        self._texture.release()
        gl.glDisable(gl.GL_TEXTURE_2D)

    def _draw_timecode(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = QFont("Consolas, Courier New, monospace")
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(200, 200, 200, 200))

        ox, oy, vw, vh = self._compute_video_rect()
        text_x = ox + 10
        text_y = oy + 18
        painter.drawText(text_x, text_y, self._timecode)

        if not self._has_frame:
            painter.setPen(QColor(255, 255, 255, 100))
            painter.setFont(QFont("Consolas, Courier New, monospace", 16))
            painter.drawText(
                self.rect(), Qt.AlignCenter, "Sem sinal de video"
            )

        painter.end()

    def set_frame(self, np_array):
        if np_array is None:
            self._has_frame = False
            self.update()
            return

        h, w = np_array.shape[:2]

        if np_array.dtype != np.uint8:
            np_array = np.clip(np_array, 0, 255).astype(np.uint8)

        if len(np_array.shape) == 2:
            np_array = np.stack([np_array] * 3, axis=-1)
        elif np_array.shape[2] == 4:
            np_array = np_array[:, :, :3]

        self._frame_data = np.ascontiguousarray(np_array)

        if self._texture.create_from_frame(self._frame_data):
            self._has_frame = True
            self._aspect_ratio = float(w) / float(h) if h > 0 else self._aspect_ratio

        self.update()
        self.frame_ready.emit()

    def set_aspect_ratio(self, ratio):
        if ratio > 0:
            self._aspect_ratio = ratio
            self.update()

    def set_timecode(self, timecode):
        self._timecode = timecode
        self.update()

    def set_adjustment(self, brightness=None, contrast=None, saturation=None):
        if brightness is not None:
            self._brightness = max(0.0, min(3.0, brightness))
        if contrast is not None:
            self._contrast = max(0.0, min(3.0, contrast))
        if saturation is not None:
            self._saturation = max(0.0, min(3.0, saturation))
        self.update()

    def brightness(self):
        return self._brightness

    def contrast(self):
        return self._contrast

    def saturation(self):
        return self._saturation

    def has_frame(self):
        return self._has_frame

    def current_frame_qimage(self):
        if not self._has_frame or self._frame_data is None:
            return None
        from PyQt5.QtGui import QImage
        h, w, c = self._frame_data.shape
        fmt = QImage.Format_RGB888 if c == 3 else QImage.Format_RGBA8888
        return QImage(self._frame_data.data, w, h, w * c, fmt).copy()

    def current_aspect_ratio(self):
        return self._aspect_ratio

    def __del__(self):
        self._texture.destroy()
