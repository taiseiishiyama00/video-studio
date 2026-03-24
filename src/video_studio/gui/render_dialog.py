"""レンダリングダイアログ

バックグラウンドスレッドでパイプラインを実行し、進捗を表示する。
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from video_studio.core.pipeline import RenderPipeline
from video_studio.core.project import Project
from video_studio.gui.theme import COLORS


class RenderWorker(QThread):
    """レンダリングをバックグラウンドで実行"""

    progress = Signal(int, int, str)  # step, total, message
    finished = Signal(str)            # output_path
    error = Signal(str)               # error message

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project

    def run(self):
        try:
            pipeline = RenderPipeline(self.project)
            result = pipeline.render(progress_callback=self._on_progress)
            self.finished.emit(str(result))
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, step: int, total: int, msg: str):
        self.progress.emit(step, total, msg)


class RenderDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("レンダリング")
        self.setMinimumSize(500, 350)
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.status_label = QLabel("レンダリングを開始しています...")
        self.status_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLORS['text']};"
        )
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: %s; color: %s; "
            "font-family: 'SF Mono', 'Menlo', monospace; "
            "border: 1px solid %s; border-radius: 4px; padding: 8px;"
            % (COLORS["bg_darkest"], COLORS["text"], COLORS["border"])
        )
        layout.addWidget(self.log_text)

        self.close_btn = QPushButton("閉じる")
        self.close_btn.setObjectName("accentBtn")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        # ワーカースレッド起動
        self.worker = RenderWorker(project)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    @Slot(int, int, str)
    def _on_progress(self, step: int, total: int, msg: str):
        pct = int(step / total * 100)
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"[{step}/{total}] {msg}")
        self.log_text.append(f"[{step}/{total}] {msg}")

    @Slot(str)
    def _on_finished(self, output_path: str):
        self.progress_bar.setValue(100)
        self.status_label.setText("レンダリング完了!")
        self.status_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLORS['success']};"
        )
        self.log_text.append(f"\n出力: {output_path}")
        self.close_btn.setEnabled(True)

    @Slot(str)
    def _on_error(self, error_msg: str):
        self.status_label.setText("エラーが発生しました")
        self.status_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLORS['danger']};"
        )
        self.log_text.append(f"\nエラー: {error_msg}")
        self.close_btn.setEnabled(True)
