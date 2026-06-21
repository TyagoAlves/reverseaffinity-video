#ifndef TOOLS_H
#define TOOLS_H

#include <QPointF>
#include <QColor>
#include <QString>

class CanvasView;

class Tool {
public:
    virtual ~Tool() = default;
    virtual QString name() const = 0;
    virtual void press(CanvasView *canvas, const QPointF &pos);
    virtual void move(CanvasView *canvas, const QPointF &last, const QPointF &pos);
    virtual void release(CanvasView *canvas, const QPointF &pos);
};

class PencilTool : public Tool {
public:
    QString name() const override { return "pencil"; }
    void press(CanvasView *canvas, const QPointF &pos) override;
    void move(CanvasView *canvas, const QPointF &last, const QPointF &pos) override;
};

class BrushTool : public Tool {
public:
    QString name() const override { return "brush"; }
    void press(CanvasView *canvas, const QPointF &pos) override;
    void move(CanvasView *canvas, const QPointF &last, const QPointF &pos) override;
};

class EraserTool : public Tool {
public:
    QString name() const override { return "eraser"; }
    void press(CanvasView *canvas, const QPointF &pos) override;
    void move(CanvasView *canvas, const QPointF &last, const QPointF &pos) override;
};

class ColorPickerTool : public Tool {
public:
    QString name() const override { return "color_picker"; }
    void press(CanvasView *canvas, const QPointF &pos) override;
};

class FloodFillTool : public Tool {
public:
    QString name() const override { return "flood_fill"; }
    void press(CanvasView *canvas, const QPointF &pos) override;
};

#endif
