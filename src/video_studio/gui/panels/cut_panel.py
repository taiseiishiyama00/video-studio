"""カット編集パネル

残す区間を追加・削除する。
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from video_studio.core.project import Project
from video_studio.core.timeline import Cut, Timeline, format_time, parse_time


class CutPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("残す区間を追加してください。\n未指定の場合は元動画全体を使用します。"))

        # 入力行
        row = QHBoxLayout()
        row.addWidget(QLabel("開始:"))
        self.start_input = QLineEdit("00:00:00")
        self.start_input.setFixedWidth(100)
        row.addWidget(self.start_input)

        row.addWidget(QLabel("終了:"))
        self.end_input = QLineEdit("00:01:00")
        self.end_input.setFixedWidth(100)
        row.addWidget(self.end_input)

        btn_add = QPushButton("追加")
        btn_add.clicked.connect(self._add)
        row.addWidget(btn_add)
        row.addStretch()
        layout.addLayout(row)

        # リスト
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_remove = QPushButton("選択した区間を削除")
        btn_remove.clicked.connect(self._remove)
        layout.addWidget(btn_remove)

        self._cuts: list[Cut] = []

    def _add(self):
        try:
            start = parse_time(self.start_input.text())
            end = parse_time(self.end_input.text())
        except ValueError:
            return
        if end <= start:
            return

        cut = Cut(start=start, end=end)
        self._cuts.append(cut)
        self._refresh_list()

    def _remove(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._cuts):
            self._cuts.pop(row)
            self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for i, c in enumerate(self._cuts):
            self.list_widget.addItem(
                f"{i + 1}. {format_time(c.start)} → {format_time(c.end)}  ({c.duration:.1f}秒)"
            )

    def load_from_project(self, project: Project):
        self._cuts = list(project.timeline.cuts)
        self._refresh_list()

    def apply_to_project(self, project: Project):
        project.timeline = Timeline(
            cuts=list(self._cuts),
            source_duration=project.timeline.source_duration,
        )
