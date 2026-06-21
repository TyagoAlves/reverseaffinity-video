#ifndef HISTORY_H
#define HISTORY_H

#include <QVector>
#include <QImage>
#include <QString>
#include <QPointF>
#include "layers.h"

struct LayerSnapshot {
    QString name;
    QImage image;
    bool visible;
    bool locked;
    double opacity;
    QString blendMode;
};

struct HistoryEntry {
    QString description;
    QVector<LayerSnapshot> snapshots;
    int activeIndex;
};

class HistoryManager {
public:
    explicit HistoryManager(int maxStates = 50);

    void push(const QString &description,
              const QVector<LayerSnapshot> &layers,
              int activeIndex);

    bool undo(QVector<LayerSnapshot> &layers, int &activeIndex);
    bool redo(QVector<LayerSnapshot> &layers, int &activeIndex);
    bool canUndo() const;
    bool canRedo() const;
    void clear();

private:
    QVector<HistoryEntry> stack_;
    int index_ = -1;
    int maxStates_;
};

// Free helper functions for layer snapshot/restore
QVector<LayerSnapshot> snapshotFromLayers(const QVector<Layer> &layers);
void restoreLayers(QVector<Layer> &layers, const QVector<LayerSnapshot> &shots);

#endif
