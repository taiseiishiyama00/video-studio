"""edge-tts音声合成 + 字幕タイミング自動同期

テキストからTTS音声を生成し、音声の長さを返す。
字幕の表示タイミングはTTS音声の長さから自動決定される。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from video_studio.core.ffmpeg_utils import get_duration


async def _generate_tts_async(
    text: str,
    voice: str,
    output_path: str,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> float:
    """非同期でTTS音声を生成"""
    import edge_tts

    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    except TypeError:
        communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

    # 生成した音声の長さを取得
    return get_duration(output_path)


def generate_tts(
    text: str,
    voice: str,
    output_path: str | Path,
    rate: str = "-8%",
    pitch: str = "-2Hz",
) -> float:
    """TTS音声を生成

    Args:
        text: 読み上げるテキスト
        voice: edge-ttsの音声名 (例: "ja-JP-NanamiNeural")
        output_path: 出力音声ファイルパス

    Returns:
        生成した音声の長さ（秒）
    """
    output_path = str(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                duration = pool.submit(
                    lambda: asyncio.run(
                        _generate_tts_async(text, voice, output_path, rate=rate, pitch=pitch)
                    )
                ).result()
        else:
            duration = loop.run_until_complete(
                _generate_tts_async(text, voice, output_path, rate=rate, pitch=pitch)
            )
    except RuntimeError:
        duration = asyncio.run(
            _generate_tts_async(text, voice, output_path, rate=rate, pitch=pitch)
        )

    return duration


def list_voices(language: str = "ja") -> list[dict]:
    """利用可能な音声リストを取得"""
    import edge_tts

    async def _list():
        voices = await edge_tts.list_voices()
        return [v for v in voices if v["Locale"].startswith(language)]

    try:
        return asyncio.run(_list())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_list())
