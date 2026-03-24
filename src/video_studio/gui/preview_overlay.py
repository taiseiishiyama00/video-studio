"""プレビューオーバーレイ

動画プレイヤーの上に透明レイヤーを重ね、
現在時刻に応じて字幕・モザイク領域・強調マーク・アバター位置をリアルタイム表示する。
レンダリング不要でプレビュー可能。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from video_studio.core.project import Annotation, MosaicRegion, Project, SubtitleEntry


class PreviewOverlay(QWidget):
    """動画プレイヤーの上に重ねる透明オーバーレイ"""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self._subtitles: list[SubtitleEntry] = []
        self._mosaic_regions: list[MosaicRegion] = []
        self._annotations: list[Annotation] = []
        self._avatar_rect: tuple[int, int, int, int] | None = None
        self._current_time = 0.0

        # 親のリサイズに追従
        parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == event.Type.Resize:
            self.setGeometry(0, 0, obj.width(), obj.height())
        return False

    def clear(self):
        self._subtitles = []
        self._mosaic_regions = []
        self._annotations = []
        self._avatar_rect = None
        self.update()

    def update_overlays(self, project: Project, current_time: float):
        """プロジェクトの状態と現在時刻からオーバーレイを更新"""
        self._current_time = current_time
        self._subtitles = project.subtitle_track
        self._mosaic_regions = project.mosaic_regions
        self._annotations = project.annotations

        if project.avatar:
            w = self.width()
            h = self.height()
            size = int(min(w, h) * project.avatar.scale)
            margin = 10
            positions = {
                "bottom-right": (w - size - margin, h - size - margin),
                "bottom-left": (margin, h - size - margin),
                "top-right": (w - size - margin, margin),
                "top-left": (margin, margin),
            }
            x, y = positions.get(project.avatar.position, positions["bottom-right"])
            self._avatar_rect = (x, y, size, size)
        else:
            self._avatar_rect = None

        self.update()

    def paintEvent(self, event):
        if not self._subtitles and not self._mosaic_regions and not self._annotations and not self._avatar_rect:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = self._current_time

        # モザイク領域（枠線で表示）
        for region in self._mosaic_regions:
            if region.start <= t <= region.end:
                rx, ry, rw, rh = self._scale_rect(region.rect)
                painter.setPen(QPen(QColor(200, 100, 200, 200), 2, Qt.DashLine))
                painter.setBrush(QColor(200, 100, 200, 30))
                painter.drawRect(rx, ry, rw, rh)
                painter.setPen(QPen(QColor(255, 255, 255, 200)))
                painter.setFont(QFont("sans-serif", 9))
                painter.drawText(rx + 4, ry + 14, "モザイク")

        # 強調マーク
        for annot in self._annotations:
            if annot.start <= t <= annot.end:
                self._draw_annotation(painter, annot)

        # 字幕プレビュー
        for sub in self._subtitles:
            dur = sub.duration or 3.0
            if sub.time <= t <= sub.time + dur:
                self._draw_subtitle(painter, sub.text)

        # アバター位置
        if self._avatar_rect:
            # 字幕がアクティブならアバター枠を表示
            any_sub_active = any(
                s.time <= t <= s.time + (s.duration or 3.0) for s in self._subtitles
            )
            if any_sub_active or not self._subtitles:
                x, y, w, h = self._avatar_rect
                painter.setPen(QPen(QColor(100, 220, 220, 180), 2, Qt.DashLine))
                painter.setBrush(QColor(100, 220, 220, 20))
                painter.drawRect(x, y, w, h)
                painter.setPen(QPen(QColor(255, 255, 255, 200)))
                painter.setFont(QFont("sans-serif", 10))
                painter.drawText(x + 4, y + 16, "アバター")

        painter.end()

    def _draw_subtitle(self, painter: QPainter, text: str):
        """字幕をプレビュー表示"""
        w = self.width()
        h = self.height()

        font = QFont("sans-serif", 18, QFont.Bold)
        painter.setFont(font)

        # 背景帯
        text_rect = QRectF(20, h - 70, w - 40, 50)
        painter.fillRect(text_rect, QColor(0, 0, 0, 150))

        # テキスト
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(text_rect, Qt.AlignCenter, text)

    def _draw_annotation(self, painter: QPainter, annot: Annotation):
        """強調マークをプレビュー表示"""
        color = QColor(annot.color)
        color.setAlpha(200)
        pen = QPen(color, annot.thickness)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        pos = annot.position
        if annot.type == "circle" and len(pos) >= 3:
            cx, cy, r = self._scale_point(pos[0], pos[1]) + (self._scale_val(pos[2]),)
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        elif annot.type == "arrow" and len(pos) >= 4:
            x1, y1 = self._scale_point(pos[0], pos[1])
            x2, y2 = self._scale_point(pos[2], pos[3])
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            # 矢印先端
            import math
            angle = math.atan2(y2 - y1, x2 - x1)
            tip = 15
            painter.drawLine(
                int(x2), int(y2),
                int(x2 - tip * math.cos(angle - 0.4)),
                int(y2 - tip * math.sin(angle - 0.4)),
            )
            painter.drawLine(
                int(x2), int(y2),
                int(x2 - tip * math.cos(angle + 0.4)),
                int(y2 - tip * math.sin(angle + 0.4)),
            )
        elif annot.type == "rect_highlight" and len(pos) >= 4:
            rx, ry, rw, rh = self._scale_rect(pos)
            painter.drawRect(rx, ry, rw, rh)

    def _scale_rect(self, rect) -> tuple[int, int, int, int]:
        """元動画座標 → オーバーレイ座標にスケーリング（仮に1920x1080基準）"""
        ref_w, ref_h = 1920, 1080
        sx = self.width() / ref_w
        sy = self.height() / ref_h
        return (int(rect[0] * sx), int(rect[1] * sy), int(rect[2] * sx), int(rect[3] * sy))

    def _scale_point(self, x, y) -> tuple[float, float]:
        ref_w, ref_h = 1920, 1080
        return (x * self.width() / ref_w, y * self.height() / ref_h)

    def _scale_val(self, v) -> float:
        return v * min(self.width() / 1920, self.height() / 1080)
