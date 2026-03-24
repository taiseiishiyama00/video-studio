"""アバター設定ダイアログ（3画像リップシンク対応）

3枚の画像で擬似リップシンク:
  1. 目開け口閉じ（ニュートラル）
  2. 目開け口開け（発話中）
  3. 目閉じ口閉じ（まばたき）
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from video_studio.core.project import AvatarConfig

POSITION_LABELS = {
    "bottom-right": "右下",
    "bottom-left": "左下",
    "top-right": "右上",
    "top-left": "左上",
}


class _ImagePicker(QVBoxLayout):
    """画像選択用の小コンポーネント"""

    def __init__(self, label: str, settings_key: str, parent_dialog):
        super().__init__()
        self._settings = QSettings("VideoStudio", "VideoStudio")
        self._settings_key = settings_key
        self._parent = parent_dialog
        self.path: str = ""

        self.addWidget(QLabel(label))
        self.preview = QLabel()
        self.preview.setFixedSize(100, 100)
        self.preview.setStyleSheet("border: 1px solid #555; background: #222;")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setText("未選択")
        self.addWidget(self.preview)

        btn = QPushButton("選択...")
        btn.clicked.connect(self._browse)
        self.addWidget(btn)

    def _browse(self):
        last_dir = self._settings.value(f"last_dir/{self._settings_key}", "")
        path, _ = QFileDialog.getOpenFileName(
            self._parent, "画像を選択", last_dir,
            "画像 (*.png *.jpg *.jpeg);;すべて (*)",
        )
        if path:
            self._settings.setValue(f"last_dir/{self._settings_key}", str(Path(path).parent))
            self.set_image(path)

    def set_image(self, path: str):
        self.path = path
        if path and Path(path).exists():
            pixmap = QPixmap(path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview.setPixmap(pixmap)
            self.preview.setText("")
        else:
            self.preview.clear()
            self.preview.setText("未選択")


class AvatarDialog(QDialog):
    def __init__(self, current_config: AvatarConfig | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("アバター設定")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("3枚の画像で擬似リップシンクを行います"))

        # 3画像選択（横並び）
        images_layout = QHBoxLayout()

        self.pick_neutral = _ImagePicker("目開け口閉じ\n(ニュートラル)", "avatar", self)
        images_layout.addLayout(self.pick_neutral)

        self.pick_mouth = _ImagePicker("目開け口開け\n(発話中)", "avatar", self)
        images_layout.addLayout(self.pick_mouth)

        self.pick_blink = _ImagePicker("目閉じ口閉じ\n(まばたき)", "avatar", self)
        images_layout.addLayout(self.pick_blink)

        layout.addLayout(images_layout)

        # 位置
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("表示位置:"))
        self.position_combo = QComboBox()
        for key, label in POSITION_LABELS.items():
            self.position_combo.addItem(label, key)
        row2.addWidget(self.position_combo)
        row2.addStretch()
        layout.addLayout(row2)

        # サイズ
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("サイズ:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 50)
        self.scale_slider.setValue(25)
        row3.addWidget(self.scale_slider)
        self.scale_label = QLabel("25%")
        self.scale_slider.valueChanged.connect(lambda v: self.scale_label.setText(f"{v}%"))
        self.scale_label.setFixedWidth(40)
        row3.addWidget(self.scale_label)
        layout.addLayout(row3)

        # 無効化
        btn_clear = QPushButton("アバターを無効化")
        btn_clear.clicked.connect(self._clear_and_accept)
        layout.addWidget(btn_clear)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._cleared = False

        # 既存設定を反映
        if current_config:
            self.pick_neutral.set_image(current_config.image)
            self.pick_mouth.set_image(current_config.image_mouth_open)
            self.pick_blink.set_image(current_config.image_blink)
            idx = list(POSITION_LABELS.keys()).index(current_config.position)
            self.position_combo.setCurrentIndex(idx)
            self.scale_slider.setValue(int(current_config.scale * 100))

    def _clear_and_accept(self):
        self._cleared = True
        self.accept()

    def get_config(self) -> AvatarConfig | None:
        if self._cleared:
            return None
        if not self.pick_neutral.path:
            return None
        return AvatarConfig(
            image=self.pick_neutral.path,
            image_mouth_open=self.pick_mouth.path,
            image_blink=self.pick_blink.path,
            position=self.position_combo.currentData(),
            scale=self.scale_slider.value() / 100.0,
        )

    def is_cleared(self) -> bool:
        return self._cleared
