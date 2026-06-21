from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QGroupBox, QComboBox, QGridLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication
from editor.i18n import _
from editor.filters import gaussian_blur, sharpen


class BlurSharpenWidget(QWidget):
    paramsChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "blur"
        self._amount = 3
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel(_("Blur / Sharpen"))
        tf = title.font()
        tf.setBold(True)
        tf.setPointSize(11)
        title.setFont(tf)
        layout.addWidget(title)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(_("Mode:")))
        self._mode_cb = QComboBox()
        self._mode_cb.addItems([_("Gaussian Blur"), _("Sharpen")])
        self._mode_cb.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self._mode_cb)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        amt_row = QHBoxLayout()
        amt_row.addWidget(QLabel(_("Amount:")))
        self._amount_slider = QSlider(Qt.Horizontal)
        self._amount_slider.setRange(1, 50)
        self._amount_slider.setValue(3)
        self._amount_label = QLabel("3")
        self._amount_label.setFixedWidth(30)
        self._amount_label.setAlignment(Qt.AlignRight)
        self._amount_slider.valueChanged.connect(self._on_amount_changed)
        amt_row.addWidget(self._amount_slider, 1)
        amt_row.addWidget(self._amount_label)
        layout.addLayout(amt_row)

        info = QLabel(_("Tip: Blur removes noise. Sharpen enhances edges."))
        info.setStyleSheet("color: #666; font-size: 10px; padding-top: 8px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

    def _on_mode_changed(self, idx):
        self._mode = "sharpen" if idx == 1 else "blur"
        self._emit_params()

    def _on_amount_changed(self, val):
        self._amount = val
        self._amount_label.setText(str(val))
        self._emit_params()

    def _emit_params(self):
        self.paramsChanged.emit({
            "mode": self._mode,
            "amount": self._amount,
        })

    def apply_to_image(self, image):
        image = image.convertToFormat(QImage.Format_ARGB32)
        if self._mode == "blur":
            return gaussian_blur(image, radius=max(1, self._amount // 3))
        else:
            return sharpen(image, amount=self._amount / 10.0)
