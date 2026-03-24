"""挿入メニュー

タイムラインをダブルクリックした位置に表示されるポップアップメニュー。
挿入する要素の種類を選択すると、対応するダイアログが開く。
"""

from __future__ import annotations

from PySide6.QtWidgets import QMenu, QWidget

from video_studio.core.timeline import format_time


def show_insert_menu(
    parent: QWidget,
    source_time: float,
    pos,
    on_subtitle,
    on_bgm,
    on_mosaic,
    on_annotation,
):
    """挿入メニューを表示

    Args:
        parent: 親ウィジェット
        source_time: カット前の絶対時間（秒）
        pos: メニュー表示位置 (QPoint)
        on_subtitle: 字幕挿入コールバック
        on_bgm: BGM挿入コールバック
        on_mosaic: モザイク挿入コールバック
        on_annotation: 強調マーク挿入コールバック
    """
    menu = QMenu(parent)
    menu.setStyleSheet("""
        QMenu { background: #2a2a2a; color: #ddd; padding: 4px; font-size: 13px; }
        QMenu::item { padding: 6px 20px; }
        QMenu::item:selected { background: #3a6ea5; }
    """)

    time_str = format_time(source_time)
    menu.addAction(f"── {time_str} に挿入 ──").setEnabled(False)
    menu.addSeparator()
    menu.addAction("字幕 + TTS", lambda: on_subtitle(source_time))
    menu.addAction("BGM", lambda: on_bgm(source_time))
    menu.addAction("モザイク", lambda: on_mosaic(source_time))
    menu.addAction("強調マーク", lambda: on_annotation(source_time))
    menu.exec(pos)
