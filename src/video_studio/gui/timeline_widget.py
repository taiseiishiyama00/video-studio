"""タイムラインウィジェット

2つのモードを持つ:
- カットモード: 元動画の全尺を表示。ドラッグで範囲選択→カット。カット済み区間はグレーアウト。
- 挿入モード: カット後の尺を表示。クリックで挿入位置を指定→ダイアログで挿入内容を選択。

挿入データは内部的にカット前の絶対時間 (source_time) で保持する。
"""

from __future__ import annotations

import math
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QMouseEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from video_studio.core.timeline import format_time


# ==============================================================================
# カットモード用タイムライン
# ==============================================================================

class CutTimeline(QWidget):
    """編集モード: 元動画全尺を表示。ドラッグでカット/速度変更範囲を選択。"""

    position_changed = Signal(int)                  # ms — シーク
    cut_requested = Signal(float, float)            # start_sec, end_sec — カット要求
    speed_requested = Signal(float, float, float)   # start_sec, end_sec, speed — 速度変更要求
    scrub_position = Signal(int)                    # ms — ドラッグ中のスクラブシーク

    RULER_H = 24
    TRACK_H = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(90)
        self._duration_ms = 1
        self._position_ms = 0
        self._cut_regions: list[tuple[float, float]] = []  # カット済み区間 (source_sec)
        self._speed_regions: list[tuple[float, float, float]] = []  # (start, end, speed)
        self._mode = "cut"  # "cut" or "speed"

        # 範囲選択
        self._dragging = False
        self._drag_start_ms = 0
        self._drag_end_ms = 0

    def set_duration(self, ms: int):
        self._duration_ms = max(1, ms)
        self.update()

    def set_position(self, ms: int):
        self._position_ms = ms
        self.update()

    def set_cut_regions(self, regions: list[tuple[float, float]]):
        """カット済み（削除された）区間を設定"""
        self._cut_regions = regions
        self.update()

    def set_speed_regions(self, regions: list[tuple[float, float, float]]):
        """速度変更（倍速）区間を設定。(start_sec, end_sec, speed)"""
        self._speed_regions = regions
        self.update()

    def set_mode(self, mode: str):
        """モードを設定: "cut" or "speed" """
        self._mode = mode
        self.update()

    def get_selection(self) -> tuple[float, float] | None:
        if not self._dragging and self._drag_start_ms != self._drag_end_ms:
            s = min(self._drag_start_ms, self._drag_end_ms) / 1000.0
            e = max(self._drag_start_ms, self._drag_end_ms) / 1000.0
            if e - s >= 0.1:
                return (s, e)
        return None

    # --- 描画 ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor(35, 35, 35))

        # ルーラー
        self._draw_ruler(painter, 0, 0, w, self.RULER_H)

        # メイントラック（元動画の全尺）
        ty = self.RULER_H
        painter.fillRect(0, ty, w, self.TRACK_H, QColor(60, 80, 60))

        # カット済み区間をグレーアウト
        for cs, ce in self._cut_regions:
            x1 = int(cs * 1000 / self._duration_ms * w)
            x2 = int(ce * 1000 / self._duration_ms * w)
            painter.fillRect(x1, ty, x2 - x1, self.TRACK_H, QColor(80, 80, 80, 200))
            # 斜線パターン
            painter.setPen(QPen(QColor(120, 120, 120, 150), 1))
            step = 8
            for lx in range(x1, x2, step):
                painter.drawLine(lx, ty, min(lx + self.TRACK_H, x2), ty + self.TRACK_H)

        # 速度変更区間を表示
        for ss, se, speed in self._speed_regions:
            x1 = int(ss * 1000 / self._duration_ms * w)
            x2 = int(se * 1000 / self._duration_ms * w)
            # 速度ごとに色を変える
            if speed > 1.0:  # 高速
                color = QColor(100, 200, 100, 120)
            elif speed < 1.0:  # 低速
                color = QColor(100, 100, 200, 120)
            else:
                color = QColor(100, 150, 150, 120)
            painter.fillRect(x1, ty, max(1, x2 - x1), self.TRACK_H, color)
            # ラベル（倍速表示）
            painter.setPen(QPen(QColor(255, 255, 255)))
            font = QFont("sans-serif", 9, QFont.Bold)
            painter.setFont(font)
            if x2 - x1 > 30:
                painter.drawText(x1 + 4, ty, x2 - x1 - 8, self.TRACK_H,
                                Qt.AlignCenter | Qt.AlignVCenter, f"{speed:.1f}x")

        # ドラッグ中の選択範囲
        if self._drag_start_ms != self._drag_end_ms:
            s = min(self._drag_start_ms, self._drag_end_ms)
            e = max(self._drag_start_ms, self._drag_end_ms)
            sx = int(s / self._duration_ms * w)
            ex = int(e / self._duration_ms * w)
            if self._mode == "cut":
                color = QColor(255, 80, 80, 80)
                line_color = QColor(255, 100, 100, 220)
            else:  # speed mode
                color = QColor(100, 200, 255, 80)
                line_color = QColor(100, 200, 255, 220)
            painter.fillRect(sx, ty, ex - sx, self.TRACK_H, color)
            painter.setPen(QPen(line_color, 2, Qt.DashLine))
            painter.drawRect(sx, ty, ex - sx, self.TRACK_H)

        # 再生位置
        px = int(self._position_ms / self._duration_ms * w)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(px, 0, px, h)

        painter.end()

    def _draw_ruler(self, painter: QPainter, x0: int, y0: int, w: int, h: int):
        painter.fillRect(x0, y0, w, h, QColor(45, 45, 45))
        painter.setPen(QPen(QColor(170, 170, 170)))
        dur_sec = self._duration_ms / 1000.0
        if dur_sec <= 0:
            return
        interval = self._calc_interval(dur_sec)
        font = QFont("sans-serif", 9)
        painter.setFont(font)
        t = 0.0
        while t <= dur_sec:
            px = x0 + int(t / dur_sec * w)
            painter.drawLine(px, y0 + h - 5, px, y0 + h)
            m, s = divmod(int(t), 60)
            painter.drawText(px + 3, y0 + h - 7, f"{m}:{s:02d}")
            t += interval

    @staticmethod
    def _calc_interval(dur_sec: float) -> int:
        interval = max(1, int(dur_sec / 20))
        for step in [1, 2, 5, 10, 15, 30, 60]:
            if interval <= step:
                return step
        return 60

    # --- マウス ---

    def _x_to_ms(self, x: float) -> int:
        ratio = max(0.0, min(1.0, x / max(1, self.width())))
        return int(ratio * self._duration_ms)

    def mousePressEvent(self, event: QMouseEvent):
        ms = self._x_to_ms(event.position().x())
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_ms = ms
            self._drag_end_ms = ms
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self._drag_end_ms = self._x_to_ms(event.position().x())
            # ドラッグ中は現在位置に動画をシーク（プレビュー同期）
            self.scrub_position.emit(self._drag_end_ms)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._drag_end_ms = self._x_to_ms(event.position().x())
            sel = self.get_selection()
            if sel:
                if self._mode == "cut":
                    self.cut_requested.emit(sel[0], sel[1])
                else:  # speed mode
                    # 速度値はメインウィンドウのダイアログで入力させるため、
                    # ここでは1.0（デフォルト）で後のダイアログで変更される
                    self.speed_requested.emit(sel[0], sel[1], 1.0)
            else:
                # クリックでシーク
                self._position_ms = self._drag_start_ms
                self.position_changed.emit(self._drag_start_ms)
            self._drag_start_ms = 0
            self._drag_end_ms = 0
            self.update()


# ==============================================================================
# 挿入モード用タイムライン
# ==============================================================================

class InsertTimeline(QWidget):
    """挿入モード: カット後の尺を表示。ドラッグで範囲選択、クリックでシーク。"""

    position_changed = Signal(int)            # ms (カット後タイムライン上)
    scrub_position = Signal(int)              # ms — ドラッグ中スクラブ
    insert_requested = Signal(float)          # source_time_sec — ダブルクリック挿入

    RULER_H = 24
    TRACK_H = 22
    TRACK_NAMES = ["字幕", "BGM", "モザイク", "強調", "アバター"]
    TRACK_COLORS = [
        QColor(100, 150, 255, 160),
        QColor(255, 180, 50, 160),
        QColor(200, 100, 200, 160),
        QColor(255, 100, 100, 160),
        QColor(100, 220, 220, 160),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self._post_cut_duration_ms = 1
        self._position_ms = 0

        # 挿入アイテム: track_idx → [(start_sec, end_sec, label), ...]
        # 時間はカット後タイムライン基準で表示用に変換済み
        self._items: list[list[tuple[float, float, str]]] = [[] for _ in self.TRACK_NAMES]

        # カット情報（source → timeline変換用）
        self._keep_regions: list[tuple[float, float]] = []  # カット後に残る区間 (source_sec)

        # 範囲選択（BGM/効果用）
        self._dragging = False
        self._drag_start_ms = 0
        self._drag_end_ms = 0

    def set_post_cut_duration(self, ms: int):
        self._post_cut_duration_ms = max(1, ms)
        self.update()

    def set_position(self, ms: int):
        self._position_ms = ms
        self.update()

    def set_keep_regions(self, regions: list[tuple[float, float]]):
        """カット後に残っている区間を設定 (source_sec)"""
        self._keep_regions = regions

    def get_selection(self) -> tuple[float, float] | None:
        """選択範囲を(start_source_sec, end_source_sec)で返す"""
        if self._dragging or self._drag_start_ms == self._drag_end_ms:
            return None
        s = min(self._drag_start_ms, self._drag_end_ms) / 1000.0
        e = max(self._drag_start_ms, self._drag_end_ms) / 1000.0
        if e - s < 0.1:
            return None
        src_s = self.timeline_to_source(s)
        src_e = self.timeline_to_source(e)
        return (src_s, src_e)

    def clear_selection(self):
        self._drag_start_ms = 0
        self._drag_end_ms = 0
        self.update()

    def set_track_items(self, track_idx: int, items: list[tuple[float, float, str]]):
        """トラックにアイテムを設定 (カット後timeline_sec, end_sec, label)"""
        if 0 <= track_idx < len(self._items):
            self._items[track_idx] = items
            self.update()

    def source_to_timeline(self, source_sec: float) -> float | None:
        """カット前の絶対時間 → カット後タイムライン時間"""
        if not self._keep_regions:
            return source_sec
        offset = 0.0
        for ks, ke in self._keep_regions:
            if ks <= source_sec <= ke:
                return offset + (source_sec - ks)
            offset += ke - ks
        return None

    def timeline_to_source(self, timeline_sec: float) -> float:
        """カット後タイムライン時間 → カット前の絶対時間"""
        if not self._keep_regions:
            return timeline_sec
        remaining = timeline_sec
        for ks, ke in self._keep_regions:
            dur = ke - ks
            if remaining <= dur:
                return ks + remaining
            remaining -= dur
        return self._keep_regions[-1][1] if self._keep_regions else timeline_sec

    # --- 描画 ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor(30, 30, 30))

        lw = 60  # ラベル幅
        tw = w - lw  # トラック幅

        self._draw_ruler(painter, lw, 0, tw, self.RULER_H)

        y = self.RULER_H
        font = QFont("sans-serif", 10)
        painter.setFont(font)

        for i, name in enumerate(self.TRACK_NAMES):
            # ラベル
            painter.setPen(QPen(QColor(200, 200, 200)))
            painter.drawText(QRectF(2, y, lw - 4, self.TRACK_H), Qt.AlignVCenter | Qt.AlignRight, name)

            # トラック背景
            painter.fillRect(lw, y, tw, self.TRACK_H, QColor(45, 45, 45))

            # アイテム
            color = self.TRACK_COLORS[i]
            for start_s, end_s, label in self._items[i]:
                x1 = lw + int(start_s * 1000 / self._post_cut_duration_ms * tw)
                x2 = lw + int(end_s * 1000 / self._post_cut_duration_ms * tw)
                item_w = max(4, x2 - x1)
                painter.fillRect(x1, y + 2, item_w, self.TRACK_H - 4, color)
                # ラベル
                if item_w > 30:
                    painter.setPen(QPen(QColor(255, 255, 255, 220)))
                    painter.setFont(QFont("sans-serif", 8))
                    painter.drawText(QRectF(x1 + 2, y + 2, item_w - 4, self.TRACK_H - 4),
                                     Qt.AlignVCenter, label[:20])
                    painter.setFont(font)

            painter.setPen(QPen(QColor(55, 55, 55)))
            painter.drawLine(lw, y + self.TRACK_H, w, y + self.TRACK_H)
            y += self.TRACK_H

        # ドラッグ中の選択範囲
        if self._drag_start_ms != self._drag_end_ms:
            s = min(self._drag_start_ms, self._drag_end_ms)
            e = max(self._drag_start_ms, self._drag_end_ms)
            sx = lw + int(s / self._post_cut_duration_ms * tw)
            ex = lw + int(e / self._post_cut_duration_ms * tw)
            tracks_y = self.RULER_H
            tracks_h = self.TRACK_H * len(self.TRACK_NAMES)
            painter.fillRect(sx, tracks_y, ex - sx, tracks_h, QColor(100, 200, 255, 50))
            painter.setPen(QPen(QColor(100, 200, 255, 200), 2, Qt.DashLine))
            painter.drawRect(sx, tracks_y, ex - sx, tracks_h)

        # 再生位置
        if self._post_cut_duration_ms > 0:
            px = lw + int(self._position_ms / self._post_cut_duration_ms * tw)
            painter.setPen(QPen(QColor(255, 60, 60), 2))
            painter.drawLine(px, 0, px, h)

        painter.end()

    def _draw_ruler(self, painter: QPainter, x0: int, y0: int, w: int, h: int):
        painter.fillRect(x0, y0, w, h, QColor(50, 50, 50))
        painter.setPen(QPen(QColor(170, 170, 170)))
        dur_sec = self._post_cut_duration_ms / 1000.0
        if dur_sec <= 0:
            return
        interval = CutTimeline._calc_interval(dur_sec)
        font = QFont("sans-serif", 9)
        painter.setFont(font)
        t = 0.0
        while t <= dur_sec:
            px = x0 + int(t / dur_sec * w)
            painter.drawLine(px, y0 + h - 5, px, y0 + h)
            m, s = divmod(int(t), 60)
            painter.drawText(px + 3, y0 + h - 7, f"{m}:{s:02d}")
            t += interval

    # --- マウス ---

    def _x_to_ms(self, x: float) -> int:
        lw = 60
        tw = self.width() - lw
        if tw <= 0:
            return 0
        ratio = max(0.0, min(1.0, (x - lw) / tw))
        return int(ratio * self._post_cut_duration_ms)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if event.position().x() < 60:
                return
            ms = self._x_to_ms(event.position().x())
            self._dragging = True
            self._drag_start_ms = ms
            self._drag_end_ms = ms
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self._drag_end_ms = self._x_to_ms(event.position().x())
            # ドラッグ中にプレビューを同期
            self.scrub_position.emit(self._drag_end_ms)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._drag_end_ms = self._x_to_ms(event.position().x())
            s = min(self._drag_start_ms, self._drag_end_ms)
            e = max(self._drag_start_ms, self._drag_end_ms)
            if e - s < 50:
                # クリック（範囲なし）→ シーク＆選択クリア
                self._position_ms = self._drag_start_ms
                self.position_changed.emit(self._drag_start_ms)
                self._drag_start_ms = 0
                self._drag_end_ms = 0
            # 範囲選択はそのまま保持（ボタン押下で利用される）
            self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """ダブルクリックで挿入メニューを開く"""
        if event.button() == Qt.LeftButton:
            if event.position().x() < 60:
                return
            ms = self._x_to_ms(event.position().x())
            timeline_sec = ms / 1000.0
            source_sec = self.timeline_to_source(timeline_sec)
            self.insert_requested.emit(source_sec)
