#include "tools.h"
#include "canvas.h"
#include <QColor>

void Tool::press(CanvasView *, const QPointF &) {}
void Tool::move(CanvasView *, const QPointF &, const QPointF &) {}
void Tool::release(CanvasView *, const QPointF &) {}

void PencilTool::press(CanvasView *canvas, const QPointF &pos)
{
    canvas->drawPoint(pos);
}

void PencilTool::move(CanvasView *canvas, const QPointF &last, const QPointF &pos)
{
    canvas->drawLine(last, pos);
}

void BrushTool::press(CanvasView *canvas, const QPointF &pos)
{
    canvas->drawPoint(pos);
}

void BrushTool::move(CanvasView *canvas, const QPointF &last, const QPointF &pos)
{
    canvas->drawLine(last, pos);
}

void EraserTool::press(CanvasView *canvas, const QPointF &pos)
{
    canvas->erasePoint(pos);
}

void EraserTool::move(CanvasView *canvas, const QPointF &last, const QPointF &pos)
{
    canvas->eraseLine(last, pos);
}

void ColorPickerTool::press(CanvasView *canvas, const QPointF &pos)
{
    QColor c = canvas->getPixelColor(pos);
    if (c.isValid())
        canvas->setForegroundColor(c);
}

void FloodFillTool::press(CanvasView *canvas, const QPointF &pos)
{
    canvas->floodFill(pos);
}
