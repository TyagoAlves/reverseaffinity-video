#ifndef GL_CANVAS_H
#define GL_CANVAS_H

#include <QOpenGLWidget>
#include <QOpenGLFunctions>
#include <QImage>

class GLCanvas : public QOpenGLWidget, protected QOpenGLFunctions {
    Q_OBJECT
public:
    explicit GLCanvas(QWidget *parent = nullptr);
    ~GLCanvas() override;

    void setImage(const QImage &img);
    void setZoomFactor(double factor);
    void setPanOffset(double dx, double dy);

signals:
    void zoomChanged(double factor);
    void panChanged(double dx, double dy);

protected:
    void initializeGL() override;
    void resizeGL(int w, int h) override;
    void paintGL() override;
    void wheelEvent(QWheelEvent *event) override;
    void mousePressEvent(QMouseEvent *event) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void mouseReleaseEvent(QMouseEvent *event) override;

private:
    void uploadTexture();

    GLuint textureId_ = 0;
    QImage image_;
    double zoomFactor_ = 1.0;
    double panX_ = 0.0;
    double panY_ = 0.0;
    bool dragging_ = false;
    QPoint lastMousePos_;
};

#endif
