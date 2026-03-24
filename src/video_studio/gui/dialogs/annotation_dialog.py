"""強調マーク挿入ダイアログ"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from video_studio.core.project import Annotation
from video_studio.core.timeline import format_time, parse_time


class AnnotationDialog(QDialog):
    def __init__(self, source_time: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("強調マーク挿入")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"開始位置: {format_time(source_time)}"))

        # 終了
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("終了位置:"))
        self.end_input = QLineEdit(format_time(source_time + 5))
        self.end_input.setFixedWidth(130)
        row0.addWidget(self.end_input)
        row0.addStretch()
        layout.addLayout(row0)

        # 種類
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("種類:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("丸囲み (cx, cy, r)", "circle")
        self.type_combo.addItem("矢印 (x1, y1, x2, y2)", "arrow")
        self.type_combo.addItem("矩形ハイライト (x, y, w, h)", "rect_highlight")
        row1.addWidget(self.type_combo)
        layout.addLayout(row1)

        # 位置パラメータ
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("位置 (カンマ区切り):"))
        self.pos_input = QLineEdit("500,300,50")
        row2.addWidget(self.pos_input)
        layout.addLayout(row2)

        # 色と太さ
        row3 = QHBoxLayout()
        self._color = "#FF0000"
        self.color_btn = QPushButton("色を選択")
        self.color_btn.setStyleSheet(f"background-color: {self._color}; color: white;")
        self.color_btn.clicked.connect(self._pick_color)
        row3.addWidget(self.color_btn)
        row3.addWidget(QLabel("太さ:"))
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 20)
        self.thickness_spin.setValue(3)
        row3.addWidget(self.thickness_spin)
        row3.addStretch()
        layout.addLayout(row3)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._source_time = source_time

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self)
        if color.isValid():
            self._color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self._color}; color: white;")

    def get_entry(self) -> Annotation | None:
        try:
            end = parse_time(self.end_input.text())
            pos = tuple(int(v.strip()) for v in self.pos_input.text().split(","))
        except (ValueError, TypeError):
            return None
        if end <= self._source_time:
            return None
        return Annotation(
            type=self.type_combo.currentData(),
            position=pos,
            start=self._source_time,
            end=end,
            color=self._color,
            thickness=self.thickness_spin.value(),
        )
