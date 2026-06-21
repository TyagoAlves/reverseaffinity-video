#ifndef APP_UI_H
#define APP_UI_H

#include <QMainWindow>
#include <QLabel>
#include <QComboBox>
#include <QSpinBox>
#include <QPushButton>

class CanvasView;
class ColorPanel;
class ToolPanel;
class LayerPanel;

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override = default;

private slots:
    void newFile();
    void openFile();
    void saveFile();
    void saveAsFile();
    void exportPng();
    void exportJpg();
    void pickColor();
    void showFilters();
    void undo();
    void redo();
    void fillColor();
    void newLayer();
    void dupLayer();
    void mergeVisible();
    void flatten();
    void updateCoords(double x, double y);

private:
    void createMenus();
    void createToolbar();
    void createStatusBar();
    void applyDarkTheme();

    CanvasView *canvas_;
    ColorPanel *colorPanel_;
    ToolPanel *toolPanel_;
    LayerPanel *layerPanel_;
    QComboBox *toolCombo_;
    QComboBox *brushShapeCombo_;
    QSpinBox *sizeSpin_;
    QPushButton *colorBtn_;
    QLabel *coordLabel_;
    QLabel *infoLabel_;
    QString currentPath_;
};

#endif
