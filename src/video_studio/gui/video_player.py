"""動画プレビュープレイヤー

QVideoSink でフレーム取得 + オーバーレイ一体描画。
音声は QAudioOutput で明示的にデフォルトデバイスへ出力。
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QUrl, Signal, Slot, QSettings, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPen
from PySide6.QtMultimedia import (
    QAudioOutput,
    QMediaDevices,
    QMediaPlayer,
    QVideoFrame,
    QVideoSink,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from video_studio.core.project import Annotation, MosaicRegion, Project, SubtitleEntry


class VideoDisplay(QWidget):
    """動画フレーム + オーバーレイを同一ウィジェットに描画"""

    region_selected = Signal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 180)

        # 自前の QVideoSink
        self._sink = QVideoSink(self)
        self._sink.videoFrameChanged.connect(self._on_frame)
        self._current_image: QImage | None = None

        # オーバーレイデータ
        self._subtitles: list[SubtitleEntry] = []
        self._mosaic_regions: list[MosaicRegion] = []
        self._annotations: list[Annotation] = []
        self._avatar_rect: tuple[int, int, int, int] | None = None
        self._current_time = 0.0

        # アバター3画像リップシンク
        self._avatar_imgs: dict[str, QImage | None] = {
            "neutral": None, "mouth": None, "blink": None,
        }
        self._avatar_loaded_paths: tuple[str, str, str] = ("", "", "")
        self._avatar_speaking = False  # TTS再生中フラグ
        self._avatar_frame = 0  # アニメーションフレーム
        self._avatar_blink_counter = 0
        self._playback_active = False  # 再生中フラグ

        # リップシンクタイマー（150msごとに口パク切替）
        self._lipsync_timer = QTimer(self)
        self._lipsync_timer.setInterval(150)
        self._lipsync_timer.timeout.connect(self._on_lipsync_tick)
        self._lipsync_timer.start()

        # 範囲選択モード
        self._selecting = False
        self._sel_start: QPointF | None = None
        self._sel_end: QPointF | None = None

    @property
    def video_sink(self) -> QVideoSink:
        return self._sink

    def _on_frame(self, frame: QVideoFrame):
        img = frame.toImage()
        if not img.isNull():
            self._current_image = img
            self.update()

    # --- 動画領域 ---

    def _video_rect(self) -> QRectF:
        if not self._current_image:
            return QRectF(0, 0, self.width(), self.height())
        iw, ih = self._current_image.width(), self._current_image.height()
        ww, wh = self.width(), self.height()
        scale = min(ww / max(1, iw), wh / max(1, ih))
        dw, dh = iw * scale, ih * scale
        return QRectF((ww - dw) / 2, (wh - dh) / 2, dw, dh)

    def _widget_to_ref(self, pos: QPointF) -> tuple[int, int]:
        vr = self._video_rect()
        if vr.width() == 0 or vr.height() == 0:
            return (0, 0)
        ref_w, ref_h = self._reference_size()
        rx = (pos.x() - vr.x()) / vr.width() * ref_w
        ry = (pos.y() - vr.y()) / vr.height() * ref_h
        return (max(0, min(ref_w, int(rx))), max(0, min(ref_h, int(ry))))

    def _scale_overlay_rect(self, rect) -> tuple[int, int, int, int]:
        vr = self._video_rect()
        ref_w, ref_h = self._reference_size()
        sx, sy = vr.width() / max(1, ref_w), vr.height() / max(1, ref_h)
        return (
            int(vr.x() + rect[0] * sx), int(vr.y() + rect[1] * sy),
            int(rect[2] * sx), int(rect[3] * sy),
        )

    def _reference_size(self) -> tuple[int, int]:
        if self._current_image and not self._current_image.isNull():
            return (self._current_image.width(), self._current_image.height())
        return (1920, 1080)

    def _clamp_frame_rect(self, rect) -> tuple[int, int, int, int]:
        ref_w, ref_h = self._reference_size()
        x, y, w, h = rect
        x = max(0, min(x, ref_w - 1))
        y = max(0, min(y, ref_h - 1))
        w = max(1, min(w, ref_w - x))
        h = max(1, min(h, ref_h - y))
        return (x, y, w, h)

    # --- オーバーレイ ---

    def clear_overlays(self):
        self._subtitles = []
        self._mosaic_regions = []
        self._annotations = []
        self._avatar_rect = None
        self._avatar_imgs = {"neutral": None, "mouth": None, "blink": None}
        self._avatar_loaded_paths = ("", "", "")
        self._avatar_speaking = False
        self.update()

    def set_avatar_speaking(self, speaking: bool):
        """TTS再生中かどうかをセット（リップシンク制御用）"""
        self._avatar_speaking = speaking

    def set_playback_active(self, active: bool):
        """再生中かどうかをセット（停止中はアニメーション停止）"""
        self._playback_active = active
        if not active:
            self._avatar_frame = 0
            self._avatar_blink_counter = 1
            self.update()

    def _on_lipsync_tick(self):
        """150msごとにリップシンクアニメーションを更新"""
        if not self._avatar_rect or not self._avatar_imgs["neutral"]:
            return
        if not self._playback_active:
            return
        self._avatar_frame += 1
        # まばたき: 約3秒に1回（20フレームに1回）
        self._avatar_blink_counter += 1
        if self._avatar_blink_counter >= 20 + random.randint(0, 10):
            self._avatar_blink_counter = 0
        self.update()

    def _get_current_avatar_image(self) -> QImage | None:
        """現在表示すべきアバター画像を返す"""
        imgs = self._avatar_imgs
        # まばたき中（2フレーム = 300ms）
        if self._avatar_blink_counter == 0 and imgs["blink"]:
            return imgs["blink"]
        # 発話中: 口パク（フレームごとに開閉）
        if self._avatar_speaking and imgs["mouth"]:
            return imgs["mouth"] if self._avatar_frame % 2 == 0 else imgs["neutral"]
        # ニュートラル
        return imgs["neutral"]

    def update_overlays(self, project: Project, current_time: float):
        self._current_time = current_time
        self._subtitles = project.subtitle_track
        self._mosaic_regions = project.mosaic_regions
        self._annotations = project.annotations
        if project.avatar:
            vr = self._video_rect()
            w, h = vr.width(), vr.height()
            size = int(min(w, h) * project.avatar.scale)
            margin = 10
            positions = {
                "bottom-right": (int(vr.x() + w - size - margin), int(vr.y() + h - size - margin)),
                "bottom-left": (int(vr.x() + margin), int(vr.y() + h - size - margin)),
                "top-right": (int(vr.x() + w - size - margin), int(vr.y() + margin)),
                "top-left": (int(vr.x() + margin), int(vr.y() + margin)),
            }
            x, y = positions.get(project.avatar.position, positions["bottom-right"])
            self._avatar_rect = (x, y, size, size)
            # 3画像をロード（パスが変わった場合のみ）
            paths = (project.avatar.image, project.avatar.image_mouth_open, project.avatar.image_blink)
            if paths != self._avatar_loaded_paths:
                self._avatar_loaded_paths = paths
                for key, p in [("neutral", paths[0]), ("mouth", paths[1]), ("blink", paths[2])]:
                    if p:
                        img = QImage(p)
                        self._avatar_imgs[key] = img if not img.isNull() else None
                    else:
                        self._avatar_imgs[key] = None
        else:
            self._avatar_rect = None
            self._avatar_imgs = {"neutral": None, "mouth": None, "blink": None}
            self._avatar_loaded_paths = ("", "", "")
        self.update()

    # --- 範囲選択 ---

    def start_region_selection(self):
        self._selecting = True
        self._sel_start = None
        self._sel_end = None
        self.setCursor(Qt.CrossCursor)

    def cancel_region_selection(self):
        self._selecting = False
        self._sel_start = self._sel_end = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def is_selecting_region(self) -> bool:
        return self._selecting

    def mousePressEvent(self, event: QMouseEvent):
        if self._selecting and event.button() == Qt.LeftButton:
            self._sel_start = self._sel_end = event.position()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._selecting and self._sel_start:
            self._sel_end = event.position()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._selecting and event.button() == Qt.LeftButton and self._sel_start:
            self._sel_end = event.position()
            self._selecting = False
            self.setCursor(Qt.ArrowCursor)
            x1, y1 = self._widget_to_ref(self._sel_start)
            x2, y2 = self._widget_to_ref(self._sel_end)
            rx, ry = min(x1, x2), min(y1, y2)
            rw, rh = abs(x2 - x1), abs(y2 - y1)
            if rw > 10 and rh > 10:
                self.region_selected.emit(rx, ry, rw, rh)
            self._sel_start = self._sel_end = None
            self.update()
        super().mouseReleaseEvent(event)

    # --- 描画 ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        if self._current_image:
            painter.drawImage(self._video_rect(), self._current_image)

        t = self._current_time

        for region in self._mosaic_regions:
            if region.start <= t <= region.end:
                self._draw_mosaic_preview(painter, region)
                rx, ry, rw, rh = self._scale_overlay_rect(self._clamp_frame_rect(region.rect))
                painter.setPen(QPen(QColor(200, 100, 200, 200), 2, Qt.DashLine))
                painter.setBrush(QColor(200, 100, 200, 30))
                painter.drawRect(rx, ry, rw, rh)
                painter.setPen(QPen(QColor(255, 255, 255, 200)))
                painter.setFont(QFont("sans-serif", 9))
                painter.drawText(rx + 4, ry + 14, "ぼかし" if region.mode == "blur" else "モザイク")

        for annot in self._annotations:
            if annot.start <= t <= annot.end:
                self._draw_annotation(painter, annot)

        for sub in self._subtitles:
            dur = sub.duration or 3.0
            if sub.time <= t <= sub.time + dur:
                self._draw_subtitle(painter, sub.text)

        if self._avatar_rect:
            x, y, w, h = self._avatar_rect
            avatar_img = self._get_current_avatar_image()
            if avatar_img:
                painter.drawImage(QRectF(x, y, w, h), avatar_img)
            else:
                painter.setPen(QPen(QColor(100, 220, 220, 120), 1, Qt.DashLine))
                painter.setBrush(QColor(30, 30, 30, 150))
                painter.drawRect(x, y, w, h)
                painter.setPen(QPen(QColor(200, 200, 200, 150)))
                painter.setFont(QFont("sans-serif", 9))
                painter.drawText(QRectF(x, y, w, h), Qt.AlignCenter, "アバター")

        if self._sel_start and self._sel_end:
            painter.setPen(QPen(QColor(0, 200, 255, 220), 2, Qt.DashLine))
            painter.setBrush(QColor(0, 200, 255, 40))
            painter.drawRect(QRectF(self._sel_start, self._sel_end).normalized())
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("sans-serif", 12, QFont.Bold))
            painter.drawText(QRectF(0, 4, self.width(), 24), Qt.AlignHCenter,
                             "ドラッグで効果範囲を選択中...")

        painter.end()

    def _draw_subtitle(self, painter: QPainter, text: str):
        vr = self._video_rect()
        painter.setFont(QFont("sans-serif", 14, QFont.Bold))
        text_rect = QRectF(vr.x() + 10, vr.y() + vr.height() - 36, vr.width() - 20, 30)
        painter.fillRect(text_rect, QColor(0, 0, 0, 160))
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(text_rect, Qt.AlignCenter, text)

    def _draw_mosaic_preview(self, painter: QPainter, region: MosaicRegion):
        if not self._current_image:
            return

        x, y, w, h = self._clamp_frame_rect(region.rect)
        source = self._current_image.copy(x, y, w, h)
        if source.isNull():
            return

        target = QRectF(*self._scale_overlay_rect((x, y, w, h)))
        strength = max(1, region.strength)
        small_w = max(1, w // strength)
        small_h = max(1, h // strength)

        if region.mode == "blur":
            reduced = source.scaled(
                small_w,
                small_h,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            preview = reduced.scaled(
                w,
                h,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
        else:
            reduced = source.scaled(
                small_w,
                small_h,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation,
            )
            preview = reduced.scaled(
                w,
                h,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation,
            )

        painter.drawImage(target, preview)

    def _draw_annotation(self, painter: QPainter, annot: Annotation):
        color = QColor(annot.color)
        color.setAlpha(200)
        painter.setPen(QPen(color, annot.thickness))
        painter.setBrush(Qt.NoBrush)
        pos = annot.position
        vr = self._video_rect()
        ref_w, ref_h = self._reference_size()
        sx, sy = vr.width() / max(1, ref_w), vr.height() / max(1, ref_h)

        if annot.type == "circle" and len(pos) >= 3:
            cx, cy = vr.x() + pos[0] * sx, vr.y() + pos[1] * sy
            r = pos[2] * min(sx, sy)
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        elif annot.type == "arrow" and len(pos) >= 4:
            x1, y1 = vr.x() + pos[0] * sx, vr.y() + pos[1] * sy
            x2, y2 = vr.x() + pos[2] * sx, vr.y() + pos[3] * sy
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            angle = math.atan2(y2 - y1, x2 - x1)
            for da in (-0.4, 0.4):
                painter.drawLine(int(x2), int(y2),
                                 int(x2 - 15 * math.cos(angle + da)),
                                 int(y2 - 15 * math.sin(angle + da)))
        elif annot.type == "rect_highlight" and len(pos) >= 4:
            painter.drawRect(*self._scale_overlay_rect(pos))


class VideoPlayer(QWidget):
    """動画プレイヤーウィジェット"""

    position_updated = Signal(int)
    duration_updated = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration_ms = 0
        self._settings = QSettings("VideoStudio", "VideoStudio")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 動画表示（QVideoSink + オーバーレイ一体型）
        self.display = VideoDisplay()
        layout.addWidget(self.display, stretch=1)

        # コントロールバー
        controls = QHBoxLayout()

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.btn_play.clicked.connect(self._toggle_play)
        controls.addWidget(self.btn_play)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self._slider_moved)
        controls.addWidget(self.slider)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFixedWidth(120)
        controls.addWidget(self.lbl_time)

        # 音量スライダー
        self.lbl_vol = QLabel("🔊")
        self.lbl_vol.setFixedWidth(20)
        controls.addWidget(self.lbl_vol)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setFixedWidth(80)
        saved_vol = int(self._settings.value("player/volume", 80) or 80)
        self.vol_slider.setValue(saved_vol)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        controls.addWidget(self.vol_slider)

        layout.addLayout(controls)

        # --- メディアプレイヤー ---
        self.player = QMediaPlayer()

        # 明示的にデフォルト音声デバイスを指定
        default_device = QMediaDevices.defaultAudioOutput()
        self.audio_output = QAudioOutput(default_device)
        self.audio_output.setVolume(saved_vol / 100.0)
        self.player.setAudioOutput(self.audio_output)

        # QVideoSink で映像を取得
        self.player.setVideoOutput(self.display.video_sink)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.errorOccurred.connect(
            lambda e, m: print(f"[VideoPlayer] Error {e}: {m}")
        )

        # --- BGM / TTS プレビュー再生用 ---
        self.bgm_player = QMediaPlayer()
        self.bgm_audio = QAudioOutput(default_device)
        self.bgm_player.setAudioOutput(self.bgm_audio)
        self._bgm_current_source: str | None = None
        self._bgm_looping = False
        # BGM終了時にループ再生
        self.bgm_player.mediaStatusChanged.connect(self._on_bgm_status)

        self.tts_player = QMediaPlayer()
        self.tts_audio = QAudioOutput(default_device)
        self.tts_player.setAudioOutput(self.tts_audio)

    def load(self, path: str):
        self.player.setSource(QUrl.fromLocalFile(path))
        # ソース設定後に音声出力を再接続（バックエンドの初期化順序を保証）
        self.player.setAudioOutput(self.audio_output)
        self.player.pause()

    @Slot(int)
    def seek(self, ms: int):
        self.player.setPosition(ms)

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _slider_moved(self, pos: int):
        self.player.setPosition(pos)

    def _on_volume_changed(self, val: int):
        self.audio_output.setVolume(val / 100.0)
        self._settings.setValue("player/volume", val)

    def _on_position_changed(self, pos: int):
        self.slider.setValue(pos)
        self.position_updated.emit(pos)
        self._update_time_label(pos, self._duration_ms)

    def _on_duration_changed(self, duration: int):
        self._duration_ms = duration
        self.slider.setRange(0, duration)
        self.duration_updated.emit(duration)
        self._update_time_label(0, duration)

    def _on_state_changed(self, state):
        self.btn_play.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")
        self.display.set_playback_active(state == QMediaPlayer.PlayingState)

    def _update_time_label(self, pos_ms: int, dur_ms: int):
        self.lbl_time.setText(f"{self._fmt(pos_ms)} / {self._fmt(dur_ms)}")

    @staticmethod
    def _fmt(ms: int) -> str:
        s = ms // 1000
        return f"{s // 60:02d}:{s % 60:02d}"

    def get_position_sec(self) -> float:
        return self.player.position() / 1000.0

    def get_duration_sec(self) -> float:
        return self._duration_ms / 1000.0

    def set_playback_rate(self, rate: float):
        self.player.setPlaybackRate(rate)

    def pause(self):
        self.player.pause()

    def is_playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlayingState

    # --- BGM / TTS プレビュー再生 ---

    def play_bgm(self, source: str, volume_db: float, offset_sec: float = 0.0):
        """BGMを再生（sourceが変わった場合のみ再読込、ループ対応）"""
        if not source:
            self.stop_bgm()
            return
        vol_linear = min(1.0, 10 ** (volume_db / 20.0))
        self.bgm_audio.setVolume(vol_linear * (self.vol_slider.value() / 100.0))
        self._bgm_looping = True
        if self._bgm_current_source != source:
            self._bgm_current_source = source
            self.bgm_player.setSource(QUrl.fromLocalFile(source))
        if self.bgm_player.playbackState() != QMediaPlayer.PlayingState:
            self.bgm_player.setPosition(int(offset_sec * 1000))
            self.bgm_player.play()

    def stop_bgm(self):
        self._bgm_looping = False
        if self.bgm_player.playbackState() != QMediaPlayer.StoppedState:
            self.bgm_player.stop()
        self._bgm_current_source = None

    def _on_bgm_status(self, status):
        """BGM終了時にループ再生"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self._bgm_looping:
            self.bgm_player.setPosition(0)
            self.bgm_player.play()

    def play_tts(self, path: str, volume_db: int = -6, offset_sec: float = 0.0):
        """TTSキャッシュ音声を再生"""
        vol_linear = min(1.0, 10 ** (volume_db / 20.0))
        self.tts_audio.setVolume(vol_linear * (self.vol_slider.value() / 100.0))
        current_source = self.tts_player.source().toLocalFile()
        if current_source != path:
            self.tts_player.setSource(QUrl.fromLocalFile(path))
        self.tts_player.setPosition(max(0, int(offset_sec * 1000)))
        self.tts_player.play()

    def stop_tts(self):
        if self.tts_player.playbackState() == QMediaPlayer.PlayingState:
            self.tts_player.stop()

    def stop_all_overlay_audio(self):
        self.stop_bgm()
        self.stop_tts()
