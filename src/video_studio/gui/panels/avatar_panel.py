"""アバターパネル

静止画からリップシンク付きアバターを設定する。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from video_studio.core.project import AvatarConfig, Project


POSITION_LABELS = {
    "bottom-right": "右下",
    "bottom-left": "左下",
    "top-right": "右上",
    "top-left": "左上",
}


class AvatarPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "静止画1枚からリップシンク付きアバターを生成します。\n"
            "字幕のTTS音声に連動して口を動かします。"
        ))

        # 画像選択
        row1 = QHBoxLayout()
        btn_browse = QPushButton("アバター画像を選択...")
        btn_browse.clicked.connect(self._browse_image)
        row1.addWidget(btn_browse)
        self.file_label = QLabel("未選択")
        row1.addWidget(self.file_label)
        row1.addStretch()
        layout.addLayout(row1)

        # プレビュー
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(200, 200)
        self.image_preview.setStyleSheet("border: 1px solid #555; background: #222;")
        self.image_preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_preview)

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
        row3.addWidget(QLabel("サイズ (画面比率):"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 50)
        self.scale_slider.setValue(25)
        row3.addWidget(self.scale_slider)
        self.scale_label = QLabel("25%")
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_label.setText(f"{v}%")
        )
        row3.addWidget(self.scale_label)
        layout.addLayout(row3)

        # SadTalker状態
        self.status_label = QLabel()
        self._check_sadtalker()
        layout.addWidget(self.status_label)

        # クリアボタン
        btn_clear = QPushButton("アバターを無効化")
        btn_clear.clicked.connect(self._clear)
        layout.addWidget(btn_clear)

        layout.addStretch()

        self._image_path: str | None = None

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "アバター画像を選択", "",
            "画像 (*.png *.jpg *.jpeg);;すべて (*)",
        )
        if path:
            self._image_path = path
            self.file_label.setText(Path(path).name)
            pixmap = QPixmap(path).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_preview.setPixmap(pixmap)

    def _clear(self):
        self._image_path = None
        self.file_label.setText("未選択")
        self.image_preview.clear()

    def _check_sadtalker(self):
        try:
            from video_studio.avatar.sadtalker import is_available
            if is_available():
                self.status_label.setText("SadTalker: 利用可能")
                self.status_label.setStyleSheet("color: #4CAF50;")
            else:
                self.status_label.setText("SadTalker: 未インストール（静止画フォールバック使用）")
                self.status_label.setStyleSheet("color: #FFA726;")
        except Exception:
            self.status_label.setText("SadTalker: チェック失敗")
            self.status_label.setStyleSheet("color: #EF5350;")

    def load_from_project(self, project: Project):
        if project.avatar:
            self._image_path = project.avatar.image
            self.file_label.setText(Path(project.avatar.image).name)
            if Path(project.avatar.image).exists():
                pixmap = QPixmap(project.avatar.image).scaled(
                    200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.image_preview.setPixmap(pixmap)

            # position
            idx = list(POSITION_LABELS.keys()).index(project.avatar.position)
            self.position_combo.setCurrentIndex(idx)
            self.scale_slider.setValue(int(project.avatar.scale * 100))

    def apply_to_project(self, project: Project):
        if self._image_path:
            project.avatar = AvatarConfig(
                image=self._image_path,
                position=self.position_combo.currentData(),
                scale=self.scale_slider.value() / 100.0,
            )
        else:
            project.avatar = None
