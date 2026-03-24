"""字幕バーンイン: Pillowで字幕を動画フレームに直接描画する"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont

from video_studio.config import FONTS_DIR, SubtitleStyle
from video_studio.core.ffmpeg_utils import get_fps, probe, run_ffmpeg
from video_studio.core.project import SubtitleEntry


@dataclass
class PreparedSubtitle:
    start: float
    end: float
    overlay: np.ndarray
    x: int
    y: int


def burn_subtitles(
    input_path: str,
    entries: list[tuple[SubtitleEntry, float]],
    style: SubtitleStyle,
    output_path: str,
) -> None:
    """字幕を動画に焼き付ける"""
    if not entries:
        shutil.copy2(input_path, output_path)
        return

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"動画を開けません: {input_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = get_fps(input_path) or 30.0

    prepared = _prepare_subtitles(entries, style, width, height)

    tmp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_video.close()
    tmp_path = Path(tmp_video.name)

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(tmp_path), fourcc, fps, (width, height))

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_idx / fps
            for subtitle in prepared:
                if subtitle.start <= current_time <= subtitle.end:
                    frame = _overlay_rgba(frame, subtitle.overlay, subtitle.x, subtitle.y)

            writer.write(frame)
            frame_idx += 1

        writer.release()
        cap.release()

        from video_studio.mosaic.blur import _reencode_h264

        _reencode_h264(str(tmp_path))
        _attach_original_audio(str(tmp_path), input_path, output_path)
    finally:
        cap.release()
        tmp_path.unlink(missing_ok=True)


def _prepare_subtitles(
    entries: list[tuple[SubtitleEntry, float]],
    style: SubtitleStyle,
    width: int,
    height: int,
) -> list[PreparedSubtitle]:
    prepared: list[PreparedSubtitle] = []
    for entry, duration in entries:
        if not entry.text.strip():
            continue

        overlay_data = _build_subtitle_overlay(entry.text, style, width, height)
        if overlay_data is None:
            continue

        overlay, x, y = overlay_data
        prepared.append(
            PreparedSubtitle(
                start=entry.time,
                end=entry.time + duration,
                overlay=overlay,
                x=x,
                y=y,
            )
        )
    return prepared


def _build_subtitle_overlay(
    text: str,
    style: SubtitleStyle,
    width: int,
    height: int,
) -> tuple[np.ndarray, int, int] | None:
    font_size = max(18, int(style.size * height / 1080))
    outline_width = max(1, int(style.outline_width * height / 1080))
    spacing = max(4, font_size // 6)
    max_text_width = max(80, int(width * 0.88))

    font = _load_font(style.font, font_size)
    measure_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(measure_img)
    wrapped = _wrap_text(measure_draw, text, font, max_text_width, outline_width)
    if not wrapped:
        return None

    bbox = measure_draw.multiline_textbbox(
        (0, 0),
        wrapped,
        font=font,
        align="center",
        spacing=spacing,
        stroke_width=outline_width,
    )
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x = max(18, width // 50)
    pad_y = max(12, height // 60)
    box_w = int(min(width - 20, text_w + pad_x * 2))
    box_h = int(text_h + pad_y * 2)

    overlay = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    radius = max(10, min(box_w, box_h) // 10)
    draw.rounded_rectangle(
        (0, 0, box_w - 1, box_h - 1),
        radius=radius,
        fill=(0, 0, 0, 160),
    )

    fill = _parse_color(style.color)
    stroke = _parse_color(style.outline_color)
    text_x = int((box_w - text_w) / 2 - bbox[0])
    text_y = int((box_h - text_h) / 2 - bbox[1])
    draw.multiline_text(
        (text_x, text_y),
        wrapped,
        font=font,
        fill=fill,
        align="center",
        spacing=spacing,
        stroke_width=outline_width,
        stroke_fill=stroke,
    )

    x = max(0, (width - box_w) // 2)
    margin = max(20, height // 20)
    if style.position == "top":
        y = margin
    elif style.position == "center":
        y = max(0, (height - box_h) // 2)
    else:
        y = max(0, height - box_h - margin)

    return np.array(overlay), x, y


def _overlay_rgba(frame: np.ndarray, overlay: np.ndarray, x: int, y: int) -> np.ndarray:
    h, w = overlay.shape[:2]
    frame_h, frame_w = frame.shape[:2]

    if x >= frame_w or y >= frame_h:
        return frame
    if x + w > frame_w:
        w = frame_w - x
        overlay = overlay[:, :w]
    if y + h > frame_h:
        h = frame_h - y
        overlay = overlay[:h, :]
    if w <= 0 or h <= 0:
        return frame

    result = frame.copy()
    alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
    color = overlay[:, :, :3][:, :, ::-1].astype(np.float32)
    base = result[y : y + h, x : x + w].astype(np.float32)
    blended = color * alpha + base * (1.0 - alpha)
    result[y : y + h, x : x + w] = blended.astype(np.uint8)
    return result


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    stroke_width: int,
) -> str:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        if not paragraph:
            lines.append("")
            continue

        current = ""
        for char in paragraph:
            candidate = current + char
            bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=stroke_width)
            if bbox[2] - bbox[0] <= max_width or not current:
                current = candidate
                continue

            lines.append(current)
            current = char

        if current:
            lines.append(current)

    return "\n".join(lines)


def _attach_original_audio(video_path: str, source_path: str, output_path: str) -> None:
    info = probe(source_path)
    has_audio = any(stream.get("codec_type") == "audio" for stream in info.get("streams", []))
    if not has_audio:
        shutil.copy2(video_path, output_path)
        return

    run_ffmpeg([
        "-i", video_path,
        "-i", source_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ])


def _parse_color(hex_color: str) -> tuple[int, int, int, int]:
    rgb = ImageColor.getrgb(hex_color)
    return rgb[0], rgb[1], rgb[2], 255


@lru_cache(maxsize=16)
def _find_font_path(font_name: str) -> str | None:
    path = Path(font_name)
    if path.is_file():
        return str(path)

    bundled = FONTS_DIR / font_name
    if bundled.is_file():
        return str(bundled)

    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate

    search_dirs = [
        FONTS_DIR,
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        Path("/usr/share/fonts"),
    ]
    for directory in search_dirs:
        if not directory.exists():
            continue
        try:
            for found in directory.rglob(font_name):
                if found.is_file():
                    return str(found)
        except OSError:
            continue

    return None


def _load_font(font_name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = _find_font_path(font_name)
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()
