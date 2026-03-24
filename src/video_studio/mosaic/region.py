"""手動選択した矩形領域＋時間範囲の管理"""

from __future__ import annotations

from video_studio.core.project import MosaicRegion


def validate_region(region: MosaicRegion, width: int, height: int) -> MosaicRegion:
    """モザイク領域を動画の解像度内にクランプ"""
    x, y, w, h = region.rect
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width - x))
    h = max(1, min(h, height - y))
    return MosaicRegion(
        rect=(x, y, w, h),
        start=region.start,
        end=region.end,
        mode=region.mode,
        strength=region.strength,
    )
