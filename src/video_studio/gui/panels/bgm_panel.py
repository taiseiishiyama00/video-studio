"""BGMパネル

タイムライン上の区間にBGMを配置。
音源ファイル指定でループ再生、または無音。
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from video_studio.core.project import BGMEntry, Project
from video_studio.core.timeline import format_time, parse_time


class BGMPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("区間を指定してBGMを配置します。\n音源はその区間内でループ再生されます。"))

        # 現在時刻表示
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("現在位置:"))
        self.time_label = QLabel("00:00:00.000")
        self.time_label.setStyleSheet("font-weight: bold; color: #FFD54F;")
        time_row.addWidget(self.time_label)
        time_row.addStretch()
        layout.addLayout(time_row)
        self._current_time = 0.0

        # 区間
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("開始:"))
        self.start_input = QLineEdit("00:00:00")
        self.start_input.setFixedWidth(100)
        row1.addWidget(self.start_input)

        btn_set_start = QPushButton("現在位置")
        btn_set_start.setFixedWidth(70)
        btn_set_start.clicked.connect(lambda: self.start_input.setText(format_time(self._current_time)))
        row1.addWidget(btn_set_start)

        row1.addWidget(QLabel("終了:"))
        self.end_input = QLineEdit("00:01:00")
        self.end_input.setFixedWidth(100)
        row1.addWidget(self.end_input)

        btn_set_end = QPushButton("現在位置")
        btn_set_end.setFixedWidth(70)
        btn_set_end.clicked.connect(lambda: self.end_input.setText(format_time(self._current_time)))
        row1.addWidget(btn_set_end)

        row1.addStretch()
        layout.addLayout(row1)

        # 音源ファイル
        row2 = QHBoxLayout()
        self.mute_check = QCheckBox("無音（音源なし）")
        row2.addWidget(self.mute_check)
        self.file_label = QLabel("未選択")
        row2.addWidget(self.file_label)
        btn_browse = QPushButton("音源を選択...")
        btn_browse.clicked.connect(self._browse_file)
        row2.addWidget(btn_browse)
        row2.addStretch()
        layout.addLayout(row2)

        # 音量
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("音量:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(-30, 0)
        self.volume_slider.setValue(-18)
        row3.addWidget(self.volume_slider)
        self.volume_label = QLabel("-18 dB")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v} dB")
        )
        row3.addWidget(self.volume_label)

        btn_add = QPushButton("追加")
        btn_add.clicked.connect(self._add)
        row3.addWidget(btn_add)
        layout.addLayout(row3)

        # リスト
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_remove = QPushButton("選択したBGMを削除")
        btn_remove.clicked.connect(self._remove)
        layout.addWidget(btn_remove)

        self._entries: list[BGMEntry] = []
        self._current_file: str | None = None

    def set_current_time(self, sec: float):
        self._current_time = sec
        self.time_label.setText(format_time(sec))

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "BGM音源を選択", "",
            "音声ファイル (*.mp3 *.wav *.ogg *.aac);;すべて (*)",
        )
        if path:
            self._current_file = path
            self.file_label.setText(path.split("/")[-1])

    def _add(self):
        try:
            start = parse_time(self.start_input.text())
            end = parse_time(self.end_input.text())
        except ValueError:
            return
        if end <= start:
            return

        source = None if self.mute_check.isChecked() else self._current_file
        entry = BGMEntry(
            start=start,
            end=end,
            source=source,
            volume=self.volume_slider.value(),
        )
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.start)
        self._refresh_list()

    def _remove(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._entries):
            self._entries.pop(row)
            self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for i, e in enumerate(self._entries):
            src = e.source.split("/")[-1] if e.source else "(無音)"
            self.list_widget.addItem(
                f"{i + 1}. {format_time(e.start)} → {format_time(e.end)} | {src} | {e.volume}dB"
            )

    def load_from_project(self, project: Project):
        self._entries = list(project.bgm_track)
        self._refresh_list()

    def apply_to_project(self, project: Project):
        project.bgm_track = list(self._entries)
