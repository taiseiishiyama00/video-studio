"""TTS生成のテスト"""

import asyncio
import sys
import types
from pathlib import Path

from video_studio.subtitles import tts


def test_generate_tts_uses_ffprobe_duration(monkeypatch, tmp_path):
    saved = {}

    class FakeCommunicate:
        def __init__(self, text, voice):
            saved["text"] = text
            saved["voice"] = voice

        async def save(self, output_path):
            saved["output_path"] = output_path
            tmp_path.joinpath(Path(output_path).name).write_bytes(b"fake")

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=FakeCommunicate))
    monkeypatch.setattr(tts, "get_duration", lambda output_path: 1.234)

    duration = asyncio.run(tts._generate_tts_async("字幕テスト", "ja-JP-NanamiNeural", str(tmp_path / "audio.mp3")))

    assert duration == 1.234
    assert saved["text"] == "字幕テスト"
    assert saved["voice"] == "ja-JP-NanamiNeural"
    assert saved["output_path"].endswith("audio.mp3")
