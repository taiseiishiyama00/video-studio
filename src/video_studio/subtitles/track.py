"""字幕トラック: 時点・テキスト・表示期間の管理"""

from __future__ import annotations

from video_studio.core.project import SubtitleEntry
from video_studio.core.timeline import format_time


def generate_srt(entries: list[tuple[SubtitleEntry, float]]) -> str:
    """字幕エントリからSRT形式の文字列を生成

    Args:
        entries: [(SubtitleEntry, duration_seconds), ...]

    Returns:
        SRT形式の文字列
    """
    lines = []
    for i, (entry, duration) in enumerate(entries, 1):
        start = _srt_time(entry.time)
        end = _srt_time(entry.time + duration)
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(entry.text)
        lines.append("")
    return "\n".join(lines)


def generate_ass(
    entries: list[tuple[SubtitleEntry, float]],
    style_line: str = "",
    play_res_x: int = 1920,
    play_res_y: int = 1080,
) -> str:
    """字幕エントリからASS形式の文字列を生成"""
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {play_res_x}\n"
        f"PlayResY: {play_res_y}\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )
    if style_line:
        header += style_line + "\n"
    else:
        header += (
            "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,"
            "&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n"
        )

    header += (
        "\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events = []
    for entry, duration in entries:
        start = _ass_time(entry.time)
        end = _ass_time(entry.time + duration)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{entry.text}")

    return header + "\n".join(events) + "\n"


def _srt_time(seconds: float) -> str:
    """SRT用タイムスタンプ: HH:MM:SS,mmm"""
    t = format_time(seconds)
    return t.replace(".", ",")[:12]


def _ass_time(seconds: float) -> str:
    """ASS用タイムスタンプ: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"
