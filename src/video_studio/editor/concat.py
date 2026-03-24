"""セグメント結合"""

from __future__ import annotations

from pathlib import Path

from video_studio.core.ffmpeg_utils import concat_files


def concatenate(segments: list[str | Path], output_path: str | Path) -> None:
    """複数の動画ファイルを結合"""
    concat_files(segments, output_path)
