#include "gl_canvas.h"
#include <QWheelEvent>
#include <QMouseEvent>
#include <QPainter>
#include <GL/gl.h>

GLCanvas::GLCanvas(QWidget *parent)
    : QOpenGLWidget(parent)
{
    setMouseTracking(true);
}

GLCanvas::~GLCanvas()
{
    makeCurrent();
    if (textureId_) {
        glDeleteTextures(1, &textureId_);
    }
}

void GLCanvas::setImage(const QImage &img)
{
    image_ = img.convertToFormat(QImage::Format_RGBA8888);
    if (textureId_) {
        makeCurrent();
        uploadTexture();
        doneCurrent();
    }
    update();
}

void GLCanvas::setZoomFactor(double factor)
{
    zoomFactor_ = std::max(0.01, factor);
    emit zoomChanged(zoomFactor_);
    update();
}

void GLCanvas::setPanOffset(double dx, double dy)
{
    panX_ = dx;
    panY_ = dy;
    emit panChanged(panX_, panY_);
    update();
}

void GLCanvas::initializeGL()
{
    initializeOpenGLFunctions();
    glClearColor(0.15f, 0.15f, 0.15f, 1.0f);

    glGenTextures(1, &textureId_);
    glBindTexture(GL_TEXTURE_2D, textureId_);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

    if (!image_.isNull()) {
        uploadTexture();
    }
}

void GLCanvas::resizeGL(int w, int h)
{
    glViewport(0, 0, w, h);
}

void GLCanvas::paintGL()
{
    glClear(GL_COLOR_BUFFER_BIT);

    if (image_.isNull() || !textureId_)
        return;

    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, width(), height(), 0, -1, 1);

    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    glEnable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, textureId_);

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    double imgW = image_.width();
    double imgH = image_.height();
    double cx = width() / 2.0 + panX_;
    double cy = height() / 2.0 + panY_;
    double halfW = imgW * zoomFactor_ / 2.0;
    double halfH = imgH * zoomFactor_ / 2.0;

    glColor4f(1.0f, 1.0f, 1.0f, 1.0f);
    glBegin(GL_QUADS);
    glTexCoord2f(0.0f, 0.0f); glVertex2f(cx - halfW, cy - halfH);
    glTexCoord2f(1.0f, 0.0f); glVertex2f(cx + halfW, cy - halfH);
    glTexCoord2f(1.0f, 1.0f); glVertex2f(cx + halfW, cy + halfH);
    glTexCoord2f(0.0f, 1.0f); glVertex2f(cx - halfW, cy + halfH);
    glEnd();

    glDisable(GL_BLEND);
    glDisable(GL_TEXTURE_2D);
}

void GLCanvas::uploadTexture()
{
    if (!textureId_ || image_.isNull())
        return;

    glBindTexture(GL_TEXTURE_2D, textureId_);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                 image_.width(), image_.height(), 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, image_.constBits());
}

void GLCanvas::wheelEvent(QWheelEvent *event)
{
    double factor = event->angleDelta().y() > 0 ? 1.15 : 1.0 / 1.15;
    zoomFactor_ *= factor;
    if (zoomFactor_ < 0.01) zoomFactor_ = 0.01;
    if (zoomFactor_ > 100.0) zoomFactor_ = 100.0;
    emit zoomChanged(zoomFactor_);
    update();
}

void GLCanvas::mousePressEvent(QMouseEvent *event)
{
    if (event->button() == Qt::MiddleButton || event->button() == Qt::LeftButton) {
        dragging_ = true;
        lastMousePos_ = event->pos();
        setCursor(Qt::ClosedHandCursor);
    }
}

void GLCanvas::mouseMoveEvent(QMouseEvent *event)
{
    if (dragging_) {
        QPoint delta = event->pos() - lastMousePos_;
        panX_ += delta.x();
        panY_ += delta.y();
        lastMousePos_ = event->pos();
        emit panChanged(panX_, panY_);
        update();
    }
}

void GLCanvas::mouseReleaseEvent(QMouseEvent *event)
{
    if (dragging_) {
        dragging_ = false;
        setCursor(Qt::ArrowCursor);
    }
}
