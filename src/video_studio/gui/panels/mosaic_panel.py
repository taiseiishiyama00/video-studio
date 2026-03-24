"""モザイクパネル

画面上の矩形領域を手動指定し、時間範囲を設定してモザイクを適用。
"""

from __future__ import annotations

from PySide6.QtWidgets import (
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

from video_studio.core.project import MosaicRegion, Project
from video_studio.core.timeline import format_time, parse_time


class MosaicPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("矩形領域 (x, y, 幅, 高さ) と時間範囲を指定してください。"))

        # 現在時刻
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("現在位置:"))
        self.time_label = QLabel("00:00:00.000")
        self.time_label.setStyleSheet("font-weight: bold; color: #FFD54F;")
        time_row.addWidget(self.time_label)
        time_row.addStretch()
        layout.addLayout(time_row)
        self._current_time = 0.0

        # 領域
        row1 = QHBoxLayout()
        for label_text, attr in [("X:", "spin_x"), ("Y:", "spin_y"), ("幅:", "spin_w"), ("高:", "spin_h")]:
            row1.addWidget(QLabel(label_text))
            spin = QSpinBox()
            spin.setRange(0, 9999)
            spin.setValue(100 if "w" in attr or "h" in attr else 0)
            setattr(self, attr, spin)
            row1.addWidget(spin)
        layout.addLayout(row1)

        # 時間
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("開始:"))
        self.start_input = QLineEdit("00:00:00")
        self.start_input.setFixedWidth(100)
        row2.addWidget(self.start_input)
        btn_s = QPushButton("現在位置")
        btn_s.setFixedWidth(70)
        btn_s.clicked.connect(lambda: self.start_input.setText(format_time(self._current_time)))
        row2.addWidget(btn_s)
        row2.addWidget(QLabel("終了:"))
        self.end_input = QLineEdit("00:00:10")
        self.end_input.setFixedWidth(100)
        row2.addWidget(self.end_input)
        btn_e = QPushButton("現在位置")
        btn_e.setFixedWidth(70)
        btn_e.clicked.connect(lambda: self.end_input.setText(format_time(self._current_time)))
        row2.addWidget(btn_e)
        row2.addStretch()
        layout.addLayout(row2)

        # モード
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("モード:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["pixelate", "blur"])
        row3.addWidget(self.mode_combo)

        row3.addWidget(QLabel("強度:"))
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 50)
        self.strength_spin.setValue(20)
        row3.addWidget(self.strength_spin)

        btn_add = QPushButton("追加")
        btn_add.clicked.connect(self._add)
        row3.addWidget(btn_add)
        row3.addStretch()
        layout.addLayout(row3)

        # リスト
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_remove = QPushButton("選択したモザイクを削除")
        btn_remove.clicked.connect(self._remove)
        layout.addWidget(btn_remove)

        self._regions: list[MosaicRegion] = []

    def set_current_time(self, sec: float):
        self._current_time = sec
        self.time_label.setText(format_time(sec))

    def _add(self):
        try:
            start = parse_time(self.start_input.text())
            end = parse_time(self.end_input.text())
        except ValueError:
            return

        region = MosaicRegion(
            rect=(self.spin_x.value(), self.spin_y.value(),
                  self.spin_w.value(), self.spin_h.value()),
            start=start,
            end=end,
            mode=self.mode_combo.currentText(),
            strength=self.strength_spin.value(),
        )
        self._regions.append(region)
        self._refresh_list()

    def _remove(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._regions):
            self._regions.pop(row)
            self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for i, r in enumerate(self._regions):
            x, y, w, h = r.rect
            self.list_widget.addItem(
                f"{i + 1}. ({x},{y},{w},{h}) {format_time(r.start)}→{format_time(r.end)} {r.mode}"
            )

    def load_from_project(self, project: Project):
        self._regions = list(project.mosaic_regions)
        self._refresh_list()

    def apply_to_project(self, project: Project):
        project.mosaic_regions = list(self._regions)
