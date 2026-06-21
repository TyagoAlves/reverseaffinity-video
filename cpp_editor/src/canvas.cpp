#include "canvas.h"
#include "tools.h"
#include <QWheelEvent>
#include <QMouseEvent>
#include <QKeyEvent>
#include <QPainter>
#include <QFileInfo>
#include <QScrollBar>
#include <queue>
#include <set>
#include <tuple>

CanvasView::CanvasView(QWidget *parent)
    : QGraphicsView(parent)
{
    scene_ = new QGraphicsScene(this);
    setScene(scene_);
    pixmapItem_ = new QGraphicsPixmapItem();
    scene_->addItem(pixmapItem_);

    layerStack = LayerStack(800, 600);

    auto shots = snapshotFromLayers(layerStack.layers);
    history.push("New document", shots, layerStack.activeIndex_);

    setRenderHint(QPainter::Antialiasing);
    setRenderHint(QPainter::SmoothPixmapTransform);
    setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    setMouseTracking(true);

    tool = new PencilTool();

    QPixmap tile(16, 16);
    QPainter pt(&tile);
    pt.fillRect(0, 0, 8, 8, QColor(60, 60, 60));
    pt.fillRect(8, 0, 8, 8, QColor(45, 45, 45));
    pt.fillRect(0, 8, 8, 8, QColor(45, 45, 45));
    pt.fillRect(8, 8, 8, 8, QColor(60, 60, 60));
    pt.end();
    checkerTile_ = tile;

    refresh();
}

void CanvasView::drawBackground(QPainter *painter, const QRectF &rect)
{
    painter->fillRect(rect, QColor(35, 35, 35));
    painter->drawTiledPixmap(rect, checkerTile_);
}

void CanvasView::refresh()
{
    QImage composite = layerStack.composite();
    pixmapItem_->setPixmap(QPixmap::fromImage(composite));
    scene_->setSceneRect(composite.rect());
}

void CanvasView::saveState(const QString &desc)
{
    auto shots = snapshotFromLayers(layerStack.layers);
    history.push(desc, shots, layerStack.activeIndex_);
}

void CanvasView::newImage(int width, int height, const QColor &bg)
{
    layerStack = LayerStack(width, height);
    if (bg != Qt::white)
        layerStack.layers[0].image.fill(bg);
    history.clear();
    auto shots = snapshotFromLayers(layerStack.layers);
    history.push("New document", shots, layerStack.activeIndex_);
    refresh();
}

bool CanvasView::openImage(const QString &path)
{
    QImage img(path);
    if (img.isNull()) return false;
    if (img.format() != QImage::Format_ARGB32)
        img = img.convertToFormat(QImage::Format_ARGB32);

    layerStack = LayerStack(img.width(), img.height());
    layerStack.layers[0].image = img.copy();
    history.clear();
    auto shots = snapshotFromLayers(layerStack.layers);
    history.push("Open " + QFileInfo(path).fileName(), shots, layerStack.activeIndex_);
    refresh();
    return true;
}

bool CanvasView::saveImage(const QString &path)
{
    QImage composite = layerStack.composite();
    return composite.save(path);
}

bool CanvasView::exportPng(const QString &path)
{
    QImage composite = layerStack.composite();
    return composite.save(path, "PNG");
}

void CanvasView::setTool(const QString &toolName)
{
    delete tool;
    if (toolName == "pencil") tool = new PencilTool();
    else if (toolName == "brush") tool = new BrushTool();
    else if (toolName == "eraser") tool = new EraserTool();
    else if (toolName == "color_picker") tool = new ColorPickerTool();
    else if (toolName == "flood_fill") tool = new FloodFillTool();
    else tool = new PencilTool();
}

void CanvasView::setBrushShape(const QString &shape)
{
    brushShape_ = shape;
}

void CanvasView::drawPoint(const QPointF &pos)
{
    auto layer = layerStack.active();
    if (!layer || layer->locked) return;

    Qt::PenCapStyle cap = (brushShape_ == "square") ? Qt::SquareCap : Qt::RoundCap;
    QPainter painter(&layer->image);
    painter.setRenderHint(QPainter::Antialiasing);
    QPen pen(toolColor_, toolSize_, Qt::SolidLine, cap, Qt::RoundJoin);
    painter.setPen(pen);
    painter.drawPoint(pos);
    painter.end();
    refresh();
}

void CanvasView::drawLine(const QPointF &p1, const QPointF &p2)
{
    auto layer = layerStack.active();
    if (!layer || layer->locked) return;

    QPainter painter(&layer->image);
    painter.setRenderHint(QPainter::Antialiasing);
    Qt::PenCapStyle cap = (brushShape_ == "square") ? Qt::SquareCap : Qt::RoundCap;
    QPen pen(toolColor_, toolSize_, Qt::SolidLine, cap, Qt::RoundJoin);
    painter.setPen(pen);
    painter.drawLine(p1, p2);
    painter.end();
    refresh();
}

void CanvasView::erasePoint(const QPointF &pos)
{
    auto layer = layerStack.active();
    if (!layer || layer->locked) return;

    QPainter painter(&layer->image);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setCompositionMode(QPainter::CompositionMode_Clear);
    Qt::PenCapStyle cap = (brushShape_ == "square") ? Qt::SquareCap : Qt::RoundCap;
    QPen pen(QColor(0, 0, 0, 0), toolSize_, Qt::SolidLine, cap, Qt::RoundJoin);
    painter.setPen(pen);
    painter.drawPoint(pos);
    painter.end();
    refresh();
}

void CanvasView::eraseLine(const QPointF &p1, const QPointF &p2)
{
    auto layer = layerStack.active();
    if (!layer || layer->locked) return;

    QPainter painter(&layer->image);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setCompositionMode(QPainter::CompositionMode_Clear);
    QPen pen(QColor(0, 0, 0, 0), toolSize_, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin);
    painter.setPen(pen);
    painter.drawLine(p1, p2);
    painter.end();
    refresh();
}

QColor CanvasView::getPixelColor(const QPointF &pos) const
{
    auto layer = layerStack.active();
    if (!layer) return QColor();
    int x = qBound(0, (int)pos.x(), layer->image.width() - 1);
    int y = qBound(0, (int)pos.y(), layer->image.height() - 1);
    return layer->image.pixelColor(x, y);
}

void CanvasView::floodFill(const QPointF &pos)
{
    auto layer = layerStack.active();
    if (!layer || layer->locked) return;

    int x = (int)pos.x(), y = (int)pos.y();
    int w = layer->image.width(), h = layer->image.height();
    if (x < 0 || x >= w || y < 0 || y >= h) return;

    QColor target = layer->image.pixelColor(x, y);
    if (target == toolColor_) return;

    std::queue<std::pair<int,int>> queue;
    std::set<std::tuple<int,int>> visited;
    queue.push({x, y});
    visited.insert({x, y});

    QPainter painter(&layer->image);
    painter.setPen(QPen(toolColor_, 1));

    while (!queue.empty()) {
        auto [cx, cy] = queue.front(); queue.pop();
        if (layer->image.pixelColor(cx, cy) == target) {
            painter.drawPoint(cx, cy);
            for (auto [nx, ny] : {std::pair{cx+1,cy}, {cx-1,cy}, {cx,cy+1}, {cx,cy-1}}) {
                if (nx >= 0 && nx < w && ny >= 0 && ny < h && !visited.count({nx, ny})) {
                    visited.insert({nx, ny});
                    queue.push({nx, ny});
                }
            }
        }
    }
    painter.end();
    refresh();
}

void CanvasView::zoomIn()
{
    zoomLevel_ *= 1.25;
    resetTransform();
    scale(zoomLevel_, zoomLevel_);
}

void CanvasView::zoomOut()
{
    zoomLevel_ /= 1.25;
    resetTransform();
    scale(zoomLevel_, zoomLevel_);
}

void CanvasView::zoomFit()
{
    fitInView(scene_->sceneRect(), Qt::KeepAspectRatio);
    zoomLevel_ = transform().m11();
}

void CanvasView::zoom100()
{
    zoomLevel_ = 1.0;
    resetTransform();
}

void CanvasView::wheelEvent(QWheelEvent *event)
{
    if (event->modifiers() & Qt::ControlModifier) {
        double factor = event->angleDelta().y() > 0 ? 1.15 : 1.0 / 1.15;
        zoomLevel_ *= factor;
        scale(factor, factor);
        emit statusChanged(QString("Zoom: %1%").arg((int)(zoomLevel_ * 100)));
    } else {
        QGraphicsView::wheelEvent(event);
    }
}

void CanvasView::mousePressEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        drawing_ = true;
        QPointF pos = mapToScene(event->pos());
        lastPoint_ = pos;
        saveState(tool ? tool->name() : "Edit");
        if (tool) tool->press(this, pos);
    } else if (event->button() == Qt::MiddleButton) {
        setCursor(Qt::ClosedHandCursor);
        lastPoint_ = mapToScene(event->pos());
    }
}

void CanvasView::mouseMoveEvent(QMouseEvent *event)
{
    QPointF pos = mapToScene(event->pos());
    emit mouseMoved(pos.x(), pos.y());

    if (event->buttons() & Qt::MiddleButton) {
        QPointF delta = pos - lastPoint_;
        horizontalScrollBar()->setValue(horizontalScrollBar()->value() - delta.x());
        verticalScrollBar()->setValue(verticalScrollBar()->value() - delta.y());
        lastPoint_ = pos;
        return;
    }

    if (drawing_ && tool) {
        tool->move(this, lastPoint_, pos);
        lastPoint_ = pos;
    }
}

void CanvasView::mouseReleaseEvent(QMouseEvent *event)
{
    if (event->button() == Qt::MiddleButton) {
        setCursor(Qt::ArrowCursor);
    }
    if (event->button() == Qt::LeftButton && drawing_) {
        drawing_ = false;
        if (tool) tool->release(this, mapToScene(event->pos()));
    }
}

void CanvasView::keyPressEvent(QKeyEvent *event)
{
    if (event->modifiers() & Qt::ControlModifier) {
        if (event->key() == Qt::Key_Z) {
            if (event->modifiers() & Qt::ShiftModifier) {
                if (history.canRedo()) {
                    auto shots = snapshotFromLayers(layerStack.layers);
                    history.redo(shots, layerStack.activeIndex_);
                    restoreLayers(layerStack.layers, shots);
                    refresh();
                }
            } else {
                if (history.canUndo()) {
                    auto shots = snapshotFromLayers(layerStack.layers);
                    history.undo(shots, layerStack.activeIndex_);
                    restoreLayers(layerStack.layers, shots);
                    refresh();
                }
            }
            return;
        }
        if (event->key() == Qt::Key_Plus) { zoomIn(); return; }
        if (event->key() == Qt::Key_Minus) { zoomOut(); return; }
        if (event->key() == Qt::Key_0) { zoomFit(); return; }
    }

    if (!(event->modifiers() & Qt::ControlModifier)) {
        QString key = event->text().toLower();
        if (key == "v") { setTool("move"); emit statusChanged("Move Tool"); return; }
        if (key == "b") { setTool("brush"); emit statusChanged("Brush Tool"); return; }
        if (key == "p") { setTool("pencil"); emit statusChanged("Pencil Tool"); return; }
        if (key == "e") { setTool("eraser"); emit statusChanged("Eraser Tool"); return; }
        if (key == "i") { setTool("color_picker"); emit statusChanged("Color Picker"); return; }
        if (key == "g") { setTool("flood_fill"); emit statusChanged("Flood Fill"); return; }
    }

    QGraphicsView::keyPressEvent(event);
}
