#ifndef FILTERS_H
#define FILTERS_H

#include <QImage>

namespace filters {

QImage grayscale(const QImage &img);
QImage invert(const QImage &img);
QImage brightness(const QImage &img, int value);
QImage contrast(const QImage &img, double factor);
QImage levels(const QImage &img, int shadow, double mid, int highlight);
QImage gaussianBlur(const QImage &img, int radius);
QImage sharpen(const QImage &img, double amount = 1.0);
QImage edgeDetect(const QImage &img);
QImage pixelate(const QImage &img, int blockSize = 8);
QImage posterize(const QImage &img, int levels = 4);
QImage sepia(const QImage &img);

} // namespace filters

#endif
