#include <QApplication>
#include "app_ui.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("reverseaffinity");
    app.setOrganizationName("reverseaffinity");

    MainWindow window;
    window.show();

    return app.exec();
}
