#ifndef PANELS_H
#define PANELS_H

#include <QWidget>
#include <QColor>
#include <QPushButton>
#include <QSpinBox>
#include <QVector>
#include <QVBoxLayout>
#include <QScrollArea>

class CanvasView;

class ColorSwatch : public QPushButton {
    Q_OBJECT
public:
    explicit ColorSwatch(const QColor &color = Qt::black, QWidget *parent = nullptr);
    QColor color() const { return color_; }
    void setColor(const QColor &c);

signals:
    void colorPicked(const QColor &c);

private:
    void updateStyle();
    QColor color_;
};

class ColorPanel : public QWidget {
    Q_OBJECT
public:
    explicit ColorPanel(QWidget *parent = nullptr);
    ColorSwatch *fgSwatch() { return fgSwatch_; }
    ColorSwatch *bgSwatch() { return bgSwatch_; }

signals:
    void colorChanged(const QColor &c);
    void bgColorChanged(const QColor &c);

public slots:
    void syncSpins(const QColor &c);

private slots:
    void swapColors();
    void hslChanged();
    void rgbChanged();

private:
    ColorSwatch *fgSwatch_;
    ColorSwatch *bgSwatch_;
    QSpinBox *hSpin_, *sSpin_, *lSpin_;
    QSpinBox *rSpin_, *gSpin_, *bSpin_;
    bool updating_ = false;
};

class ToolButton : public QPushButton {
    Q_OBJECT
public:
    ToolButton(const QString &text, const QString &tooltip, QWidget *parent = nullptr);
};

class ToolPanel : public QWidget {
    Q_OBJECT
public:
    explicit ToolPanel(CanvasView *canvas, QWidget *parent = nullptr);

signals:
    void toolSelected(const QString &toolName);

private:
    void selectTool(const QString &name);
    QVector<ToolButton*> buttons_;
    CanvasView *canvas_;
};

class LayerPanel : public QWidget {
    Q_OBJECT
public:
    explicit LayerPanel(CanvasView *canvas, QWidget *parent = nullptr);

public slots:
    void refreshLayers();

private:
    CanvasView *canvas_;
    QVBoxLayout *listLayout_;
};

#endif
