"""モザイク挿入ダイアログ"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from video_studio.core.project import MosaicRegion
from video_studio.core.timeline import format_time, parse_time


class MosaicDialog(QDialog):
    def __init__(self, source_time: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("モザイク挿入")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"開始位置: {format_time(source_time)}"))

        # 終了
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("終了位置:"))
        self.end_input = QLineEdit(format_time(source_time + 10))
        self.end_input.setFixedWidth(130)
        row0.addWidget(self.end_input)
        row0.addStretch()
        layout.addLayout(row0)

        # 領域
        layout.addWidget(QLabel("矩形領域 (ピクセル座標):"))
        row1 = QHBoxLayout()
        for label, attr, default in [("X:", "spin_x", 0), ("Y:", "spin_y", 0),
                                      ("幅:", "spin_w", 200), ("高:", "spin_h", 200)]:
            row1.addWidget(QLabel(label))
            spin = QSpinBox()
            spin.setRange(0, 9999)
            spin.setValue(default)
            setattr(self, attr, spin)
            row1.addWidget(spin)
        layout.addLayout(row1)

        # モード
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("モード:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["pixelate", "blur"])
        row2.addWidget(self.mode_combo)
        row2.addWidget(QLabel("強度:"))
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 50)
        self.strength_spin.setValue(20)
        row2.addWidget(self.strength_spin)
        row2.addStretch()
        layout.addLayout(row2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._source_time = source_time

    def get_entry(self) -> MosaicRegion | None:
        try:
            end = parse_time(self.end_input.text())
        except (ValueError, TypeError):
            return None
        if end <= self._source_time:
            return None
        return MosaicRegion(
            rect=(self.spin_x.value(), self.spin_y.value(),
                  self.spin_w.value(), self.spin_h.value()),
            start=self._source_time,
            end=end,
            mode=self.mode_combo.currentText(),
            strength=self.strength_spin.value(),
        )
