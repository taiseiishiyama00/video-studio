"""アバター合成・オーバーレイ

レンダリング時はプレビューと同じく画像ベースでアバターを合成する。
これにより透過PNGのアルファを維持しつつ、発話中の口パク/まばたき表示を
プレビューと同じ前提で扱える。
"""

from __future__ import annotations

import cv2
import numpy as np

from video_studio.core.ffmpeg_utils import get_fps
from video_studio.core.project import AvatarConfig


def generate_avatar_clip(
    image_path: str,
    audio_path: str,
    output_path: str,
) -> None:
    """アバタークリップを生成（SadTalker or フォールバック）"""
    from video_studio.avatar import sadtalker

    if sadtalker.is_available():
        sadtalker.generate(image_path, audio_path, output_path)
    else:
        # フォールバック: 静止画から動画を生成（口は動かないが画像は表示）
        _generate_static_clip(image_path, audio_path, output_path)


def _generate_static_clip(image_path: str, audio_path: str, output_path: str) -> None:
    """静止画と音声から動画を生成（フォールバック）"""
    from pydub import AudioSegment

    from video_studio.core.ffmpeg_utils import run_ffmpeg

    audio = AudioSegment.from_file(audio_path)
    duration = len(audio) / 1000.0

    run_ffmpeg([
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-vf", "scale=320:-2",
        "-shortest",
        output_path,
    ])


def overlay_avatar_clips(
    base_video: str,
    avatar_clips: list[dict],
    avatar_config: AvatarConfig,
    output_path: str,
) -> None:
    """アバターをメイン動画にオーバーレイ

    Args:
        base_video: ベース動画パス
        avatar_clips: [{"start": float, "duration": float}, ...]
        avatar_config: アバター設定
        output_path: 出力パス
    """
    cap = cv2.VideoCapture(base_video)
    if not cap.isOpened():
        raise RuntimeError(f"動画を開けません: {base_video}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = get_fps(base_video)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    avatar_size = max(1, int(min(width, height) * avatar_config.scale))
    x, y = _calc_position(avatar_config.position, width, height, avatar_size)
    avatar_images = _load_avatar_images(avatar_config, avatar_size)
    if avatar_images["neutral"] is None:
        raise RuntimeError(f"アバター画像を読み込めません: {avatar_config.image}")

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps if fps > 0 else 0.0
        speaking = _is_avatar_speaking(current_time, avatar_clips)
        blinking = _is_avatar_blinking(frame_idx, fps)
        mouth_open = _is_mouth_open(frame_idx, fps)
        avatar_frame = _select_avatar_frame(avatar_images, speaking, blinking, mouth_open)
        if avatar_frame is not None:
            frame = _overlay_frame(frame, avatar_frame, x, y)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    from video_studio.mosaic.blur import _reencode_h264
    _reencode_h264(output_path)


def _calc_position(
    position: str, video_w: int, video_h: int, avatar_size: int
) -> tuple[int, int]:
    """アバターの表示位置を計算"""
    margin = 20
    positions = {
        "bottom-right": (video_w - avatar_size - margin, video_h - avatar_size - margin),
        "bottom-left": (margin, video_h - avatar_size - margin),
        "top-right": (video_w - avatar_size - margin, margin),
        "top-left": (margin, margin),
    }
    return positions.get(position, positions["bottom-right"])


def _overlay_frame(
    base: np.ndarray, overlay: np.ndarray, x: int, y: int
) -> np.ndarray:
    """フレームにオーバーレイ画像を合成"""
    h, w = overlay.shape[:2]
    bh, bw = base.shape[:2]

    # はみ出し防止
    if x + w > bw:
        w = bw - x
        overlay = overlay[:, :w]
    if y + h > bh:
        h = bh - y
        overlay = overlay[:h, :]
    if x < 0 or y < 0:
        return base

    result = base.copy()

    if overlay.shape[2] == 4:
        # アルファチャンネルがある場合
        alpha = overlay[:h, :w, 3:4].astype(np.float32) / 255.0
        over_rgb = overlay[:h, :w, :3].astype(np.float32)
        base_rgb = result[y : y + h, x : x + w].astype(np.float32)
        blended = over_rgb * alpha + base_rgb * (1.0 - alpha)
        result[y : y + h, x : x + w] = blended.astype(np.uint8)
    else:
        result[y : y + h, x : x + w] = overlay[:h, :w, :3]

    return result


def _load_avatar_images(
    avatar_config: AvatarConfig,
    avatar_size: int,
) -> dict[str, np.ndarray | None]:
    """アバター画像をロードしてレンダリングサイズへ揃える"""
    neutral = _load_avatar_image(avatar_config.image, avatar_size)
    mouth = _load_avatar_image(avatar_config.image_mouth_open, avatar_size)
    blink = _load_avatar_image(avatar_config.image_blink, avatar_size)
    return {
        "neutral": neutral,
        "mouth": mouth if mouth is not None else neutral,
        "blink": blink if blink is not None else neutral,
    }


def _load_avatar_image(path: str, avatar_size: int) -> np.ndarray | None:
    """画像をそのまま読み込み、アルファ付きなら維持して返す"""
    if not path:
        return None

    image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if image is None or image.size == 0:
        return None

    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
    elif image.ndim == 3 and image.shape[2] > 4:
        image = image[:, :, :4]

    interpolation = cv2.INTER_AREA if max(image.shape[:2]) > avatar_size else cv2.INTER_LINEAR
    return cv2.resize(image, (avatar_size, avatar_size), interpolation=interpolation)


def _is_avatar_speaking(current_time: float, avatar_clips: list[dict]) -> bool:
    """現在時刻に発話区間があるか"""
    for clip in avatar_clips:
        start = clip.get("start", 0.0)
        duration = clip.get("duration", 0.0)
        if start <= current_time < start + duration:
            return True
    return False


def _is_avatar_blinking(frame_idx: int, fps: float) -> bool:
    """一定周期で短くまばたきさせる"""
    if fps <= 0:
        return False

    blink_interval = max(1, int(round(fps * 3.0)))
    blink_duration = max(1, int(round(fps * 0.12)))
    phase = frame_idx % blink_interval
    return phase >= blink_interval - blink_duration


def _is_mouth_open(frame_idx: int, fps: float) -> bool:
    """発話中の口パク周期（約150msごとに開閉）"""
    if fps <= 0:
        return True

    cycle_frames = max(1, int(round(fps * 0.15)))
    return (frame_idx // cycle_frames) % 2 == 0


def _select_avatar_frame(
    avatar_images: dict[str, np.ndarray | None],
    speaking: bool,
    blinking: bool,
    mouth_open: bool,
) -> np.ndarray | None:
    """現在表示すべきアバター画像を返す"""
    if speaking:
        if mouth_open:
            return avatar_images["mouth"]
        return avatar_images["neutral"]
    if blinking:
        return avatar_images["blink"]
    return avatar_images["neutral"]
