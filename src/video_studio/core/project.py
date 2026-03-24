"""プロジェクトモデル

タイムラインと全トラック（字幕、BGM、アバター、モザイク、強調マーク）を管理する。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from video_studio.config import SubtitleStyle
from video_studio.core.timeline import SpeedRegion, Timeline, parse_time


@dataclass
class SubtitleEntry:
    """字幕エントリ: タイムライン上の時点にテキストを配置"""

    time: float  # カット後タイムライン上の挿入時点（秒）
    text: str
    voice: str = "ja-JP-NanamiNeural"
    duration: float | None = None  # TTS音声から自動決定、手動設定も可
    tts_volume: int = -6  # TTS音量 (dB)
    tts_rate: str = "-5%"
    tts_pitch: str = "+2Hz"

    @classmethod
    def from_dict(cls, d: dict) -> SubtitleEntry:
        return cls(
            time=parse_time(d["time"]),
            text=d["text"],
            voice=d.get("voice", "ja-JP-NanamiNeural"),
            duration=d.get("duration"),
            tts_volume=d.get("tts_volume", -6),
            tts_rate=d.get("tts_rate", "-5%"),
            tts_pitch=d.get("tts_pitch", "+2Hz"),
        )


@dataclass
class BGMEntry:
    """BGMエントリ: タイムライン上の区間にBGMを配置"""

    start: float  # 秒
    end: float  # 秒
    source: str | None = None  # 音源ファイルパス（Noneで無音）
    volume: float = -18  # dB

    @property
    def duration(self) -> float:
        return self.end - self.start

    @classmethod
    def from_dict(cls, d: dict) -> BGMEntry:
        return cls(
            start=parse_time(d["start"]),
            end=parse_time(d["end"]),
            source=d.get("source"),
            volume=d.get("volume", -18),
        )


@dataclass
class AvatarConfig:
    """アバター設定（3画像リップシンク対応）"""

    image: str  # 目開け口閉じ（ニュートラル）
    image_mouth_open: str = ""  # 目開け口開け（発話中）
    image_blink: str = ""  # 目閉じ口閉じ（まばたき）
    position: str = "bottom-right"
    scale: float = 0.25

    @classmethod
    def from_dict(cls, d: dict) -> AvatarConfig:
        return cls(
            image=d["image"],
            image_mouth_open=d.get("image_mouth_open", ""),
            image_blink=d.get("image_blink", ""),
            position=d.get("position", "bottom-right"),
            scale=d.get("scale", 0.25),
        )


@dataclass
class MosaicRegion:
    """モザイク領域: 手動選択した矩形 + 時間範囲"""

    rect: tuple[int, int, int, int]  # (x, y, w, h)
    start: float  # 秒
    end: float  # 秒
    mode: str = "pixelate"  # "pixelate" | "blur"
    strength: int = 20  # モザイクの強度

    @classmethod
    def from_dict(cls, d: dict) -> MosaicRegion:
        return cls(
            rect=tuple(d["rect"]),
            start=parse_time(d["start"]),
            end=parse_time(d["end"]),
            mode=d.get("mode", "pixelate"),
            strength=d.get("strength", 20),
        )


@dataclass
class Annotation:
    """強調マーク: 丸囲み・矢印・ハイライト"""

    type: str  # "circle" | "arrow" | "rect_highlight"
    position: tuple[int, ...]  # circle: (cx, cy, r), arrow: (x1, y1, x2, y2), rect: (x, y, w, h)
    start: float  # 秒
    end: float  # 秒
    color: str = "#FF0000"
    thickness: int = 3

    @classmethod
    def from_dict(cls, d: dict) -> Annotation:
        return cls(
            type=d["type"],
            position=tuple(d["position"]),
            start=parse_time(d["start"]),
            end=parse_time(d["end"]),
            color=d.get("color", "#FF0000"),
            thickness=d.get("thickness", 3),
        )


@dataclass
class Project:
    """プロジェクト: 全トラックを保持"""

    source: str  # 元動画ファイルパス
    output: str = "output.mp4"
    timeline: Timeline = field(default_factory=lambda: Timeline(cuts=[]))
    subtitle_track: list[SubtitleEntry] = field(default_factory=list)
    bgm_track: list[BGMEntry] = field(default_factory=list)
    avatar: AvatarConfig | None = None
    mosaic_regions: list[MosaicRegion] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    subtitle_style: SubtitleStyle = field(default_factory=SubtitleStyle)

    @classmethod
    def from_json(cls, path: str | Path) -> Project:
        """project.jsonからプロジェクトを読み込み"""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        cuts_data = data.get("cuts", [])
        timeline = Timeline.from_dict_list(cuts_data) if cuts_data else Timeline(cuts=[])

        # Speed regions
        speed_regions_data = data.get("speed_regions", [])
        if speed_regions_data:
            timeline.speed_regions = [SpeedRegion.from_dict(s) for s in speed_regions_data]

        subtitle_track = [SubtitleEntry.from_dict(s) for s in data.get("subtitle_track", [])]
        bgm_track = [BGMEntry.from_dict(b) for b in data.get("bgm_track", [])]
        avatar = AvatarConfig.from_dict(data["avatar"]) if data.get("avatar") else None
        mosaic_regions = [MosaicRegion.from_dict(m) for m in data.get("mosaic_regions", [])]
        annotations = [Annotation.from_dict(a) for a in data.get("annotations", [])]

        subtitle_style = SubtitleStyle()
        if "subtitle_style" in data:
            s = data["subtitle_style"]
            subtitle_style = SubtitleStyle(
                font=s.get("font", subtitle_style.font),
                size=s.get("size", subtitle_style.size),
                color=s.get("color", subtitle_style.color),
                outline_color=s.get("outline_color", subtitle_style.outline_color),
                position=s.get("position", subtitle_style.position),
            )

        return cls(
            source=data["source"],
            output=data.get("output", "output.mp4"),
            timeline=timeline,
            subtitle_track=subtitle_track,
            bgm_track=bgm_track,
            avatar=avatar,
            mosaic_regions=mosaic_regions,
            annotations=annotations,
            subtitle_style=subtitle_style,
        )

    def to_dict(self) -> dict:
        """プロジェクトを辞書に変換"""
        from video_studio.core.timeline import format_time

        d: dict = {"source": self.source, "output": self.output}

        if self.timeline.cuts:
            d["cuts"] = [
                {"start": format_time(c.start), "end": format_time(c.end)}
                for c in self.timeline.cuts
            ]

        if self.timeline.speed_regions:
            d["speed_regions"] = [
                {
                    "start": format_time(r.start),
                    "end": format_time(r.end),
                    "speed": r.speed,
                }
                for r in self.timeline.speed_regions
            ]

        if self.subtitle_track:
            d["subtitle_track"] = [
                {
                    "time": format_time(s.time), "text": s.text,
                    "voice": s.voice, "tts_volume": s.tts_volume,
                    "tts_rate": s.tts_rate, "tts_pitch": s.tts_pitch,
                    "duration": s.duration,
                }
                for s in self.subtitle_track
            ]

        if self.bgm_track:
            d["bgm_track"] = [
                {
                    "start": format_time(b.start),
                    "end": format_time(b.end),
                    "source": b.source,
                    "volume": b.volume,
                }
                for b in self.bgm_track
            ]

        if self.avatar:
            d["avatar"] = {
                "image": self.avatar.image,
                "image_mouth_open": self.avatar.image_mouth_open,
                "image_blink": self.avatar.image_blink,
                "position": self.avatar.position,
                "scale": self.avatar.scale,
            }

        if self.mosaic_regions:
            d["mosaic_regions"] = [
                {
                    "rect": list(m.rect),
                    "start": format_time(m.start),
                    "end": format_time(m.end),
                    "mode": m.mode,
                    "strength": m.strength,
                }
                for m in self.mosaic_regions
            ]

        if self.annotations:
            d["annotations"] = [
                {
                    "type": a.type,
                    "position": list(a.position),
                    "start": format_time(a.start),
                    "end": format_time(a.end),
                    "color": a.color,
                    "thickness": a.thickness,
                }
                for a in self.annotations
            ]

        return d

    def save_json(self, path: str | Path) -> None:
        """プロジェクトをJSONに保存"""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
