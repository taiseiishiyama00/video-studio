"""出力パネル

レンダリングを開始するボタンとプロジェクト概要を表示。
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RenderPanel(QWidget):
    render_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "全要素を合成して最終動画を書き出します。\n\n"
            "メニューの「ファイル → レンダリング」または\n"
            "下のボタンからレンダリングを開始できます。"
        ))

        layout.addStretch()

        btn = QPushButton("レンダリング開始")
        btn.setMinimumHeight(50)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn.clicked.connect(self.render_requested)
        layout.addWidget(btn)

        layout.addStretch()
