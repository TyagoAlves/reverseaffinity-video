#include "history.h"

QVector<LayerSnapshot> snapshotFromLayers(const QVector<Layer> &layers)
{
    QVector<LayerSnapshot> shots;
    for (const auto &l : layers) {
        shots.append({l.name, l.image.copy(), l.visible, l.locked, l.opacity, l.blendMode});
    }
    return shots;
}

void restoreLayers(QVector<Layer> &layers, const QVector<LayerSnapshot> &shots)
{
    layers.clear();
    for (const auto &s : shots) {
        Layer l;
        l.name = s.name;
        l.image = s.image;
        l.visible = s.visible;
        l.locked = s.locked;
        l.opacity = s.opacity;
        l.blendMode = s.blendMode;
        layers.append(l);
    }
}

HistoryManager::HistoryManager(int maxStates)
    : maxStates_(maxStates)
{
}

void HistoryManager::push(const QString &description,
                           const QVector<LayerSnapshot> &layers,
                           int activeIndex)
{
    HistoryEntry entry;
    entry.description = description;
    entry.snapshots = layers;
    entry.activeIndex = activeIndex;

    while (index_ < stack_.size() - 1)
        stack_.removeLast();

    stack_.append(entry);
    if (stack_.size() > maxStates_)
        stack_.removeFirst();
    index_ = stack_.size() - 1;
}

bool HistoryManager::undo(QVector<LayerSnapshot> &layers, int &activeIndex)
{
    if (index_ <= 0) return false;
    index_--;
    const auto &entry = stack_[index_];
    layers = entry.snapshots;
    activeIndex = entry.activeIndex;
    return true;
}

bool HistoryManager::redo(QVector<LayerSnapshot> &layers, int &activeIndex)
{
    if (index_ >= stack_.size() - 1) return false;
    index_++;
    const auto &entry = stack_[index_];
    layers = entry.snapshots;
    activeIndex = entry.activeIndex;
    return true;
}

bool HistoryManager::canUndo() const { return index_ > 0; }
bool HistoryManager::canRedo() const { return index_ < stack_.size() - 1; }
void HistoryManager::clear()
{
    stack_.clear();
    index_ = -1;
}
