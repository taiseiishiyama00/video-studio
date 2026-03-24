"""グローバル設定"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = ROOT_DIR / "models"
ASSETS_DIR = ROOT_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

DEFAULT_FONT = "NotoSansJP-Bold.ttf"
DEFAULT_TTS_VOICE = "ja-JP-NanamiNeural"
DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_VIDEO_FORMAT = "mp4"
DEFAULT_FPS = 30
DEFAULT_BGM_VOLUME_DB = -18


@dataclass
class SubtitleStyle:
    """字幕スタイル設定"""

    font: str = DEFAULT_FONT
    size: int = 48
    color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: int = 2
    position: str = "bottom"  # "top" | "center" | "bottom"

    def to_ass_style(self) -> str:
        """ASS字幕用スタイル文字列を生成"""
        alignment = {"top": 8, "center": 5, "bottom": 2}[self.position]
        primary = self._hex_to_ass(self.color)
        outline = self._hex_to_ass(self.outline_color)
        return (
            f"Style: Default,{self.font},{self.size},"
            f"{primary},&H000000FF,{outline},&H00000000,"
            f"0,0,0,0,100,100,0,0,1,{self.outline_width},0,"
            f"{alignment},10,10,10,1"
        )

    @staticmethod
    def _hex_to_ass(hex_color: str) -> str:
        """#RRGGBB → &H00BBGGRR (ASS形式)"""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"&H00{b:02X}{g:02X}{r:02X}"
