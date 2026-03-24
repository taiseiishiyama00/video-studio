"""強調マークパネル

丸囲み・矢印・ハイライト枠を配置する。
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from video_studio.core.project import Annotation, Project
from video_studio.core.timeline import format_time, parse_time

TYPE_LABELS = {
    "circle": "丸囲み (cx, cy, r)",
    "arrow": "矢印 (x1, y1, x2, y2)",
    "rect_highlight": "矩形ハイライト (x, y, w, h)",
}


class AnnotationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("強調マークを配置します。"))

        # 現在時刻
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("現在位置:"))
        self.time_label = QLabel("00:00:00.000")
        self.time_label.setStyleSheet("font-weight: bold; color: #FFD54F;")
        time_row.addWidget(self.time_label)
        time_row.addStretch()
        layout.addLayout(time_row)
        self._current_time = 0.0

        # 種類
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("種類:"))
        self.type_combo = QComboBox()
        for key, label in TYPE_LABELS.items():
            self.type_combo.addItem(label, key)
        row1.addWidget(self.type_combo)
        row1.addStretch()
        layout.addLayout(row1)

        # 位置パラメータ
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("位置 (カンマ区切り):"))
        self.position_input = QLineEdit("500,300,50")
        row2.addWidget(self.position_input)
        layout.addLayout(row2)

        # 時間
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("開始:"))
        self.start_input = QLineEdit("00:00:00")
        self.start_input.setFixedWidth(100)
        row3.addWidget(self.start_input)
        btn_s = QPushButton("現在位置")
        btn_s.setFixedWidth(70)
        btn_s.clicked.connect(lambda: self.start_input.setText(format_time(self._current_time)))
        row3.addWidget(btn_s)
        row3.addWidget(QLabel("終了:"))
        self.end_input = QLineEdit("00:00:05")
        self.end_input.setFixedWidth(100)
        row3.addWidget(self.end_input)
        btn_e = QPushButton("現在位置")
        btn_e.setFixedWidth(70)
        btn_e.clicked.connect(lambda: self.end_input.setText(format_time(self._current_time)))
        row3.addWidget(btn_e)
        row3.addStretch()
        layout.addLayout(row3)

        # 色と太さ
        row4 = QHBoxLayout()
        self._color = "#FF0000"
        self.color_btn = QPushButton("色を選択")
        self.color_btn.setStyleSheet(f"background-color: {self._color}")
        self.color_btn.clicked.connect(self._pick_color)
        row4.addWidget(self.color_btn)

        row4.addWidget(QLabel("太さ:"))
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 20)
        self.thickness_spin.setValue(3)
        row4.addWidget(self.thickness_spin)

        btn_add = QPushButton("追加")
        btn_add.clicked.connect(self._add)
        row4.addWidget(btn_add)
        row4.addStretch()
        layout.addLayout(row4)

        # リスト
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_remove = QPushButton("選択したマークを削除")
        btn_remove.clicked.connect(self._remove)
        layout.addWidget(btn_remove)

        self._annotations: list[Annotation] = []

    def set_current_time(self, sec: float):
        self._current_time = sec
        self.time_label.setText(format_time(sec))

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self)
        if color.isValid():
            self._color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self._color}")

    def _add(self):
        try:
            start = parse_time(self.start_input.text())
            end = parse_time(self.end_input.text())
            pos = tuple(int(v.strip()) for v in self.position_input.text().split(","))
        except (ValueError, TypeError):
            return

        annot_type = self.type_combo.currentData()
        annot = Annotation(
            type=annot_type,
            position=pos,
            start=start,
            end=end,
            color=self._color,
            thickness=self.thickness_spin.value(),
        )
        self._annotations.append(annot)
        self._refresh_list()

    def _remove(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._annotations):
            self._annotations.pop(row)
            self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        type_names = {"circle": "丸囲み", "arrow": "矢印", "rect_highlight": "矩形"}
        for i, a in enumerate(self._annotations):
            name = type_names.get(a.type, a.type)
            self.list_widget.addItem(
                f"{i + 1}. {name} {a.position} {format_time(a.start)}→{format_time(a.end)} {a.color}"
            )

    def load_from_project(self, project: Project):
        self._annotations = list(project.annotations)
        self._refresh_list()

    def apply_to_project(self, project: Project):
        project.annotations = list(self._annotations)
