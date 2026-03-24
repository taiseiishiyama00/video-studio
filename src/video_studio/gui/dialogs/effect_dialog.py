"""効果挿入ダイアログ

モザイク（ぼかし/ピクセレート）と強調マーク（丸/矢印/矩形）を統合。
時間範囲と効果タイプを選択 → プレビュー上で範囲選択の2ステップUI。
"""

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
    QStackedWidget,
    QVBoxLayout,
)

from video_studio.core.timeline import format_time, parse_time


# 効果タイプ定義
EFFECT_TYPES = [
    ("モザイク（ピクセレート）", "pixelate"),
    ("モザイク（ぼかし）", "blur"),
    ("強調: 矩形", "rect_highlight"),
    ("強調: 丸囲み", "circle"),
    ("強調: 矢印", "arrow"),
]


class EffectDialog(QDialog):
    """効果の種類と時間範囲を選択するダイアログ"""

    def __init__(self, source_time: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("効果を追加")
        self.setMinimumWidth(400)

        self._source_time = source_time

        layout = QVBoxLayout(self)

        # 時間範囲
        layout.addWidget(QLabel(f"現在位置: {format_time(source_time)}"))

        row_start = QHBoxLayout()
        row_start.addWidget(QLabel("開始:"))
        self.start_input = QLineEdit(format_time(source_time))
        self.start_input.setFixedWidth(130)
        row_start.addWidget(self.start_input)
        row_start.addStretch()
        layout.addLayout(row_start)

        row_end = QHBoxLayout()
        row_end.addWidget(QLabel("終了:"))
        self.end_input = QLineEdit(format_time(source_time + 5))
        self.end_input.setFixedWidth(130)
        row_end.addWidget(self.end_input)
        row_end.addStretch()
        layout.addLayout(row_end)

        # 効果タイプ選択
        row_type = QHBoxLayout()
        row_type.addWidget(QLabel("効果:"))
        self.type_combo = QComboBox()
        for label, value in EFFECT_TYPES:
            self.type_combo.addItem(label, value)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        row_type.addWidget(self.type_combo, stretch=1)
        layout.addLayout(row_type)

        # 効果タイプ別パラメータ（スタック）
        self.params_stack = QStackedWidget()

        # --- モザイク系パラメータ ---
        mosaic_params = QWidget()
        mp_layout = QHBoxLayout(mosaic_params)
        mp_layout.setContentsMargins(0, 0, 0, 0)
        mp_layout.addWidget(QLabel("強度:"))
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 50)
        self.strength_spin.setValue(20)
        mp_layout.addWidget(self.strength_spin)
        mp_layout.addStretch()
        self.params_stack.addWidget(mosaic_params)  # index 0

        # --- 強調系パラメータ ---
        annot_params = QWidget()
        ap_layout = QHBoxLayout(annot_params)
        ap_layout.setContentsMargins(0, 0, 0, 0)
        self._color = "#FF0000"
        self.color_btn = QPushButton("色を選択")
        self.color_btn.setStyleSheet(f"background-color: {self._color}; color: white;")
        self.color_btn.clicked.connect(self._pick_color)
        ap_layout.addWidget(self.color_btn)
        ap_layout.addWidget(QLabel("太さ:"))
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 20)
        self.thickness_spin.setValue(3)
        ap_layout.addWidget(self.thickness_spin)
        ap_layout.addStretch()
        self.params_stack.addWidget(annot_params)  # index 1

        layout.addWidget(self.params_stack)

        # 説明
        self.hint_label = QLabel("OKを押した後、動画プレビュー上でドラッグして効果範囲を選択します")
        self.hint_label.setStyleSheet("color: #888; font-size: 11px; margin-top: 8px;")
        layout.addWidget(self.hint_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 初期表示
        self._on_type_changed(0)

    def _on_type_changed(self, index: int):
        effect_type = self.type_combo.currentData()
        if effect_type in ("pixelate", "blur"):
            self.params_stack.setCurrentIndex(0)
        else:
            self.params_stack.setCurrentIndex(1)

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self)
        if color.isValid():
            self._color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self._color}; color: white;")

    def get_params(self) -> dict | None:
        """ダイアログの入力値を辞書で返す。無効なら None。"""
        try:
            start = parse_time(self.start_input.text())
            end = parse_time(self.end_input.text())
        except (ValueError, TypeError):
            return None
        if end <= start:
            return None

        effect_type = self.type_combo.currentData()
        result = {
            "effect_type": effect_type,
            "start": start,
            "end": end,
        }

        if effect_type in ("pixelate", "blur"):
            result["strength"] = self.strength_spin.value()
        else:
            result["color"] = self._color
            result["thickness"] = self.thickness_spin.value()

        return result
