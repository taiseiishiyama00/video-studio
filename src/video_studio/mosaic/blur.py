"""ブラー/ピクセレート処理

手動選択した矩形領域にモザイクを適用する。
フレーム単位で処理し、指定した時間範囲のみに適用。
"""

from __future__ import annotations

import cv2
import numpy as np

from video_studio.core.ffmpeg_utils import get_fps
from video_studio.core.project import MosaicRegion


def pixelate_region(frame: np.ndarray, x: int, y: int, w: int, h: int, strength: int) -> np.ndarray:
    """矩形領域をピクセレート（モザイク）化"""
    roi = frame[y : y + h, x : x + w]
    if roi.size == 0:
        return frame

    # 縮小して拡大（ニアレストネイバー）
    factor = max(1, strength)
    small_w = max(1, w // factor)
    small_h = max(1, h // factor)
    small = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    result = frame.copy()
    result[y : y + h, x : x + w] = mosaic
    return result


def blur_region(frame: np.ndarray, x: int, y: int, w: int, h: int, strength: int) -> np.ndarray:
    """矩形領域にガウシアンブラーを適用"""
    roi = frame[y : y + h, x : x + w]
    if roi.size == 0:
        return frame

    ksize = max(1, strength) * 2 + 1  # 奇数にする
    blurred = cv2.GaussianBlur(roi, (ksize, ksize), 0)

    result = frame.copy()
    result[y : y + h, x : x + w] = blurred
    return result


def apply_mosaic_regions(
    input_path: str,
    regions: list[MosaicRegion],
    output_path: str,
) -> None:
    """動画にモザイク領域を適用

    Args:
        input_path: 入力動画パス
        regions: モザイク領域のリスト
        output_path: 出力動画パス
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"動画を開けません: {input_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = get_fps(input_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps

        for region in regions:
            if region.start <= current_time <= region.end:
                x, y, w, h = region.rect
                # クランプ
                x = max(0, min(x, width - 1))
                y = max(0, min(y, height - 1))
                w = max(1, min(w, width - x))
                h = max(1, min(h, height - y))

                if region.mode == "blur":
                    frame = blur_region(frame, x, y, w, h, region.strength)
                else:
                    frame = pixelate_region(frame, x, y, w, h, region.strength)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    # mp4vで書き出した後、FFmpegでH.264に変換
    _reencode_h264(output_path)


def _reencode_h264(path: str) -> None:
    """OpenCVのmp4v出力をH.264に再エンコード"""
    import tempfile
    from pathlib import Path

    from video_studio.core.ffmpeg_utils import run_ffmpeg

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.close()

    try:
        run_ffmpeg([
            "-i", path,
            "-c:v", "libx264",
            "-c:a", "copy",
            tmp.name,
        ])
        Path(path).unlink()
        Path(tmp.name).rename(path)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise
