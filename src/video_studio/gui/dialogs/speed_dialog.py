"""速度変更ダイアログ"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
)

from video_studio.core.timeline import format_time


class SpeedDialog(QDialog):
    def __init__(self, start: float, end: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("速度変更")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"範囲: {format_time(start)} → {format_time(end)}"))
        dur = end - start
        layout.addWidget(QLabel(f"期間: {format_time(dur)}"))

        # プリセット
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("速度:"))
        self.combo = QComboBox()
        self.combo.addItem("0.25x (4分の1速)", 0.25)
        self.combo.addItem("0.5x (半速)", 0.5)
        self.combo.addItem("1.0x (通常速)", 1.0)
        self.combo.addItem("1.5x (1.5倍速)", 1.5)
        self.combo.addItem("2.0x (2倍速)", 2.0)
        self.combo.addItem("3.0x (3倍速)", 3.0)
        self.combo.currentIndexChanged.connect(self._on_preset_changed)
        row1.addWidget(self.combo)
        layout.addLayout(row1)

        # カスタム値
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("カスタム:"))
        self.spin = QDoubleSpinBox()
        self.spin.setRange(0.1, 10.0)
        self.spin.setSingleStep(0.1)
        self.spin.setValue(1.0)
        row2.addWidget(self.spin)
        row2.addWidget(QLabel("x"))
        layout.addLayout(row2)

        # ボタン
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._start = start
        self._end = end

    def _on_preset_changed(self, index: int):
        speed = self.combo.currentData()
        if speed is not None:
            self.spin.setValue(speed)

    def get_speed(self) -> float:
        return self.spin.value()
