"""BGM挿入ダイアログ"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from video_studio.core.project import BGMEntry
from video_studio.core.timeline import format_time, parse_time


class BGMDialog(QDialog):
    def __init__(self, source_time: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BGM 挿入")
        self.setMinimumWidth(400)
        self._settings = QSettings("VideoStudio", "VideoStudio")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"開始位置: {format_time(source_time)}"))

        # 終了時間
        row = QHBoxLayout()
        row.addWidget(QLabel("終了位置:"))
        self.end_input = QLineEdit(format_time(source_time + 60))
        self.end_input.setFixedWidth(130)
        row.addWidget(self.end_input)
        row.addStretch()
        layout.addLayout(row)

        # 音源
        row2 = QHBoxLayout()
        self.mute_check = QCheckBox("無音（音源なし）")
        row2.addWidget(self.mute_check)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.file_label = QLabel("未選択")
        row3.addWidget(self.file_label)
        btn = QPushButton("音源を選択...")
        btn.clicked.connect(self._browse)
        row3.addWidget(btn)
        row3.addStretch()
        layout.addLayout(row3)

        # 音量
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("音量:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(-30, 0)
        saved_bgm_vol = int(self._settings.value("bgm/volume", -18))
        self.volume_slider.setValue(saved_bgm_vol)
        row4.addWidget(self.volume_slider)
        self.vol_label = QLabel(f"{saved_bgm_vol} dB")
        self.volume_slider.valueChanged.connect(lambda v: self.vol_label.setText(f"{v} dB"))
        row4.addWidget(self.vol_label)
        layout.addLayout(row4)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._source_time = source_time
        self._file_path: str | None = None

    def _browse(self):
        last_dir = self._settings.value("last_dir/bgm", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "BGM音源を選択", last_dir,
            "音声 (*.mp3 *.wav *.ogg *.aac);;すべて (*)",
        )
        if path:
            self._settings.setValue("last_dir/bgm", str(Path(path).parent))
            self._file_path = path
            self.file_label.setText(path.split("/")[-1])

    def get_entry(self) -> BGMEntry | None:
        try:
            end = parse_time(self.end_input.text())
        except (ValueError, TypeError):
            return None
        if end <= self._source_time:
            return None
        source = None if self.mute_check.isChecked() else self._file_path
        self._settings.setValue("bgm/volume", self.volume_slider.value())
        return BGMEntry(
            start=self._source_time,
            end=end,
            source=source,
            volume=self.volume_slider.value(),
        )
