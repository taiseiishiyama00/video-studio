"""字幕+TTSパネル

タイムライン上の時点にテキストを配置。
字幕表示 + TTS音声を同時に挿入。
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from video_studio.core.project import Project, SubtitleEntry
from video_studio.core.timeline import format_time, parse_time

VOICES = [
    "ja-JP-NanamiNeural",
    "ja-JP-KeitaNeural",
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "zh-CN-XiaoxiaoNeural",
    "ko-KR-SunHiNeural",
]


class SubtitlePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "テキストを配置すると、字幕とTTS音声が同時に挿入されます。\n"
            "動画を再生/停止した位置が自動で入ります。"
        ))

        # 挿入時点
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("挿入時点:"))
        self.time_label = QLabel("00:00:00.000")
        self.time_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFD54F;")
        row1.addWidget(self.time_label)
        row1.addStretch()
        layout.addLayout(row1)
        self._current_time = 0.0

        # テキスト
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("テキスト:"))
        self.text_input = QLineEdit()
        row2.addWidget(self.text_input)
        layout.addLayout(row2)

        # 音声
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("音声:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(VOICES)
        row3.addWidget(self.voice_combo)

        btn_add = QPushButton("追加")
        btn_add.clicked.connect(self._add)
        row3.addWidget(btn_add)
        row3.addStretch()
        layout.addLayout(row3)

        # リスト
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_remove = QPushButton("選択した字幕を削除")
        btn_remove.clicked.connect(self._remove)
        layout.addWidget(btn_remove)

        self._entries: list[SubtitleEntry] = []

    def set_current_time(self, sec: float):
        """再生位置の自動更新"""
        self._current_time = sec
        self.time_label.setText(format_time(sec))

    def _add(self):
        text = self.text_input.text().strip()
        if not text:
            return

        entry = SubtitleEntry(
            time=self._current_time,
            text=text,
            voice=self.voice_combo.currentText(),
        )
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.time)
        self._refresh_list()
        self.text_input.clear()

    def _remove(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._entries):
            self._entries.pop(row)
            self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for i, e in enumerate(self._entries):
            self.list_widget.addItem(
                f"{i + 1}. [{format_time(e.time)}] {e.text}  ({e.voice})"
            )

    def load_from_project(self, project: Project):
        self._entries = list(project.subtitle_track)
        self._refresh_list()

    def apply_to_project(self, project: Project):
        project.subtitle_track = list(self._entries)
