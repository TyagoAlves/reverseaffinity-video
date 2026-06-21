#include "layers.h"
#include <QPainter>

Layer::Layer(int width, int height, const QString &name)
    : name(name)
    , image(width, height, QImage::Format_ARGB32)
{
    image.fill(name == "Background" ? Qt::white : Qt::transparent);
}

Layer Layer::copy() const
{
    Layer l;
    l.name = name;
    l.image = image.copy();
    l.visible = visible;
    l.locked = locked;
    l.opacity = opacity;
    l.blendMode = blendMode;
    return l;
}

LayerStack::LayerStack(int width, int height)
{
    layers.append(Layer(width, height, "Background"));
}

Layer *LayerStack::active()
{
    if (activeIndex_ >= 0 && activeIndex_ < layers.size())
        return &layers[activeIndex_];
    return nullptr;
}

const Layer *LayerStack::active() const
{
    if (activeIndex_ >= 0 && activeIndex_ < layers.size())
        return &layers[activeIndex_];
    return nullptr;
}

Layer &LayerStack::addLayer(const QString &name)
{
    int w = layers[0].image.width();
    int h = layers[0].image.height();
    layers.append(Layer(w, h, name.isEmpty() ? QString("Layer %1").arg(layers.size()) : name));
    activeIndex_ = layers.size() - 1;
    return layers.last();
}

void LayerStack::removeLayer(int index)
{
    if (layers.size() <= 1) return;
    if (index >= 0 && index < layers.size()) {
        layers.removeAt(index);
        if (activeIndex_ >= layers.size())
            activeIndex_ = layers.size() - 1;
    }
}

void LayerStack::moveLayer(int from, int to)
{
    if (from < 0 || from >= layers.size() || to < 0 || to >= layers.size())
        return;
    layers.move(from, to);
    activeIndex_ = to;
}

void LayerStack::duplicateLayer(int index)
{
    if (index < 0 || index >= layers.size()) return;
    Layer dup = layers[index].copy();
    dup.name += " (copy)";
    layers.insert(index + 1, dup);
    activeIndex_ = index + 1;
}

void LayerStack::flatten()
{
    if (layers.size() == 1) return;
    QImage base = composite();
    layers.clear();
    layers.append(Layer(base.width(), base.height(), "Flattened"));
    layers[0].image = base;
    activeIndex_ = 0;
}

void LayerStack::mergeVisible()
{
    QVector<Layer> visible;
    for (const auto &l : layers) {
        if (l.visible) visible.append(l);
    }
    if (visible.isEmpty()) return;

    QImage base = composite();
    for (auto &l : layers) {
        if (l.visible) {
            l.image = base.copy();
            l.name = "Merged";
            break;
        }
    }
}

QImage LayerStack::composite() const
{
    if (layers.isEmpty()) return QImage();

    QImage result(layers[0].image.size(), QImage::Format_ARGB32);
    result.fill(Qt::transparent);
    QPainter painter(&result);

    for (const auto &layer : layers) {
        if (!layer.visible) continue;
        painter.setOpacity(layer.opacity);
        painter.drawImage(0, 0, layer.image);
    }
    painter.end();
    return result;
}
