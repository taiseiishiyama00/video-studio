"""BGMトラック: 区間・音源・ループ・無音の管理

BGMは指定区間内でループ再生される。音源なし（null）の場合はその区間は無音。
"""

from __future__ import annotations

from pydub import AudioSegment

from video_studio.core.project import BGMEntry


def create_bgm_segment(entry: BGMEntry) -> AudioSegment:
    """BGMエントリから指定区間分の音声セグメントを生成

    Args:
        entry: BGMエントリ

    Returns:
        区間の長さに合わせたAudioSegment
    """
    duration_ms = int(entry.duration * 1000)

    if entry.source is None:
        # 無音
        return AudioSegment.silent(duration=duration_ms)

    # 音源を読み込み
    bgm = AudioSegment.from_file(entry.source)

    # 音量調整
    bgm = bgm + entry.volume  # pydubではdBで加算

    # 区間の長さになるまでループ
    if len(bgm) < duration_ms:
        repeats = (duration_ms // len(bgm)) + 1
        bgm = bgm * repeats

    # 区間の長さにトリム
    bgm = bgm[:duration_ms]

    # フェードイン・フェードアウト（500ms）
    fade_ms = min(500, duration_ms // 4)
    if fade_ms > 0:
        bgm = bgm.fade_in(fade_ms).fade_out(fade_ms)

    return bgm


def build_bgm_track(entries: list[BGMEntry], total_duration: float) -> AudioSegment:
    """全BGMエントリからタイムライン全体のBGMトラックを構築

    Args:
        entries: BGMエントリのリスト
        total_duration: タイムライン全体の長さ（秒）

    Returns:
        タイムライン全体の長さのAudioSegment
    """
    total_ms = int(total_duration * 1000)
    track = AudioSegment.silent(duration=total_ms)

    for entry in entries:
        segment = create_bgm_segment(entry)
        start_ms = int(entry.start * 1000)
        track = track.overlay(segment, position=start_ms)

    return track
