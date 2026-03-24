"""ツールパネル（タブ切替）

各編集機能のパネルをタブで管理する。
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from video_studio.core.project import Project
from video_studio.gui.panels.cut_panel import CutPanel
from video_studio.gui.panels.subtitle_panel import SubtitlePanel
from video_studio.gui.panels.bgm_panel import BGMPanel
from video_studio.gui.panels.mosaic_panel import MosaicPanel
from video_studio.gui.panels.annotation_panel import AnnotationPanel
from video_studio.gui.panels.avatar_panel import AvatarPanel
from video_studio.gui.panels.render_panel import RenderPanel


class ToolTabs(QWidget):
    render_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.cut_panel = CutPanel()
        self.subtitle_panel = SubtitlePanel()
        self.bgm_panel = BGMPanel()
        self.mosaic_panel = MosaicPanel()
        self.annotation_panel = AnnotationPanel()
        self.avatar_panel = AvatarPanel()
        self.render_panel = RenderPanel()

        self.tabs.addTab(self.cut_panel, "カット")
        self.tabs.addTab(self.subtitle_panel, "字幕+TTS")
        self.tabs.addTab(self.bgm_panel, "BGM")
        self.tabs.addTab(self.mosaic_panel, "モザイク")
        self.tabs.addTab(self.annotation_panel, "強調")
        self.tabs.addTab(self.avatar_panel, "アバター")
        self.tabs.addTab(self.render_panel, "出力")

        self.render_panel.render_requested.connect(self.render_requested)

    def set_project(self, project: Project):
        """プロジェクトの内容を各パネルに反映"""
        self.cut_panel.load_from_project(project)
        self.subtitle_panel.load_from_project(project)
        self.bgm_panel.load_from_project(project)
        self.mosaic_panel.load_from_project(project)
        self.annotation_panel.load_from_project(project)
        self.avatar_panel.load_from_project(project)

    def set_current_time(self, sec: float):
        """現在の再生位置を各パネルに通知"""
        self.subtitle_panel.set_current_time(sec)
        self.bgm_panel.set_current_time(sec)
        self.mosaic_panel.set_current_time(sec)
        self.annotation_panel.set_current_time(sec)

    def apply_to_project(self, project: Project):
        """各パネルの内容をプロジェクトに書き戻す"""
        self.cut_panel.apply_to_project(project)
        self.subtitle_panel.apply_to_project(project)
        self.bgm_panel.apply_to_project(project)
        self.mosaic_panel.apply_to_project(project)
        self.annotation_panel.apply_to_project(project)
        self.avatar_panel.apply_to_project(project)
