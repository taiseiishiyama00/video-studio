"""音声ミキシング: 元音声 + TTS + BGMを合成"""

from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment

from video_studio.audio.bgm_track import build_bgm_track
from video_studio.core.project import BGMEntry


def mix_audio(
    base_video: str,
    tts_entries: list[dict],
    bgm_entries: list[BGMEntry],
    duration: float,
    output_path: str,
) -> None:
    """全音声トラックをミックスして出力

    Args:
        base_video: カット後の動画パス（元音声抽出用）
        tts_entries: [{"entry": SubtitleEntry, "audio_path": Path, "duration": float}, ...]
        bgm_entries: BGMエントリのリスト
        duration: タイムライン全体の長さ（秒）
        output_path: 出力音声パス
    """
    total_ms = int(duration * 1000)

    # 元動画から音声を抽出
    base_audio = _extract_audio(base_video, total_ms)

    # TTS音声をタイムライン上に配置
    tts_track = AudioSegment.silent(duration=total_ms)
    for tts in tts_entries:
        tts_audio = AudioSegment.from_file(str(tts["audio_path"]))
        start_ms = int(tts["entry"].time * 1000)
        tts_track = tts_track.overlay(tts_audio, position=start_ms)

    # BGMトラックを構築
    bgm_track = build_bgm_track(bgm_entries, duration)

    # ミキシング
    mixed = base_audio.overlay(tts_track).overlay(bgm_track)

    # 出力
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    mixed.export(output_path, format="mp3")


def _extract_audio(video_path: str, target_ms: int) -> AudioSegment:
    """動画から音声を抽出。失敗時は無音を返す"""
    import tempfile

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        from video_studio.core.ffmpeg_utils import run_ffmpeg
        run_ffmpeg([
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            tmp.name,
        ])

        audio = AudioSegment.from_wav(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

        # 長さを調整
        if len(audio) < target_ms:
            audio += AudioSegment.silent(duration=target_ms - len(audio))
        elif len(audio) > target_ms:
            audio = audio[:target_ms]

        return audio

    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        return AudioSegment.silent(duration=target_ms)
