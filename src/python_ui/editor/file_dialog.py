import os
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QComboBox,
    QFileDialog, QWidget, QAbstractItemView, QApplication
)

from .i18n import _


class FileDialog(QDialog):
    MODE_OPEN = 0
    MODE_SAVE = 1

    def __init__(self, title="", directory="", filter_str="", mode=MODE_OPEN, parent=None):
        super().__init__(parent)
        self._mode = mode
        self._filter_str = filter_str
        self.selected_path = None

        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a2e; color: #e0e0e0; }
            QLineEdit { background: #0e0e1a; color: #e0e0e0; border: 1px solid #333; padding: 6px; border-radius: 4px; }
            QListWidget { background: #0e0e1a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected { background: #3a8ac4; color: #fff; }
            QPushButton { background: #2a2a3e; color: #e0e0e0; border: 1px solid #444; padding: 6px 16px; border-radius: 4px; }
            QPushButton:hover { background: #3a4a6e; border-color: #5a8ac4; }
            QPushButton:pressed { background: #4a5a7e; }
            QComboBox { background: #0e0e1a; color: #e0e0e0; border: 1px solid #333; padding: 4px; border-radius: 4px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #1a1a2e; color: #e0e0e0; selection-background-color: #3a8ac4; }
            QLabel { color: #aaa; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        nav = QHBoxLayout()
        self._path_edit = QLineEdit(os.path.abspath(directory or os.getcwd()))
        nav.addWidget(self._path_edit)
        go_btn = QPushButton(_("Go"))
        go_btn.clicked.connect(self._navigate)
        nav.addWidget(go_btn)
        up_btn = QPushButton(_("Up"))
        up_btn.clicked.connect(self._go_up)
        nav.addWidget(up_btn)
        layout.addLayout(nav)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._file_list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._file_list)

        bottom = QHBoxLayout()
        self._filter_combo = QComboBox()
        for f in filter_str.split(";;"):
            self._filter_combo.addItem(f.strip())
        bottom.addWidget(QLabel(_("Filter:")))
        bottom.addWidget(self._filter_combo)
        bottom.addStretch()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(_("File name"))
        bottom.addWidget(QLabel(_("File name:")))
        bottom.addWidget(self._name_edit)

        cancel_btn = QPushButton(_("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(cancel_btn)

        self._action_btn = QPushButton(_("Open") if mode == self.MODE_OPEN else _("Save"))
        self._action_btn.setStyleSheet("""
            QPushButton { background: #3a8ac4; color: #fff; font-weight: bold; padding: 6px 20px; }
            QPushButton:hover { background: #4a9ad4; }
        """)
        self._action_btn.clicked.connect(self._accept)
        bottom.addWidget(self._action_btn)

        layout.addLayout(bottom)

        self._filter_combo.currentIndexChanged.connect(self._refresh)
        self._file_list.currentItemChanged.connect(self._on_selection)

        self._refresh()

    def _navigate(self):
        path = self._path_edit.text().strip()
        if os.path.isdir(path):
            self._refresh(path)

    def _go_up(self):
        parent = os.path.dirname(self._path_edit.text())
        if parent:
            self._refresh(parent)

    def _refresh(self, directory=None):
        if directory:
            root = directory
        else:
            root = self._path_edit.text()
        self._path_edit.setText(os.path.abspath(root))
        self._file_list.clear()
        try:
            items = sorted(os.listdir(root))
        except PermissionError:
            return
        for name in items:
            full = os.path.join(root, name)
            if os.path.isdir(full):
                item = QListWidgetItem("[" + name + "]")
                item.setData(Qt.UserRole, full)
                item.setForeground(QColor("#5a8ac4"))
                self._file_list.addItem(item)
        for name in items:
            full = os.path.join(root, name)
            if os.path.isfile(full):
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, full)
                self._file_list.addItem(item)

    def _on_double_click(self, item):
        path = item.data(Qt.UserRole)
        if os.path.isdir(path):
            self._refresh(path)
        else:
            self._name_edit.setText(os.path.basename(path))
            self._accept()

    def _on_selection(self, current, previous):
        if current:
            path = current.data(Qt.UserRole)
            if path and os.path.isfile(path):
                self._name_edit.setText(os.path.basename(path))

    def _accept(self):
        name = self._name_edit.text().strip()
        root = self._path_edit.text().strip()
        if name:
            self.selected_path = os.path.join(root, name)
            self.accept()


def get_open_file_name(title="", directory="", filter_str="", parent=None):
    dlg = FileDialog(title, directory, filter_str, FileDialog.MODE_OPEN, parent)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.selected_path, ""
    return "", ""


def get_save_file_name(title="", directory="", filter_str="", parent=None):
    dlg = FileDialog(title, directory, filter_str, FileDialog.MODE_SAVE, parent)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.selected_path, ""
    return "", ""


def get_open_file_names(title="", directory="", filter_str="", parent=None):
    return QFileDialog.getOpenFileNames(parent, title, directory, filter_str)
