#include "app_ui.h"
#include "canvas.h"
#include "panels.h"
#include "filters.h"

#include <functional>
#include <initializer_list>
#include <QMenuBar>
#include <QToolBar>
#include <QStatusBar>
#include <QFileDialog>
#include <QColorDialog>
#include <QInputDialog>
#include <QMessageBox>
#include <QAction>
#include <QDockWidget>
#include <QSlider>
#include <QDoubleSpinBox>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPushButton>
#include <QLabel>
#include <QKeySequence>

class FilterDialog : public QWidget {
public:
    explicit FilterDialog(CanvasView *canvas, QWidget *parent = nullptr)
        : QWidget(parent, Qt::Window), canvas_(canvas)
    {
        setWindowTitle("Filters");
        resize(220, 400);

        auto *layout = new QVBoxLayout(this);

        auto addGroup = [&](const QString &title, std::initializer_list<QPair<QString, std::function<void()>>> items) {
            layout->addWidget(new QLabel("<b>" + title + "</b>"));
            for (auto &[name, cb] : items) {
                auto *btn = new QPushButton(name);
                connect(btn, &QPushButton::clicked, this, cb);
                layout->addWidget(btn);
            }
        };

        auto apply = [this](std::function<QImage(const QImage&)> func) {
            auto layer = canvas_->layerStack.active();
            if (!layer) return;
            layer->image = func(layer->image);
            canvas_->refresh();
            canvas_->saveState("Filter");
        };

        auto applyInt = [this, apply](std::function<QImage(const QImage&, int)> func, const QString &title, int def, int min, int max) {
            bool ok;
            int val = QInputDialog::getInt(this, title, "Value:", def, min, max, 1, &ok);
            if (ok) apply([func, val](const QImage &img) { return func(img, val); });
        };

        auto applyDouble = [this, apply](std::function<QImage(const QImage&, double)> func, const QString &title, double def, double min, double max) {
            bool ok;
            double val = QInputDialog::getDouble(this, title, "Value:", def, min, max, 1, &ok);
            if (ok) apply([func, val](const QImage &img) { return func(img, val); });
        };

        addGroup("Adjustments", {
            {"Brightness / Contrast", [this]() { showBrightnessContrast(); }},
            {"Levels", [this]() { showLevels(); }},
        });

        addGroup("Filters", {
            {"Grayscale", [apply]() { apply(filters::grayscale); }},
            {"Invert", [apply]() { apply(filters::invert); }},
            {"Sepia", [apply]() { apply(filters::sepia); }},
            {"Posterize", [applyInt]() { applyInt(filters::posterize, "Posterize", 4, 2, 64); }},
        });

        addGroup("Blur & Sharpen", {
            {"Gaussian Blur", [applyInt]() { applyInt(filters::gaussianBlur, "Blur Radius", 3, 1, 50); }},
            {"Sharpen", [applyDouble]() { applyDouble(filters::sharpen, "Sharpen Amount", 1.0, 0.1, 5.0); }},
            {"Edge Detect", [apply]() { apply(filters::edgeDetect); }},
        });

        addGroup("Pixelate", {
            {"Pixelate", [applyInt]() { applyInt(filters::pixelate, "Block Size", 8, 2, 100); }},
        });
    }

private:
    void showBrightnessContrast()
    {
        auto *dialog = new QWidget(this, Qt::Window);
        dialog->setWindowTitle("Brightness / Contrast");
        dialog->resize(300, 120);
        auto *layout = new QVBoxLayout(dialog);

        auto *bl = new QHBoxLayout();
        bl->addWidget(new QLabel("Brightness:"));
        auto *bs = new QSlider(Qt::Horizontal);
        bs->setRange(-255, 255);
        bl->addWidget(bs);
        layout->addLayout(bl);

        auto *cl = new QHBoxLayout();
        cl->addWidget(new QLabel("Contrast:"));
        auto *cs = new QSlider(Qt::Horizontal);
        cs->setRange(0, 300);
        cs->setValue(100);
        cl->addWidget(cs);
        layout->addLayout(cl);

        auto *btn = new QPushButton("Apply");
        connect(btn, &QPushButton::clicked, this, [this, bs, cs]() {
            auto layer = canvas_->layerStack.active();
            if (!layer) return;
            layer->image = filters::brightness(layer->image, bs->value());
            layer->image = filters::contrast(layer->image, cs->value() / 100.0);
            canvas_->refresh();
            canvas_->saveState("Brightness/Contrast");
        });
        dialog->show();
    }

    void showLevels()
    {
        auto *dialog = new QWidget(this, Qt::Window);
        dialog->setWindowTitle("Levels");
        dialog->resize(300, 140);
        auto *layout = new QVBoxLayout(dialog);

        auto *sll = new QHBoxLayout();
        sll->addWidget(new QLabel("Shadow:"));
        auto *ss = new QSlider(Qt::Horizontal);
        ss->setRange(0, 255);
        sll->addWidget(ss);
        layout->addLayout(sll);

        auto *mll = new QHBoxLayout();
        mll->addWidget(new QLabel("Mid:"));
        auto *ms = new QDoubleSpinBox();
        ms->setRange(0.1, 9.9);
        ms->setValue(1.0);
        ms->setSingleStep(0.1);
        mll->addWidget(ms);
        layout->addLayout(mll);

        auto *hll = new QHBoxLayout();
        hll->addWidget(new QLabel("Highlight:"));
        auto *hs = new QSlider(Qt::Horizontal);
        hs->setRange(0, 255);
        hs->setValue(255);
        hll->addWidget(hs);
        layout->addLayout(hll);

        auto *btn = new QPushButton("Apply");
        connect(btn, &QPushButton::clicked, this, [this, ss, ms, hs]() {
            auto layer = canvas_->layerStack.active();
            if (!layer) return;
            layer->image = filters::levels(layer->image, ss->value(), ms->value(), hs->value());
            canvas_->refresh();
            canvas_->saveState("Levels");
        });
        layout->addWidget(btn);
        dialog->show();
    }

    CanvasView *canvas_;
};


MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    setWindowTitle("reverseaffinity");
    resize(1280, 800);

    applyDarkTheme();

    canvas_ = new CanvasView(this);
    setCentralWidget(canvas_);

    colorPanel_ = new ColorPanel();
    connect(colorPanel_, &ColorPanel::colorChanged, canvas_, &CanvasView::setForegroundColor);
    connect(colorPanel_, &ColorPanel::bgColorChanged, canvas_, &CanvasView::setBackgroundColor);

    toolPanel_ = new ToolPanel(canvas_);

    layerPanel_ = new LayerPanel(canvas_);

    auto *colorDock = new QDockWidget("Color", this);
    colorDock->setWidget(colorPanel_);
    addDockWidget(Qt::RightDockWidgetArea, colorDock);

    auto *layerDock = new QDockWidget("Layers", this);
    layerDock->setWidget(layerPanel_);
    addDockWidget(Qt::RightDockWidgetArea, layerDock);

    auto *toolDock = new QDockWidget("Tools", this);
    toolDock->setWidget(toolPanel_);
    addDockWidget(Qt::LeftDockWidgetArea, toolDock);

    createMenus();
    createToolbar();
    createStatusBar();

    connect(canvas_, &CanvasView::statusChanged, this, [this](const QString &msg) {
        statusBar()->showMessage(msg);
    });

    connect(canvas_, &CanvasView::mouseMoved, this, &MainWindow::updateCoords);


}

void MainWindow::applyDarkTheme()
{
    setStyleSheet(R"(
        QMainWindow, QWidget { background-color: #1a1a2e; color: #e0e0e0; }
        QMenuBar { background-color: #16162a; color: #ccc; border-bottom: 1px solid #333; }
        QMenuBar::item:selected { background: #2a2a4a; }
        QMenu { background-color: #1a1a2e; color: #ccc; border: 1px solid #333; }
        QMenu::item:selected { background-color: #f97316; color: #fff; }
        QToolBar { background-color: #16162a; border-bottom: 1px solid #333; spacing: 6px; padding: 2px; }
        QDockWidget { background-color: #1a1a2e; color: #ccc; }
        QDockWidget::title { background-color: #16162a; padding: 6px; border-bottom: 1px solid #333; }
        QStatusBar { background-color: #16162a; border-top: 1px solid #333; color: #888; }
        QComboBox { background: #2a2a3e; color: #e0e0e0; border: 1px solid #555; padding: 4px; border-radius: 3px; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background: #2a2a3e; color: #e0e0e0; selection-background-color: #f97316; }
        QSpinBox { background: #2a2a3e; color: #e0e0e0; border: 1px solid #555; border-radius: 3px; padding: 2px; }
        QPushButton { background: #2a2a3e; color: #e0e0e0; border: 1px solid #555; border-radius: 4px; padding: 4px 8px; }
        QPushButton:hover { background: #3a3a5e; border-color: #f97316; }
        QPushButton:checked { background: #f97316; color: #fff; border-color: #f97316; }
        QScrollBar:vertical { background: #1a1a2e; width: 8px; }
        QScrollBar::handle:vertical { background: #444; border-radius: 4px; min-height: 20px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QLabel { color: #ccc; }
        QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; }
        QSlider::handle:horizontal { background: #f97316; width: 12px; border-radius: 6px; margin: -4px 0; }
        QFrame { border: none; }
    )");
}

void MainWindow::createMenus()
{
    auto *fileMenu = menuBar()->addMenu("&File");

    auto *newAct = fileMenu->addAction("&New...", this, &MainWindow::newFile, QKeySequence::New);
    auto *openAct = fileMenu->addAction("&Open...", this, &MainWindow::openFile, QKeySequence::Open);
    fileMenu->addSeparator();
    auto *saveAct = fileMenu->addAction("&Save", this, &MainWindow::saveFile, QKeySequence::Save);
    auto *saveAsAct = fileMenu->addAction("Save &As...", this, &MainWindow::saveAsFile, QKeySequence("Ctrl+Shift+S"));

    auto *exportMenu = fileMenu->addMenu("Export");
    exportMenu->addAction("Export as &PNG...", this, &MainWindow::exportPng);
    exportMenu->addAction("Export as &JPEG...", this, &MainWindow::exportJpg);

    fileMenu->addSeparator();
    fileMenu->addAction("E&xit", this, &QWidget::close, QKeySequence("Ctrl+Q"));

    auto *editMenu = menuBar()->addMenu("&Edit");
    editMenu->addAction("&Undo", this, &MainWindow::undo, QKeySequence::Undo);
    editMenu->addAction("&Redo", this, &MainWindow::redo, QKeySequence("Ctrl+Shift+Z"));
    editMenu->addSeparator();
    editMenu->addAction("Fill with &Color...", this, &MainWindow::fillColor);

    auto *layerMenu = menuBar()->addMenu("&Layer");
    layerMenu->addAction("&New Layer", this, &MainWindow::newLayer, QKeySequence("Ctrl+Shift+N"));
    layerMenu->addAction("&Duplicate Layer", this, &MainWindow::dupLayer);
    layerMenu->addSeparator();
    layerMenu->addAction("Merge &Visible", this, &MainWindow::mergeVisible);
    layerMenu->addAction("&Flatten Image", this, &MainWindow::flatten);

    auto *filterMenu = menuBar()->addMenu("F&ilter");
    filterMenu->addAction("&Filter Gallery...", this, &MainWindow::showFilters);

    auto *viewMenu = menuBar()->addMenu("&View");
    viewMenu->addAction("Zoom &In", canvas_, &CanvasView::zoomIn, QKeySequence("Ctrl++"));
    viewMenu->addAction("Zoom &Out", canvas_, &CanvasView::zoomOut, QKeySequence("Ctrl+-"));
    viewMenu->addAction("Zoom to &100%", canvas_, &CanvasView::zoom100, QKeySequence("Ctrl+1"));
    viewMenu->addAction("&Fit to Screen", canvas_, &CanvasView::zoomFit, QKeySequence("Ctrl+0"));
}

void MainWindow::createToolbar()
{
    auto *toolbar = addToolBar("Tools");
    toolbar->setMovable(false);

    toolbar->addWidget(new QLabel("Size:"));
    sizeSpin_ = new QSpinBox();
    sizeSpin_->setRange(1, 500);
    sizeSpin_->setValue(3);
    connect(sizeSpin_, QOverload<int>::of(&QSpinBox::valueChanged), canvas_, &CanvasView::setToolSize);
    toolbar->addWidget(sizeSpin_);

    toolbar->addSeparator();

    toolbar->addWidget(new QLabel("Brush:"));
    brushShapeCombo_ = new QComboBox();
    brushShapeCombo_->addItems({"Round", "Square"});
    connect(brushShapeCombo_, &QComboBox::currentTextChanged, canvas_, &CanvasView::setBrushShape);
    toolbar->addWidget(brushShapeCombo_);

    toolbar->addSeparator();

    colorBtn_ = new QPushButton();
    colorBtn_->setFixedSize(28, 28);
    colorBtn_->setStyleSheet("background-color: #000000; border: 1px solid #888; border-radius: 3px;");
    connect(colorBtn_, &QPushButton::clicked, this, &MainWindow::pickColor);
    toolbar->addWidget(new QLabel("Color:"));
    toolbar->addWidget(colorBtn_);
}

void MainWindow::createStatusBar()
{
    statusBar()->showMessage("Ready");
    coordLabel_ = new QLabel("X: 0  Y: 0");
    infoLabel_ = new QLabel("");
    statusBar()->addPermanentWidget(coordLabel_);
    statusBar()->addPermanentWidget(infoLabel_);
}

void MainWindow::updateCoords(double x, double y)
{
    coordLabel_->setText(QString("X: %1  Y: %2").arg((int)x).arg((int)y));
    QColor c = canvas_->getPixelColor(QPointF(x, y));
    if (c.isValid())
        infoLabel_->setText(QString("R:%1 G:%2 B:%3").arg(c.red()).arg(c.green()).arg(c.blue()));
}

void MainWindow::newFile()
{
    bool ok1, ok2;
    int w = QInputDialog::getInt(this, "New Image", "Width:", 800, 1, 10000, 1, &ok1);
    if (!ok1) return;
    int h = QInputDialog::getInt(this, "New Image", "Height:", 600, 1, 10000, 1, &ok2);
    if (!ok2) return;
    canvas_->newImage(w, h);
    currentPath_.clear();
    layerPanel_->refreshLayers();
}

void MainWindow::openFile()
{
    QString path = QFileDialog::getOpenFileName(this, "Open Image", {},
        "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;All Files (*)");
    if (!path.isEmpty() && canvas_->openImage(path)) {
        currentPath_ = path;
        statusBar()->showMessage("Opened: " + path);
        layerPanel_->refreshLayers();
    }
}

void MainWindow::saveFile()
{
    if (!currentPath_.isEmpty()) {
        canvas_->saveImage(currentPath_);
        statusBar()->showMessage("Saved: " + currentPath_);
    } else {
        saveAsFile();
    }
}

void MainWindow::saveAsFile()
{
    QString path = QFileDialog::getSaveFileName(this, "Save Image", {},
        "PNG (*.png);;JPEG (*.jpg *.jpeg);;TIFF (*.tiff);;WebP (*.webp);;BMP (*.bmp)");
    if (!path.isEmpty()) {
        canvas_->saveImage(path);
        currentPath_ = path;
        statusBar()->showMessage("Saved: " + path);
    }
}

void MainWindow::exportPng()
{
    QString path = QFileDialog::getSaveFileName(this, "Export as PNG", {}, "PNG (*.png)");
    if (!path.isEmpty()) canvas_->exportPng(path);
}

void MainWindow::exportJpg()
{
    QString path = QFileDialog::getSaveFileName(this, "Export as JPEG", {}, "JPEG (*.jpg *.jpeg)");
    if (!path.isEmpty()) canvas_->saveImage(path);
}

void MainWindow::pickColor()
{
    QColor color = QColorDialog::getColor(canvas_->toolColor_, this);
    if (color.isValid()) {
        canvas_->setForegroundColor(color);
        colorBtn_->setStyleSheet(QString("background-color: %1; border: 1px solid #888; border-radius: 3px;").arg(color.name()));
        colorPanel_->fgSwatch()->setColor(color);
        colorPanel_->syncSpins(color);
    }
}

void MainWindow::showFilters()
{
    auto *dialog = new FilterDialog(canvas_, this);
    dialog->show();
}

void MainWindow::undo()
{
    if (canvas_->history.canUndo()) {
        auto shots = snapshotFromLayers(canvas_->layerStack.layers);
        canvas_->history.undo(shots, canvas_->layerStack.activeIndex_);
        restoreLayers(canvas_->layerStack.layers, shots);
        canvas_->refresh();
        layerPanel_->refreshLayers();
    }
}

void MainWindow::redo()
{
    if (canvas_->history.canRedo()) {
        auto shots = snapshotFromLayers(canvas_->layerStack.layers);
        canvas_->history.redo(shots, canvas_->layerStack.activeIndex_);
        restoreLayers(canvas_->layerStack.layers, shots);
        canvas_->refresh();
        layerPanel_->refreshLayers();
    }
}

void MainWindow::fillColor()
{
    auto *layer = canvas_->layerStack.active();
    if (!layer || layer->locked) return;
    QColor color = QColorDialog::getColor(canvas_->toolColor_, this);
    if (color.isValid()) {
        canvas_->saveState("Fill color");
        layer->image.fill(color);
        canvas_->refresh();
    }
}

void MainWindow::newLayer()
{
    canvas_->saveState("New layer");
    canvas_->layerStack.addLayer();
    canvas_->refresh();
    layerPanel_->refreshLayers();
}

void MainWindow::dupLayer()
{
    int idx = canvas_->layerStack.activeIndex();
    canvas_->saveState("Duplicate layer");
    canvas_->layerStack.duplicateLayer(idx);
    canvas_->refresh();
    layerPanel_->refreshLayers();
}

void MainWindow::mergeVisible()
{
    canvas_->saveState("Merge visible");
    canvas_->layerStack.mergeVisible();
    canvas_->refresh();
    layerPanel_->refreshLayers();
}

void MainWindow::flatten()
{
    canvas_->saveState("Flatten");
    canvas_->layerStack.flatten();
    canvas_->refresh();
    layerPanel_->refreshLayers();
}
