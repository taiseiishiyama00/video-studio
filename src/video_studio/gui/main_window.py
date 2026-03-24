"""メインウィンドウ

レイアウト:
  上: 動画プレビュー（VideoDisplay: QVideoSink + オーバーレイ一体描画）
  下: タブ切替
    - 編集: CutTimeline + カット/速度変更
    - 挿入: InsertTimeline + 字幕/BGM/効果ボタン
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QApplication as _QApp  # processEvents用
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from video_studio.core.ffmpeg_utils import get_duration
from video_studio.core.project import (
    Annotation,
    BGMEntry,
    MosaicRegion,
    Project,
    SubtitleEntry,
)
from video_studio.core.timeline import Cut, SpeedRegion, Timeline, format_time
from video_studio.gui.dialogs.avatar_dialog import AvatarDialog
from video_studio.gui.dialogs.bgm_dialog import BGMDialog
from video_studio.gui.dialogs.effect_dialog import EffectDialog
from video_studio.gui.dialogs.insert_menu import show_insert_menu
from video_studio.gui.dialogs.speed_dialog import SpeedDialog
from video_studio.gui.dialogs.subtitle_dialog import SubtitleDialog
from video_studio.gui.render_dialog import RenderDialog
from video_studio.gui.theme import COLORS
from video_studio.gui.timeline_widget import CutTimeline, InsertTimeline
from video_studio.gui.undo_redo import Action, UndoRedoStack
from video_studio.gui.video_player import VideoPlayer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Studio")
        self.resize(1200, 850)

        self.project: Project | None = None
        self._source_duration: float = 0.0

        # Undo/Redo スタック（カットと挿入で独立）
        self._cut_undo = UndoRedoStack()
        self._insert_undo = UndoRedoStack()

        # 効果ワークフロー用の一時データ
        self._pending_effect: dict | None = None

        # TTSキャッシュ: SubtitleEntry → 生成済み音声ファイルパス
        self._tts_cache: dict[int, str] = {}  # id(entry) → path
        self._tts_dir = Path(tempfile.mkdtemp(prefix="vs_tts_"))
        self._tts_playing_id: int | None = None
        self._bgm_playing_entry: BGMEntry | None = None
        self._last_tts_error: str | None = None

        # ディレクトリ記憶
        self._settings = QSettings("VideoStudio", "VideoStudio")

        self._setup_menubar()
        self._setup_ui()
        self._setup_shortcuts()

    # =========================================================================
    # UI構築
    # =========================================================================

    def _setup_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("ファイル")
        file_menu.addAction("動画を開く...", self._open_video, "Ctrl+O")
        file_menu.addAction("プロジェクトを開く...", self._open_project, "Ctrl+Shift+O")
        file_menu.addAction("プロジェクトを保存...", self._save_project, "Ctrl+S")
        file_menu.addSeparator()
        file_menu.addAction("レンダリング...", self._start_render, "Ctrl+R")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # --- 動画プレイヤー（VideoDisplay 一体型） ---
        self.video_player = VideoPlayer()
        self.video_player.display.region_selected.connect(self._on_region_selected)
        main_layout.addWidget(self.video_player, stretch=3)

        # --- タブ切替 + タイムライン ---
        tab_panel = QWidget()
        tab_panel_layout = QVBoxLayout(tab_panel)
        tab_panel_layout.setContentsMargins(0, 0, 0, 0)
        tab_panel_layout.setSpacing(0)

        # タブバー
        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(0, 0, 0, 0)
        tab_bar.setSpacing(0)

        TAB_STYLE_BASE = """
            QPushButton {{
                padding: 8px 32px; font-size: 13px; font-weight: bold;
                border: none; border-bottom: 3px solid {border};
                background: {bg}; color: {fg};
                border-radius: 0px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
            }}
            QPushButton:hover {{ background: {hover}; }}
        """
        TAB_ACTIVE = TAB_STYLE_BASE.format(
            border=COLORS["accent"],
            bg=COLORS["bg_mid"],
            fg=COLORS["text_bright"],
            hover=COLORS["bg_mid"],
        )
        TAB_INACTIVE = TAB_STYLE_BASE.format(
            border="transparent",
            bg=COLORS["bg_darkest"],
            fg=COLORS["text_dim"],
            hover=COLORS["bg_dark"],
        )

        self.btn_tab_edit = QPushButton("編集")
        self.btn_tab_edit.setCursor(Qt.PointingHandCursor)
        self.btn_tab_edit.clicked.connect(lambda: self._switch_tab(0))
        tab_bar.addWidget(self.btn_tab_edit)

        self.btn_tab_insert = QPushButton("挿入")
        self.btn_tab_insert.setCursor(Qt.PointingHandCursor)
        self.btn_tab_insert.clicked.connect(lambda: self._switch_tab(1))
        tab_bar.addWidget(self.btn_tab_insert)

        tab_bar.addStretch()
        tab_panel_layout.addLayout(tab_bar)

        self._tab_style_active = TAB_ACTIVE
        self._tab_style_inactive = TAB_INACTIVE

        # スタックウィジェット
        self.mode_stack = QStackedWidget()

        # --- 編集モード ---
        cut_container = QWidget()
        cut_layout = QVBoxLayout(cut_container)
        cut_layout.setContentsMargins(0, 4, 0, 0)
        cut_layout.setSpacing(2)

        self.cut_timeline = CutTimeline()
        self.cut_timeline.position_changed.connect(self.video_player.seek)
        self.cut_timeline.cut_requested.connect(self._do_cut)
        self.cut_timeline.speed_requested.connect(self._do_speed)
        self.cut_timeline.scrub_position.connect(self._on_scrub)
        cut_layout.addWidget(self.cut_timeline, stretch=1)

        cut_bar = QHBoxLayout()
        cut_bar.setContentsMargins(4, 0, 4, 4)

        self.btn_mode_cut = QPushButton("✂ カット")
        self.btn_mode_cut.setCheckable(True)
        self.btn_mode_cut.setChecked(True)
        self.btn_mode_cut.setMaximumWidth(100)
        self.btn_mode_cut.clicked.connect(lambda: self._set_edit_mode("cut"))
        cut_bar.addWidget(self.btn_mode_cut)

        self.btn_mode_speed = QPushButton("⚡ 速度")
        self.btn_mode_speed.setCheckable(True)
        self.btn_mode_speed.setMaximumWidth(100)
        self.btn_mode_speed.clicked.connect(lambda: self._set_edit_mode("speed"))
        cut_bar.addWidget(self.btn_mode_speed)

        cut_bar.addSpacing(4)
        self.chk_edit_full = QCheckBox("全体")
        self.chk_edit_full.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 11px;"
        )
        cut_bar.addWidget(self.chk_edit_full)

        cut_bar.addSpacing(8)

        self.cut_info = QLabel("動画を開いてください")
        self.cut_info.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        cut_bar.addWidget(self.cut_info)
        cut_bar.addStretch()

        self.btn_cut_undo = QPushButton("元に戻す")
        self.btn_cut_undo.setEnabled(False)
        self.btn_cut_undo.clicked.connect(self._undo_cut)
        cut_bar.addWidget(self.btn_cut_undo)

        self.btn_cut_redo = QPushButton("やり直し")
        self.btn_cut_redo.setEnabled(False)
        self.btn_cut_redo.clicked.connect(self._redo_cut)
        cut_bar.addWidget(self.btn_cut_redo)

        cut_layout.addLayout(cut_bar)
        self.mode_stack.addWidget(cut_container)

        # --- 挿入モード ---
        insert_container = QWidget()
        insert_layout = QVBoxLayout(insert_container)
        insert_layout.setContentsMargins(0, 4, 0, 0)
        insert_layout.setSpacing(2)

        self.insert_timeline = InsertTimeline()
        self.insert_timeline.position_changed.connect(self._on_insert_seek)
        self.insert_timeline.scrub_position.connect(self._on_insert_scrub)
        self.insert_timeline.insert_requested.connect(self._show_insert_menu)
        insert_layout.addWidget(self.insert_timeline, stretch=1)

        # 挿入モード操作バー
        ins_bar = QHBoxLayout()
        ins_bar.setContentsMargins(4, 0, 4, 4)

        INSERT_BTN_STYLE = """
            QPushButton {
                padding: 5px 14px; font-size: 12px; font-weight: bold;
                background: %s; color: %s; border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background: %s; }
            QPushButton:disabled { background: %s; color: %s; }
        """ % (
            COLORS["accent_dark"],
            COLORS["text_bright"],
            COLORS["accent"],
            COLORS["bg_mid"],
            COLORS["border_light"],
        )

        self.btn_add_subtitle = QPushButton("+ 字幕")
        self.btn_add_subtitle.setStyleSheet(INSERT_BTN_STYLE)
        self.btn_add_subtitle.clicked.connect(self._insert_subtitle_at_current)
        ins_bar.addWidget(self.btn_add_subtitle)

        self.btn_add_bgm = QPushButton("+ BGM")
        self.btn_add_bgm.setStyleSheet(INSERT_BTN_STYLE)
        self.btn_add_bgm.clicked.connect(self._insert_bgm_at_current)
        ins_bar.addWidget(self.btn_add_bgm)

        self.btn_add_effect = QPushButton("+ 効果")
        self.btn_add_effect.setStyleSheet(INSERT_BTN_STYLE)
        self.btn_add_effect.clicked.connect(self._insert_effect_at_current)
        ins_bar.addWidget(self.btn_add_effect)

        self.btn_add_avatar = QPushButton("+ アバター")
        self.btn_add_avatar.setStyleSheet(INSERT_BTN_STYLE)
        self.btn_add_avatar.clicked.connect(self._configure_avatar)
        ins_bar.addWidget(self.btn_add_avatar)

        ins_bar.addSpacing(4)
        self.chk_insert_full = QCheckBox("全体")
        self.chk_insert_full.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 11px;"
        )
        ins_bar.addWidget(self.chk_insert_full)

        ins_bar.addSpacing(8)

        self.insert_info = QLabel("ドラッグで範囲選択 / 全体チェックで尺全体")
        self.insert_info.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 11px;"
        )
        ins_bar.addWidget(self.insert_info)
        ins_bar.addStretch()

        self.btn_ins_undo = QPushButton("元に戻す")
        self.btn_ins_undo.setEnabled(False)
        self.btn_ins_undo.clicked.connect(self._undo_insert)
        ins_bar.addWidget(self.btn_ins_undo)

        self.btn_ins_redo = QPushButton("やり直し")
        self.btn_ins_redo.setEnabled(False)
        self.btn_ins_redo.clicked.connect(self._redo_insert)
        ins_bar.addWidget(self.btn_ins_redo)

        insert_layout.addLayout(ins_bar)
        self.mode_stack.addWidget(insert_container)

        tab_panel_layout.addWidget(self.mode_stack, stretch=1)
        main_layout.addWidget(tab_panel, stretch=2)

        # 初期タブ状態
        self._switch_tab(0)

        # ステータスバー
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # 再生位置の連携
        self.video_player.position_updated.connect(self._on_position_updated)
        self.video_player.duration_updated.connect(self._on_duration_set)
        # 再生停止時にBGM/TTSも停止
        self.video_player.player.playbackStateChanged.connect(self._on_play_state)

    def _on_play_state(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        if state != QMediaPlayer.PlayingState:
            self._reset_overlay_audio_state()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_current)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self._redo_current)
        QShortcut(QKeySequence("Escape"), self, self._cancel_region_selection)

    # =========================================================================
    # 再生位置の連携
    # =========================================================================

    def _on_duration_set(self, ms: int):
        self._source_duration = ms / 1000.0
        self.cut_timeline.set_duration(ms)
        self._refresh_insert_timeline()

    def _on_position_updated(self, ms: int):
        self.cut_timeline.set_position(ms)
        if self.project:
            current_sec = ms / 1000.0
            # VideoDisplay にオーバーレイを即時反映
            self.video_player.display.update_overlays(self.project, current_sec)
            # 挿入タイムラインの再生位置バーを同期
            tl_ms = self.insert_timeline.source_to_timeline(current_sec)
            if tl_ms is not None:
                self.insert_timeline.set_position(int(tl_ms * 1000))
            # BGM / TTS プレビュー再生
            if self.video_player.is_playing():
                self._sync_overlay_audio(current_sec)

        # スマートプレビュー: カット区間スキップ & 速度変更
        if self.project and self.video_player.is_playing():
            self._apply_smart_playback(ms)

    def _on_scrub(self, ms: int):
        """ドラッグ中のスクラブ"""
        if self.video_player.is_playing():
            self.video_player.pause()
        self.video_player.seek(ms)

    def _apply_smart_playback(self, current_ms: int):
        """再生中にカット区間をスキップし、速度区間で再生速度を変更"""
        if not self.project:
            return

        current_sec = current_ms / 1000.0

        if self.project.timeline.cuts:
            in_kept = any(
                c.start <= current_sec <= c.end
                for c in self.project.timeline.cuts
            )
            if not in_kept:
                next_start = None
                for cut in sorted(self.project.timeline.cuts, key=lambda c: c.start):
                    if cut.start > current_sec:
                        next_start = cut.start
                        break
                if next_start is not None:
                    self.video_player.seek(int(next_start * 1000))
                else:
                    self.video_player.pause()
                return

        target_rate = 1.0
        for region in self.project.timeline.speed_regions:
            if region.start <= current_sec <= region.end:
                target_rate = region.speed
                break

        if abs(self.video_player.player.playbackRate() - target_rate) > 0.01:
            self.video_player.set_playback_rate(target_rate)

    def _on_insert_seek(self, post_cut_ms: int):
        """挿入タイムラインでのシーク"""
        source_sec = self.insert_timeline.timeline_to_source(post_cut_ms / 1000.0)
        self.video_player.seek(int(source_sec * 1000))

    def _on_insert_scrub(self, post_cut_ms: int):
        """挿入タイムラインでのドラッグ中スクラブ"""
        if self.video_player.is_playing():
            self.video_player.pause()
        source_sec = self.insert_timeline.timeline_to_source(post_cut_ms / 1000.0)
        self.video_player.seek(int(source_sec * 1000))

    def _switch_tab(self, index: int):
        self.mode_stack.setCurrentIndex(index)
        self.btn_tab_edit.setStyleSheet(
            self._tab_style_active if index == 0 else self._tab_style_inactive
        )
        self.btn_tab_insert.setStyleSheet(
            self._tab_style_active if index == 1 else self._tab_style_inactive
        )
        if index == 1:
            self._refresh_insert_timeline()

    # =========================================================================
    # 編集モード（カット・速度変更）
    # =========================================================================

    def _set_edit_mode(self, mode: str):
        if mode == "cut":
            self.btn_mode_cut.setChecked(True)
            self.btn_mode_speed.setChecked(False)
            self.cut_timeline.set_mode("cut")
        else:
            self.btn_mode_cut.setChecked(False)
            self.btn_mode_speed.setChecked(True)
            self.cut_timeline.set_mode("speed")

    def _do_cut(self, start: float, end: float):
        if not self.project:
            return

        old_cuts = list(self.project.timeline.cuts) if self.project.timeline.cuts else []

        def do_fn():
            if not self.project.timeline.cuts:
                self.project.timeline.cuts = [Cut(0.0, self._source_duration)]
            new_cuts = []
            for cut in self.project.timeline.cuts:
                if end <= cut.start or start >= cut.end:
                    new_cuts.append(cut)
                else:
                    if cut.start < start:
                        new_cuts.append(Cut(cut.start, start))
                    if end < cut.end:
                        new_cuts.append(Cut(end, cut.end))
            self.project.timeline.cuts = new_cuts
            self._refresh_cut_display()

        def undo_fn():
            self.project.timeline.cuts = old_cuts if old_cuts else []
            self._refresh_cut_display()

        action = Action(
            description=f"カット {format_time(start)} → {format_time(end)}",
            do_fn=do_fn, undo_fn=undo_fn,
        )
        self._cut_undo.execute(action)
        self._update_cut_buttons()

    def _refresh_cut_display(self):
        if not self.project:
            return
        cut_regions = self._calc_cut_regions()
        self.cut_timeline.set_cut_regions(cut_regions)

        speed_regions = [(r.start, r.end, r.speed) for r in self.project.timeline.speed_regions]
        self.cut_timeline.set_speed_regions(speed_regions)

        keep = self.project.timeline.cuts
        total_keep = sum(c.duration for c in keep) if keep else self._source_duration
        final_duration = self.project.timeline.duration

        self.cut_info.setText(
            f"最終尺: {format_time(final_duration)}  "
            f"(カット後: {format_time(total_keep)}, 元: {format_time(self._source_duration)})"
        )

        current_sec = self.video_player.get_position_sec()
        if self.project.timeline.cuts:
            in_kept = any(
                c.start <= current_sec <= c.end for c in self.project.timeline.cuts
            )
            if not in_kept:
                for cut in sorted(self.project.timeline.cuts, key=lambda c: c.start):
                    if cut.start >= current_sec:
                        self.video_player.seek(int(cut.start * 1000))
                        break

        self.video_player.set_playback_rate(1.0)
        self._refresh_insert_timeline()

    def _calc_cut_regions(self) -> list[tuple[float, float]]:
        if not self.project or not self.project.timeline.cuts:
            return []
        keep = sorted(self.project.timeline.cuts, key=lambda c: c.start)
        removed = []
        prev_end = 0.0
        for cut in keep:
            if cut.start > prev_end:
                removed.append((prev_end, cut.start))
            prev_end = cut.end
        if prev_end < self._source_duration:
            removed.append((prev_end, self._source_duration))
        return removed

    def _undo_cut(self):
        desc = self._cut_undo.undo()
        if desc:
            self.status.showMessage(f"元に戻しました: {desc}", 3000)
        self._update_cut_buttons()

    def _redo_cut(self):
        desc = self._cut_undo.redo()
        if desc:
            self.status.showMessage(f"やり直しました: {desc}", 3000)
        self._update_cut_buttons()

    def _do_speed(self, start: float, end: float, default_speed: float):
        if not self.project:
            return
        # 全体チェック時は尺全体に適用
        if self.chk_edit_full.isChecked():
            start, end = 0.0, self._source_duration
        dlg = SpeedDialog(start, end, self)
        if dlg.exec() != SpeedDialog.Accepted:
            return
        speed = dlg.get_speed()
        if speed <= 0.0:
            return

        new_region = SpeedRegion(start, end, speed)
        old_regions = list(self.project.timeline.speed_regions)

        def do_fn():
            self.project.timeline.speed_regions = [
                r for r in self.project.timeline.speed_regions
                if not (max(r.start, start) < min(r.end, end))
            ]
            self.project.timeline.speed_regions.append(new_region)
            self.project.timeline.speed_regions.sort(key=lambda r: r.start)
            self._refresh_cut_display()

        def undo_fn():
            self.project.timeline.speed_regions = old_regions
            self._refresh_cut_display()

        action = Action(
            description=f"速度変更 {format_time(start)}→{format_time(end)}: {speed:.1f}x",
            do_fn=do_fn, undo_fn=undo_fn,
        )
        self._cut_undo.execute(action)
        self._update_cut_buttons()

    def _update_cut_buttons(self):
        self.btn_cut_undo.setEnabled(self._cut_undo.can_undo())
        self.btn_cut_redo.setEnabled(self._cut_undo.can_redo())

    # =========================================================================
    # 挿入操作
    # =========================================================================

    def _refresh_insert_timeline(self):
        if not self.project:
            return
        keep = self.project.timeline.cuts
        if keep:
            keep_regions = [(c.start, c.end) for c in sorted(keep, key=lambda c: c.start)]
            post_cut_dur = sum(c.duration for c in keep)
        else:
            keep_regions = [(0.0, self._source_duration)]
            post_cut_dur = self._source_duration

        self.insert_timeline.set_keep_regions(keep_regions)
        self.insert_timeline.set_post_cut_duration(int(post_cut_dur * 1000))

        # track 0: 字幕
        sub_items = []
        for s in self.project.subtitle_track:
            t = self.insert_timeline.source_to_timeline(s.time)
            if t is not None:
                dur = s.duration or 3.0
                sub_items.append((t, t + dur, s.text))
        self.insert_timeline.set_track_items(0, sub_items)

        # track 1: BGM
        bgm_items = []
        post_cut_dur_sec = post_cut_dur
        for b in self.project.bgm_track:
            ts = self.insert_timeline.source_to_timeline(b.start)
            te = self.insert_timeline.source_to_timeline(b.end)
            if ts is None:
                ts = 0.0
            if te is None:
                te = post_cut_dur_sec
            src = Path(b.source).name if b.source else "(無音)"
            bgm_items.append((ts, te, src))
        self.insert_timeline.set_track_items(1, bgm_items)

        # track 2: モザイク/効果
        mos_items = []
        for m in self.project.mosaic_regions:
            ts = self.insert_timeline.source_to_timeline(m.start)
            te = self.insert_timeline.source_to_timeline(m.end)
            if ts is not None and te is not None:
                label = "ぼかし" if m.mode == "blur" else "モザイク"
                mos_items.append((ts, te, label))
        self.insert_timeline.set_track_items(2, mos_items)

        # track 3: 強調
        ann_items = []
        for a in self.project.annotations:
            ts = self.insert_timeline.source_to_timeline(a.start)
            te = self.insert_timeline.source_to_timeline(a.end)
            if ts is not None and te is not None:
                names = {"circle": "丸", "arrow": "矢印", "rect_highlight": "矩形"}
                ann_items.append((ts, te, names.get(a.type, a.type)))
        self.insert_timeline.set_track_items(3, ann_items)

        # track 4: アバター
        if self.project.avatar:
            avatar_items = [(s[0], s[1], "アバター") for s in sub_items]
            self.insert_timeline.set_track_items(4, avatar_items)
        else:
            self.insert_timeline.set_track_items(4, [])

    def _get_current_source_time(self) -> float:
        return self.video_player.get_position_sec()

    def _configure_avatar(self):
        """アバター設定ダイアログを開く"""
        if not self.project:
            return
        dlg = AvatarDialog(self.project.avatar, self)
        if dlg.exec() == AvatarDialog.Accepted:
            old_avatar = self.project.avatar
            new_avatar = dlg.get_config()

            def do_fn():
                self.project.avatar = new_avatar
                self._refresh_insert_timeline()
                self._refresh_preview()
                if new_avatar:
                    self._settings.setValue("avatar/image", new_avatar.image)
                    self._settings.setValue("avatar/image_mouth_open", new_avatar.image_mouth_open)
                    self._settings.setValue("avatar/image_blink", new_avatar.image_blink)
                    self._settings.setValue("avatar/position", new_avatar.position)
                    self._settings.setValue("avatar/scale", new_avatar.scale)

            def undo_fn():
                self.project.avatar = old_avatar
                self._refresh_insert_timeline()
                self._refresh_preview()

            desc = "アバター設定" if new_avatar else "アバター無効化"
            action = Action(description=desc, do_fn=do_fn, undo_fn=undo_fn)
            self._insert_undo.execute(action)
            self._update_insert_buttons()

    def _insert_subtitle_at_current(self):
        if self.project:
            self._insert_subtitle(self._get_current_source_time())

    def _get_insert_range(self) -> tuple[float, float] | None:
        """全体チェックまたはタイムライン選択から範囲を取得"""
        if self.chk_insert_full.isChecked():
            return (0.0, self._source_duration)
        sel = self.insert_timeline.get_selection()
        if sel:
            self.insert_timeline.clear_selection()
            return sel
        return None

    def _insert_bgm_at_current(self):
        if not self.project:
            return
        rng = self._get_insert_range()
        if rng:
            self._insert_bgm_range(rng[0], rng[1])
        else:
            self._insert_bgm(self._get_current_source_time())

    def _insert_bgm_range(self, start: float, end: float):
        """範囲選択済みのBGM挿入"""
        dlg = BGMDialog(start, self)
        # 終了時間をプリセット
        dlg.end_input.setText(format_time(end))
        if dlg.exec() == BGMDialog.Accepted:
            entry = dlg.get_entry()
            if entry:
                self._do_insert(
                    desc=f"BGM {format_time(entry.start)}→{format_time(entry.end)}",
                    add_fn=lambda: self.project.bgm_track.append(entry),
                    remove_fn=lambda: self.project.bgm_track.remove(entry),
                )

    def _insert_effect_at_current(self):
        """効果挿入: タイムライン範囲 → ダイアログ → プレビュー上で範囲選択"""
        if not self.project:
            return
        rng = self._get_insert_range()
        if rng:
            source_time = rng[0]
            end_time = rng[1]
        else:
            source_time = self._get_current_source_time()
            end_time = source_time + 5

        dlg = EffectDialog(source_time, self)
        dlg.end_input.setText(format_time(end_time))
        if dlg.exec() != EffectDialog.Accepted:
            return
        params = dlg.get_params()
        if not params:
            return

        self._pending_effect = params
        self.video_player.display.start_region_selection()
        self.status.showMessage(
            "動画プレビュー上でドラッグして効果範囲を選択してください（Escでキャンセル）", 0
        )

    def _cancel_region_selection(self):
        """Escで範囲選択をキャンセル"""
        if self.video_player.display.is_selecting_region() or self._pending_effect:
            self.video_player.display.cancel_region_selection()
            self._pending_effect = None
            self.status.clearMessage()

    def _on_region_selected(self, x: int, y: int, w: int, h: int):
        """プレビュー上で範囲が選択された → 効果を作成"""
        self.status.clearMessage()
        if not self._pending_effect or not self.project:
            return

        params = self._pending_effect
        self._pending_effect = None
        effect_type = params["effect_type"]
        start = params["start"]
        end = params["end"]

        if effect_type in ("pixelate", "blur"):
            entry = MosaicRegion(
                rect=(x, y, w, h),
                start=start,
                end=end,
                mode=effect_type,
                strength=params.get("strength", 20),
            )
            self._do_insert(
                desc=f"効果({effect_type}) {format_time(start)}→{format_time(end)}",
                add_fn=lambda: self.project.mosaic_regions.append(entry),
                remove_fn=lambda: self.project.mosaic_regions.remove(entry),
            )
        elif effect_type == "circle":
            cx, cy, r = x + w // 2, y + h // 2, min(w, h) // 2
            entry = Annotation(
                type="circle",
                position=(cx, cy, r),
                start=start,
                end=end,
                color=params.get("color", "#FF0000"),
                thickness=params.get("thickness", 3),
            )
            self._do_insert(
                desc=f"効果(丸) {format_time(start)}→{format_time(end)}",
                add_fn=lambda: self.project.annotations.append(entry),
                remove_fn=lambda: self.project.annotations.remove(entry),
            )
        elif effect_type == "arrow":
            entry = Annotation(
                type="arrow",
                position=(x, y, x + w, y + h),
                start=start,
                end=end,
                color=params.get("color", "#FF0000"),
                thickness=params.get("thickness", 3),
            )
            self._do_insert(
                desc=f"効果(矢印) {format_time(start)}→{format_time(end)}",
                add_fn=lambda: self.project.annotations.append(entry),
                remove_fn=lambda: self.project.annotations.remove(entry),
            )
        elif effect_type == "rect_highlight":
            entry = Annotation(
                type="rect_highlight",
                position=(x, y, w, h),
                start=start,
                end=end,
                color=params.get("color", "#FF0000"),
                thickness=params.get("thickness", 3),
            )
            self._do_insert(
                desc=f"効果(矩形) {format_time(start)}→{format_time(end)}",
                add_fn=lambda: self.project.annotations.append(entry),
                remove_fn=lambda: self.project.annotations.remove(entry),
            )

    def _show_insert_menu(self, source_time: float):
        if not self.project:
            return
        from PySide6.QtGui import QCursor
        show_insert_menu(
            parent=self,
            source_time=source_time,
            pos=QCursor.pos(),
            on_subtitle=self._insert_subtitle,
            on_bgm=self._insert_bgm,
            on_mosaic=lambda t: self._insert_effect_at_time(t),
            on_annotation=lambda t: self._insert_effect_at_time(t),
        )

    def _insert_effect_at_time(self, source_time: float):
        """ダブルクリックメニューからの効果挿入"""
        if not self.project:
            return
        dlg = EffectDialog(source_time, self)
        if dlg.exec() != EffectDialog.Accepted:
            return
        params = dlg.get_params()
        if not params:
            return
        self._pending_effect = params
        self.video_player.display.start_region_selection()
        self.status.showMessage(
            "動画プレビュー上でドラッグして効果範囲を選択（Escでキャンセル）", 0
        )

    def _insert_subtitle(self, source_time: float):
        dlg = SubtitleDialog(source_time, self)
        if dlg.exec() == SubtitleDialog.Accepted:
            entry = dlg.get_entry()
            if entry:
                # TTS音声を先に生成（同期）してからInsert
                if not self._generate_tts_sync(entry):
                    detail = self._last_tts_error or "不明なエラー"
                    QMessageBox.warning(
                        self,
                        "TTS生成失敗",
                        "字幕用の機械音声を生成できなかったため、字幕は追加していません。\n\n"
                        f"詳細: {detail}",
                    )
                    return
                self._do_insert(
                    desc=f"字幕「{entry.text}」",
                    add_fn=lambda: self.project.subtitle_track.append(entry),
                    remove_fn=lambda: self.project.subtitle_track.remove(entry),
                )

    def _insert_bgm(self, source_time: float):
        dlg = BGMDialog(source_time, self)
        if dlg.exec() == BGMDialog.Accepted:
            entry = dlg.get_entry()
            if entry:
                self._do_insert(
                    desc=f"BGM {format_time(entry.start)}→{format_time(entry.end)}",
                    add_fn=lambda: self.project.bgm_track.append(entry),
                    remove_fn=lambda: self.project.bgm_track.remove(entry),
                )

    def _do_insert(self, desc: str, add_fn, remove_fn):
        """挿入操作を実行（Undo可能 + プレビュー即時更新）"""
        def do_fn():
            add_fn()
            self._refresh_insert_timeline()
            self._refresh_preview()

        def undo_fn():
            remove_fn()
            self._refresh_insert_timeline()
            self._refresh_preview()

        action = Action(description=desc, do_fn=do_fn, undo_fn=undo_fn)
        self._insert_undo.execute(action)
        self._update_insert_buttons()

    def _refresh_preview(self):
        """プレビューを現在の再生位置で即時更新"""
        if self.project:
            current_sec = self.video_player.get_position_sec()
            self.video_player.display.update_overlays(self.project, current_sec)

    # --- BGM / TTS プレビュー再生 ---

    def _sync_overlay_audio(self, current_sec: float):
        """再生位置に応じてBGM/TTSを再生・停止"""
        if not self.project:
            return

        # BGM
        bgm_active = None
        for b in self.project.bgm_track:
            if b.start <= current_sec <= b.end and b.source:
                bgm_active = b
                break
        if bgm_active:
            offset = current_sec - bgm_active.start
            if self._bgm_playing_entry is not bgm_active:
                self._bgm_playing_entry = bgm_active
                self.video_player.play_bgm(bgm_active.source, bgm_active.volume, offset)
        else:
            if self._bgm_playing_entry:
                self._bgm_playing_entry = None
                self.video_player.stop_bgm()

        # TTS
        tts_active = None
        for sub in self.project.subtitle_track:
            dur = sub.duration or 3.0
            if sub.time <= current_sec <= sub.time + dur:
                tts_active = sub
                break
        if tts_active:
            entry_id = id(tts_active)
            speaking = self._tts_playing_id == entry_id
            if self._tts_playing_id != entry_id and self._ensure_tts_cache(tts_active):
                playback_sec = self.video_player.get_position_sec()
                self._tts_playing_id = entry_id
                self.video_player.play_tts(
                    self._tts_cache[entry_id],
                    tts_active.tts_volume,
                    max(0.0, playback_sec - tts_active.time),
                )
                speaking = True
            self.video_player.display.set_avatar_speaking(speaking)
        else:
            if self._tts_playing_id is not None:
                self._tts_playing_id = None
                self.video_player.stop_tts()
            self.video_player.display.set_avatar_speaking(False)

    def _ensure_tts_cache(self, entry: SubtitleEntry) -> bool:
        entry_id = id(entry)
        cached = self._tts_cache.get(entry_id)
        if cached and Path(cached).exists():
            return True
        return self._generate_tts_sync(entry)

    def _generate_tts_sync(self, entry: SubtitleEntry) -> bool:
        """TTS音声を同期生成しキャッシュに登録"""
        entry_id = id(entry)
        cached = self._tts_cache.get(entry_id)
        if cached and Path(cached).exists():
            return True
        output_path = str(self._tts_dir / f"tts_{entry_id}.mp3")
        self.status.showMessage(f"TTS生成中: {entry.text[:20]}...")
        _QApp.processEvents()
        try:
            from video_studio.subtitles.tts import generate_tts
            duration = generate_tts(entry.text, entry.voice, output_path)
            self._tts_cache[entry_id] = output_path
            if entry.duration is None:
                entry.duration = duration
            self._last_tts_error = None
            self.status.showMessage(f"TTS生成完了 ({duration:.1f}秒)", 3000)
            return True
        except Exception as e:
            Path(output_path).unlink(missing_ok=True)
            self._last_tts_error = str(e)
            self.status.showMessage(f"TTS生成失敗: {e}", 5000)
            print(f"[TTS] Generation failed: {e}")
            return False

    def _reset_overlay_audio_state(self, clear_tts_cache: bool = False):
        self.video_player.stop_all_overlay_audio()
        self.video_player.display.set_avatar_speaking(False)
        self._bgm_playing_entry = None
        self._tts_playing_id = None

        if clear_tts_cache:
            for path in self._tts_cache.values():
                Path(path).unlink(missing_ok=True)
            self._tts_cache.clear()

    def _undo_insert(self):
        desc = self._insert_undo.undo()
        if desc:
            self.status.showMessage(f"元に戻しました: {desc}", 3000)
        self._update_insert_buttons()

    def _redo_insert(self):
        desc = self._insert_undo.redo()
        if desc:
            self.status.showMessage(f"やり直しました: {desc}", 3000)
        self._update_insert_buttons()

    def _update_insert_buttons(self):
        self.btn_ins_undo.setEnabled(self._insert_undo.can_undo())
        self.btn_ins_redo.setEnabled(self._insert_undo.can_redo())

    # =========================================================================
    # Undo/Redo ショートカット
    # =========================================================================

    def _undo_current(self):
        if self.mode_stack.currentIndex() == 0:
            self._undo_cut()
        else:
            self._undo_insert()

    def _redo_current(self):
        if self.mode_stack.currentIndex() == 0:
            self._redo_cut()
        else:
            self._redo_insert()

    # =========================================================================
    # ファイル操作
    # =========================================================================

    def _last_dir(self, key: str) -> str:
        return self._settings.value(f"last_dir/{key}", "")

    def _save_dir(self, key: str, path: str):
        self._settings.setValue(f"last_dir/{key}", str(Path(path).parent))

    def _restore_avatar_from_settings(self):
        """QSettingsからアバター設定を復元（プロジェクトにアバターが未設定の場合）"""
        if self.project and not self.project.avatar:
            image = self._settings.value("avatar/image", "")
            if image and Path(image).exists():
                from video_studio.core.project import AvatarConfig
                self.project.avatar = AvatarConfig(
                    image=image,
                    image_mouth_open=self._settings.value("avatar/image_mouth_open", ""),
                    image_blink=self._settings.value("avatar/image_blink", ""),
                    position=self._settings.value("avatar/position", "bottom-right"),
                    scale=float(self._settings.value("avatar/scale", 0.25)),
                )

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "動画を開く", self._last_dir("video"),
            "動画ファイル (*.mp4 *.mov *.avi *.mkv *.webm);;すべて (*)",
        )
        if not path:
            return
        self._save_dir("video", path)
        try:
            self._reset_overlay_audio_state(clear_tts_cache=True)
            self._source_duration = get_duration(path)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"動画のプロパティ取得失敗:\n{e}")
            return

        try:
            self.project = Project(source=path)
            self.project.timeline.source_duration = self._source_duration
            self._restore_avatar_from_settings()
            self.video_player.load(path)
            self._on_duration_set(int(self._source_duration * 1000))

            self._cut_undo.clear()
            self._insert_undo.clear()
            self._refresh_cut_display()
            self._refresh_insert_timeline()
            self._update_cut_buttons()
            self._update_insert_buttons()
            self.video_player.display.clear_overlays()
            self.setWindowTitle(f"Video Studio - {Path(path).name}")
            self.status.showMessage(f"読み込み完了: {Path(path).name}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"動画の読み込み失敗:\n{e}")
            import traceback
            traceback.print_exc()

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "プロジェクトを開く", self._last_dir("project"),
            "プロジェクト (*.json);;すべて (*)",
        )
        if not path:
            return
        self._save_dir("project", path)
        try:
            self._reset_overlay_audio_state(clear_tts_cache=True)
            self.project = Project.from_json(path)
            self._source_duration = get_duration(self.project.source)
            self.project.timeline.source_duration = self._source_duration
            self._restore_avatar_from_settings()
            self.video_player.load(self.project.source)
            self._cut_undo.clear()
            self._insert_undo.clear()
            self._refresh_cut_display()
            self._refresh_insert_timeline()
            self.setWindowTitle(f"Video Studio - {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"読み込み失敗:\n{e}")

    def _save_project(self):
        if not self.project:
            QMessageBox.warning(self, "警告", "先に動画を開いてください。")
            return
        default = str(Path(self._last_dir("project_save") or ".") / "project.json")
        path, _ = QFileDialog.getSaveFileName(self, "保存", default, "JSON (*.json)")
        if path:
            self._save_dir("project_save", path)
            self.project.save_json(path)
            self.status.showMessage(f"保存しました: {path}", 3000)

    def _start_render(self):
        if not self.project:
            QMessageBox.warning(self, "警告", "先に動画を開いてください。")
            return
        default = str(Path(self._last_dir("render") or ".") / "output.mp4")
        path, _ = QFileDialog.getSaveFileName(self, "出力先", default, "動画 (*.mp4)")
        if not path:
            return
        self._save_dir("render", path)
        self.project.output = path
        dialog = RenderDialog(self.project, self)
        dialog.exec()
