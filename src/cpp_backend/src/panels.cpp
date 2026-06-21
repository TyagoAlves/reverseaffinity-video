#include "panels.h"
#include "canvas.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QGridLayout>
#include <QColorDialog>
#include <QCheckBox>
#include <QScrollArea>
#include <QFrame>
#include <QPushButton>

ColorSwatch::ColorSwatch(const QColor &color, QWidget *parent)
    : QPushButton(parent), color_(color)
{
    setFixedSize(32, 32);
    updateStyle();
    connect(this, &QPushButton::clicked, this, [this]() {
        QColor c = QColorDialog::getColor(color_, this);
        if (c.isValid()) {
            setColor(c);
            emit colorPicked(c);
        }
    });
}

void ColorSwatch::setColor(const QColor &c)
{
    color_ = c;
    updateStyle();
}

void ColorSwatch::updateStyle()
{
    setStyleSheet(QString("background-color: %1; border: 2px solid #666; border-radius: 3px;")
                  .arg(color_.name()));
}

ColorPanel::ColorPanel(QWidget *parent)
    : QWidget(parent)
{
    setWindowTitle("Color");
    setMinimumWidth(200);

    auto *layout = new QVBoxLayout(this);
    layout->setContentsMargins(4, 4, 4, 4);

    auto *swatchLayout = new QHBoxLayout();
    swatchLayout->addWidget(new QLabel("FG:"));
    fgSwatch_ = new ColorSwatch(Qt::black);
    swatchLayout->addWidget(fgSwatch_);
    swatchLayout->addWidget(new QLabel("BG:"));
    bgSwatch_ = new ColorSwatch(Qt::white);
    swatchLayout->addWidget(bgSwatch_);

    auto *swapBtn = new QPushButton("<=>");
    swapBtn->setFixedWidth(36);
    connect(swapBtn, &QPushButton::clicked, this, &ColorPanel::swapColors);
    swatchLayout->addWidget(swapBtn);
    layout->addLayout(swatchLayout);

    connect(fgSwatch_, &ColorSwatch::colorPicked, this, [this](const QColor &c) {
        syncSpins(c);
        emit colorChanged(c);
    });

    auto *hslLabel = new QLabel("<b>HSL</b>");
    layout->addWidget(hslLabel);

    auto *grid = new QGridLayout();
    grid->addWidget(new QLabel("H:"), 0, 0);
    hSpin_ = new QSpinBox(); hSpin_->setRange(0, 360);
    connect(hSpin_, QOverload<int>::of(&QSpinBox::valueChanged), this, &ColorPanel::hslChanged);
    grid->addWidget(hSpin_, 0, 1);

    grid->addWidget(new QLabel("S:"), 1, 0);
    sSpin_ = new QSpinBox(); sSpin_->setRange(0, 100);
    connect(sSpin_, QOverload<int>::of(&QSpinBox::valueChanged), this, &ColorPanel::hslChanged);
    grid->addWidget(sSpin_, 1, 1);

    grid->addWidget(new QLabel("L:"), 2, 0);
    lSpin_ = new QSpinBox(); lSpin_->setRange(0, 100);
    connect(lSpin_, QOverload<int>::of(&QSpinBox::valueChanged), this, &ColorPanel::hslChanged);
    grid->addWidget(lSpin_, 2, 1);

    grid->addWidget(new QLabel("R:"), 3, 0);
    rSpin_ = new QSpinBox(); rSpin_->setRange(0, 255);
    connect(rSpin_, QOverload<int>::of(&QSpinBox::valueChanged), this, &ColorPanel::rgbChanged);
    grid->addWidget(rSpin_, 3, 1);

    grid->addWidget(new QLabel("G:"), 4, 0);
    gSpin_ = new QSpinBox(); gSpin_->setRange(0, 255);
    connect(gSpin_, QOverload<int>::of(&QSpinBox::valueChanged), this, &ColorPanel::rgbChanged);
    grid->addWidget(gSpin_, 4, 1);

    grid->addWidget(new QLabel("B:"), 5, 0);
    bSpin_ = new QSpinBox(); bSpin_->setRange(0, 255);
    connect(bSpin_, QOverload<int>::of(&QSpinBox::valueChanged), this, &ColorPanel::rgbChanged);
    grid->addWidget(bSpin_, 5, 1);

    layout->addLayout(grid);
}

void ColorPanel::syncSpins(const QColor &c)
{
    updating_ = true;
    rSpin_->setValue(c.red());
    gSpin_->setValue(c.green());
    bSpin_->setValue(c.blue());
    hSpin_->setValue(qMax(0, c.hue()));
    sSpin_->setValue(c.saturation());
    lSpin_->setValue(c.lightness());
    updating_ = false;
}

void ColorPanel::swapColors()
{
    QColor fg = fgSwatch_->color();
    QColor bg = bgSwatch_->color();
    fgSwatch_->setColor(bg);
    bgSwatch_->setColor(fg);
    syncSpins(bg);
    emit colorChanged(bg);
}

void ColorPanel::hslChanged()
{
    if (updating_) return;
    QColor c;
    c.setHsl(hSpin_->value(), sSpin_->value(), lSpin_->value());
    updating_ = true;
    rSpin_->setValue(c.red());
    gSpin_->setValue(c.green());
    bSpin_->setValue(c.blue());
    updating_ = false;
    fgSwatch_->setColor(c);
    emit colorChanged(c);
}

void ColorPanel::rgbChanged()
{
    if (updating_) return;
    QColor c(rSpin_->value(), gSpin_->value(), bSpin_->value());
    updating_ = true;
    hSpin_->setValue(qMax(0, c.hue()));
    sSpin_->setValue(c.saturation());
    lSpin_->setValue(c.lightness());
    updating_ = false;
    fgSwatch_->setColor(c);
    emit colorChanged(c);
}

ToolButton::ToolButton(const QString &text, const QString &tooltip, QWidget *parent)
    : QPushButton(text, parent)
{
    setToolTip(tooltip);
    setFixedSize(36, 36);
    setFont(QFont("monospace", 10, QFont::Bold));
    setCheckable(true);
}

ToolPanel::ToolPanel(CanvasView *canvas, QWidget *parent)
    : QWidget(parent), canvas_(canvas)
{
    setWindowTitle("Tools");
    setFixedWidth(56);

    auto *layout = new QVBoxLayout(this);
    layout->setContentsMargins(4, 4, 4, 4);
    layout->setSpacing(2);

    struct ToolDef { QString label; QString name; QString tip; };
    QVector<ToolDef> tools = {
        {"V", "move", "Move Tool"},
        {"B", "brush", "Brush Tool"},
        {"P", "pencil", "Pencil Tool"},
        {"E", "eraser", "Eraser Tool"},
        {"I", "color_picker", "Color Picker"},
        {"G", "flood_fill", "Flood Fill"},
    };

    for (auto &t : tools) {
        auto *btn = new ToolButton(t.label, t.tip);
        connect(btn, &QPushButton::clicked, this, [this, name = t.name, btn]() {
            selectTool(name);
            for (auto *b : buttons_) b->setChecked(b == btn);
        });
        layout->addWidget(btn);
        buttons_.append(btn);
    }
    layout->addStretch();

    if (!buttons_.isEmpty()) buttons_[1]->setChecked(true);
}

void ToolPanel::selectTool(const QString &name)
{
    if (canvas_) {
        canvas_->setTool(name);
        emit toolSelected(name);
    }
}

LayerPanel::LayerPanel(CanvasView *canvas, QWidget *parent)
    : QWidget(parent), canvas_(canvas)
{
    setWindowTitle("Layers");
    setMinimumWidth(180);

    auto *mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(4, 4, 4, 4);

    auto *scrollArea = new QScrollArea();
    scrollArea->setWidgetResizable(true);
    scrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    auto *scrollContent = new QWidget();
    listLayout_ = new QVBoxLayout(scrollContent);
    listLayout_->setSpacing(2);
    scrollArea->setWidget(scrollContent);
    mainLayout->addWidget(scrollArea);

    auto *btnLayout = new QHBoxLayout();
    auto *addBtn = new QPushButton("+");
    auto *delBtn = new QPushButton("-");
    addBtn->setFixedWidth(30);
    delBtn->setFixedWidth(30);
    connect(addBtn, &QPushButton::clicked, this, [this]() {
        if (!canvas_) return;
        canvas_->saveState("New layer");
        canvas_->layerStack.addLayer();
        canvas_->refresh();
        refreshLayers();
    });
    connect(delBtn, &QPushButton::clicked, this, [this]() {
        if (!canvas_) return;
        canvas_->saveState("Delete layer");
        canvas_->layerStack.removeLayer(canvas_->layerStack.activeIndex_);
        canvas_->refresh();
        refreshLayers();
    });
    btnLayout->addWidget(addBtn);
    btnLayout->addWidget(delBtn);
    btnLayout->addStretch();
    mainLayout->addLayout(btnLayout);

    refreshLayers();
}

void LayerPanel::refreshLayers()
{
    QLayoutItem *child;
    while ((child = listLayout_->takeAt(0)) != nullptr) {
        delete child->widget();
        delete child;
    }

    if (!canvas_) return;

    for (int i = canvas_->layerStack.layers.size() - 1; i >= 0; --i) {
        auto &layer = canvas_->layerStack.layers[i];

        auto *frame = new QFrame();
        frame->setFrameShape(QFrame::StyledPanel);
        frame->setStyleSheet(canvas_->layerStack.activeIndex_ == i
            ? "QFrame { background: #2a2a3a; border: 1px solid #f97316; border-radius: 4px; }"
            : "QFrame { background: #1a1a2a; border: 1px solid #333; border-radius: 4px; }");

        auto *row = new QHBoxLayout(frame);
        row->setContentsMargins(4, 2, 4, 2);

        auto *visBtn = new QPushButton(layer.visible ? "●" : "○");
        visBtn->setFixedSize(20, 20);
        visBtn->setStyleSheet("border: none; font-size: 10px;");
        connect(visBtn, &QPushButton::clicked, this, [this, i]() {
            if (!canvas_) return;
            canvas_->layerStack.layers[i].visible = !canvas_->layerStack.layers[i].visible;
            canvas_->refresh();
            refreshLayers();
        });
        row->addWidget(visBtn);

        QPixmap thumb = QPixmap::fromImage(
            layer.image.scaled(24, 24, Qt::KeepAspectRatio, Qt::SmoothTransformation));
        auto *thumbLabel = new QLabel();
        thumbLabel->setPixmap(thumb);
        row->addWidget(thumbLabel);

        auto *nameLabel = new QLabel(layer.name);
        nameLabel->setStyleSheet("color: #ccc; font-size: 11px;");
        row->addWidget(nameLabel, 1);

        auto *clickBtn = new QPushButton();
        clickBtn->setStyleSheet("background: transparent; border: none;");
        clickBtn->setFixedSize(1000, 30);
        connect(clickBtn, &QPushButton::clicked, this, [this, i]() {
            if (!canvas_) return;
            canvas_->layerStack.setActiveIndex(i);
            canvas_->refresh();
            refreshLayers();
        });
        clickBtn->setAttribute(Qt::WA_TransparentForMouseEvents, false);

        listLayout_->addWidget(frame);
    }
    listLayout_->addStretch();
}
