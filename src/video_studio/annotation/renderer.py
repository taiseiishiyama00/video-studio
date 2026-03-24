"""強調マークの描画・合成

タイムライン上の指定した時間範囲にアノテーション（丸囲み・矢印・ハイライト）を描画する。
"""

from __future__ import annotations

import cv2

from video_studio.annotation.shapes import draw_arrow, draw_circle, draw_rect_highlight
from video_studio.core.ffmpeg_utils import get_fps
from video_studio.core.project import Annotation


def draw_annotations(
    input_path: str,
    annotations: list[Annotation],
    output_path: str,
) -> None:
    """動画にアノテーションを描画

    Args:
        input_path: 入力動画パス
        annotations: アノテーションのリスト
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

        for annot in annotations:
            if annot.start <= current_time <= annot.end:
                frame = _draw_annotation(frame, annot)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    # H.264に再エンコード
    from video_studio.mosaic.blur import _reencode_h264
    _reencode_h264(output_path)


def _draw_annotation(frame, annot: Annotation):
    """アノテーションの種類に応じて描画"""
    pos = annot.position

    if annot.type == "circle":
        # position: (cx, cy, r) or (cx, cy, rx, ry) → 円として描画
        if len(pos) >= 3:
            cx, cy, r = pos[0], pos[1], pos[2]
            return draw_circle(frame, cx, cy, r, annot.color, annot.thickness)

    elif annot.type == "arrow":
        # position: (x1, y1, x2, y2)
        if len(pos) >= 4:
            return draw_arrow(frame, pos[0], pos[1], pos[2], pos[3], annot.color, annot.thickness)

    elif annot.type == "rect_highlight":
        # position: (x, y, w, h)
        if len(pos) >= 4:
            return draw_rect_highlight(
                frame, pos[0], pos[1], pos[2], pos[3], annot.color, annot.thickness
            )

    return frame
