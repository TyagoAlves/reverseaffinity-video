#ifndef CANVAS_H
#define CANVAS_H

#include <QGraphicsView>
#include <QGraphicsScene>
#include <QGraphicsPixmapItem>
#include <QImage>
#include <QPointF>
#include <QColor>
#include <QVector>
#include <QPainter>

#include "layers.h"
#include "history.h"

class Tool;

class CanvasView : public QGraphicsView {
    Q_OBJECT
public:
    explicit CanvasView(QWidget *parent = nullptr);

    void newImage(int width, int height, const QColor &bg = Qt::white);
    bool openImage(const QString &path);
    bool saveImage(const QString &path);
    bool exportPng(const QString &path);

    void setTool(const QString &toolName);
    void setToolSize(int size) { toolSize_ = qMax(1, size); }
    void setBrushShape(const QString &shape);
    void setForegroundColor(const QColor &c) { toolColor_ = c; }
    void setBackgroundColor(const QColor &c) { bgColor_ = c; }

    void drawPoint(const QPointF &pos);
    void drawLine(const QPointF &p1, const QPointF &p2);
    void erasePoint(const QPointF &pos);
    void eraseLine(const QPointF &p1, const QPointF &p2);
    QColor getPixelColor(const QPointF &pos) const;
    void floodFill(const QPointF &pos);

    void zoomIn();
    void zoomOut();
    void zoomFit();
    void zoom100();

    void saveState(const QString &desc = "Edit");

    LayerStack layerStack;
    HistoryManager history;
    Tool *tool = nullptr;
    int toolSize_ = 3;
    QColor toolColor_ = Qt::black;
    QColor bgColor_ = Qt::white;
    QString brushShape_ = "round";
    bool drawing_ = false;
    QPointF lastPoint_;
    QPointF selectionStart_;

signals:
    void mouseMoved(double x, double y);
    void statusChanged(const QString &msg);

protected:
    void wheelEvent(QWheelEvent *event) override;
    void mousePressEvent(QMouseEvent *event) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void mouseReleaseEvent(QMouseEvent *event) override;
    void keyPressEvent(QKeyEvent *event) override;
    void drawBackground(QPainter *painter, const QRectF &rect) override;

public:
    void refresh();

private:
    QGraphicsScene *scene_;
    QGraphicsPixmapItem *pixmapItem_;
    double zoomLevel_ = 1.0;
    QPixmap checkerTile_;
};

#endif
