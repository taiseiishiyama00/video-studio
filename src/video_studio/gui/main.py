"""GUIアプリのエントリポイント"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from video_studio.gui.main_window import MainWindow


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("Video Studio")
    app.setOrganizationName("VideoStudio")
    from video_studio.gui.theme import get_stylesheet

    app.setStyleSheet(get_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
