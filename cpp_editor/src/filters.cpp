#include "filters.h"
#include <cmath>
#include <algorithm>
#include <QPainter>

namespace filters {

static inline int clamp(int v, int lo, int hi) {
    return std::max(lo, std::min(hi, v));
}

QImage grayscale(const QImage &img)
{
    QImage result = img.copy();
    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            QColor c = result.pixelColor(x, y);
            int g = qRound(0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue());
            c.setRgb(g, g, g, c.alpha());
            result.setPixelColor(x, y, c);
        }
    }
    return result;
}

QImage invert(const QImage &img)
{
    QImage result = img.copy();
    result.invertPixels();
    return result;
}

QImage brightness(const QImage &img, int value)
{
    QImage result = img.copy();
    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            QColor c = result.pixelColor(x, y);
            c.setRgb(clamp(c.red() + value, 0, 255),
                     clamp(c.green() + value, 0, 255),
                     clamp(c.blue() + value, 0, 255),
                     c.alpha());
            result.setPixelColor(x, y, c);
        }
    }
    return result;
}

QImage contrast(const QImage &img, double factor)
{
    QImage result = img.copy();
    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            QColor c = result.pixelColor(x, y);
            c.setRgb(clamp(qRound(128 + (c.red() - 128) * factor), 0, 255),
                     clamp(qRound(128 + (c.green() - 128) * factor), 0, 255),
                     clamp(qRound(128 + (c.blue() - 128) * factor), 0, 255),
                     c.alpha());
            result.setPixelColor(x, y, c);
        }
    }
    return result;
}

QImage levels(const QImage &img, int shadow, double mid, int highlight)
{
    QImage result = img.copy();
    double diff = highlight - shadow;
    if (diff < 1.0) diff = 1.0;
    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            QColor c = result.pixelColor(x, y);
            int r = clamp(qRound(std::pow((c.red() - shadow) / diff, mid) * 255), 0, 255);
            int g = clamp(qRound(std::pow((c.green() - shadow) / diff, mid) * 255), 0, 255);
            int b = clamp(qRound(std::pow((c.blue() - shadow) / diff, mid) * 255), 0, 255);
            c.setRgb(r, g, b, c.alpha());
            result.setPixelColor(x, y, c);
        }
    }
    return result;
}

QImage gaussianBlur(const QImage &img, int radius)
{
    if (radius < 1) return img.copy();
    int k = radius * 2 + 1;
    QImage result = img.copy();
    QImage temp = img.copy();

    for (int pass = 0; pass < 3; ++pass) {
        for (int y = 0; y < result.height(); ++y) {
            for (int x = 0; x < result.width(); ++x) {
                int ar = 0, ag = 0, ab = 0, aa = 0, count = 0;
                for (int dy = -radius; dy <= radius; ++dy) {
                    for (int dx = -radius; dx <= radius; ++dx) {
                        int sx = clamp(x + dx, 0, result.width() - 1);
                        int sy = clamp(y + dy, 0, result.height() - 1);
                        QColor c = temp.pixelColor(sx, sy);
                        ar += c.red(); ag += c.green(); ab += c.blue(); aa += c.alpha();
                        ++count;
                    }
                }
                if (count > 0) {
                    result.setPixelColor(x, y, QColor(ar / count, ag / count, ab / count, aa / count));
                }
            }
        }
        if (pass < 2) temp = result;
    }
    return result;
}

QImage sharpen(const QImage &img, double amount)
{
    QImage result = img.copy();
    QImage blurred = gaussianBlur(img, 1);

    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            QColor orig = img.pixelColor(x, y);
            QColor blur = blurred.pixelColor(x, y);
            int r = clamp(qRound(orig.red() + (orig.red() - blur.red()) * amount), 0, 255);
            int g = clamp(qRound(orig.green() + (orig.green() - blur.green()) * amount), 0, 255);
            int b = clamp(qRound(orig.blue() + (orig.blue() - blur.blue()) * amount), 0, 255);
            result.setPixelColor(x, y, QColor(r, g, b, orig.alpha()));
        }
    }
    return result;
}

QImage edgeDetect(const QImage &img)
{
    QImage result = img.copy();
    int kx[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    int ky[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};

    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            int gx = 0, gy = 0;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int sx = clamp(x + dx, 0, result.width() - 1);
                    int sy = clamp(y + dy, 0, result.height() - 1);
                    int gray = qGray(img.pixelColor(sx, sy).rgb());
                    gx += gray * kx[dy + 1][dx + 1];
                    gy += gray * ky[dy + 1][dx + 1];
                }
            }
            int mag = clamp(qRound(std::sqrt(gx * gx + gy * gy)), 0, 255);
            result.setPixelColor(x, y, QColor(mag, mag, mag));
        }
    }
    return result;
}

QImage pixelate(const QImage &img, int blockSize)
{
    QImage result = img.copy();
    int bs = std::max(2, blockSize);
    for (int y = 0; y < result.height(); y += bs) {
        for (int x = 0; x < result.width(); x += bs) {
            int ar = 0, ag = 0, ab = 0, aa = 0, count = 0;
            int mx = std::min(x + bs, result.width());
            int my = std::min(y + bs, result.height());
            for (int dy = y; dy < my; ++dy) {
                for (int dx = x; dx < mx; ++dx) {
                    QColor c = img.pixelColor(dx, dy);
                    ar += c.red(); ag += c.green(); ab += c.blue(); aa += c.alpha();
                    ++count;
                }
            }
            if (count > 0) {
                QColor avg(ar / count, ag / count, ab / count, aa / count);
                for (int dy = y; dy < my; ++dy)
                    for (int dx = x; dx < mx; ++dx)
                        result.setPixelColor(dx, dy, avg);
            }
        }
    }
    return result;
}

QImage posterize(const QImage &img, int levels)
{
    QImage result = img.copy();
    int factor = 256 / levels;
    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            QColor c = result.pixelColor(x, y);
            c.setRgb((c.red() / factor) * factor,
                     (c.green() / factor) * factor,
                     (c.blue() / factor) * factor,
                     c.alpha());
            result.setPixelColor(x, y, c);
        }
    }
    return result;
}

QImage sepia(const QImage &img)
{
    QImage result = img.copy();
    for (int y = 0; y < result.height(); ++y) {
        for (int x = 0; x < result.width(); ++x) {
            QColor c = img.pixelColor(x, y);
            int r = clamp(qRound(c.red() * 0.393 + c.green() * 0.769 + c.blue() * 0.189), 0, 255);
            int g = clamp(qRound(c.red() * 0.349 + c.green() * 0.686 + c.blue() * 0.168), 0, 255);
            int b = clamp(qRound(c.red() * 0.272 + c.green() * 0.534 + c.blue() * 0.131), 0, 255);
            c.setRgb(r, g, b, c.alpha());
            result.setPixelColor(x, y, c);
        }
    }
    return result;
}

} // namespace filters
