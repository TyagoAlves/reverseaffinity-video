#ifndef LAYERS_H
#define LAYERS_H

#include <QImage>
#include <QString>
#include <QVector>
#include <QColor>

struct Layer {
    QString name;
    QImage image;
    bool visible = true;
    bool locked = false;
    double opacity = 1.0;
    QString blendMode = "normal";

    Layer() = default;
    Layer(int width, int height, const QString &name = "Background");
    Layer copy() const;
};

class LayerStack {
public:
    LayerStack(int width = 800, int height = 600);

    Layer *active();
    const Layer *active() const;
    int activeIndex() const { return activeIndex_; }
    void setActiveIndex(int idx) { activeIndex_ = idx; }

    Layer &addLayer(const QString &name = QString());
    void removeLayer(int index);
    void moveLayer(int from, int to);
    void duplicateLayer(int index);
    void flatten();
    void mergeVisible();

    QImage composite() const;

    QVector<Layer> layers;
    int activeIndex_ = 0;
};

#endif
