"""プロジェクトモデルのテスト"""

import json
import tempfile
from pathlib import Path

from video_studio.core.project import (
    Annotation,
    AvatarConfig,
    BGMEntry,
    MosaicRegion,
    Project,
    SubtitleEntry,
)


class TestSubtitleEntry:
    def test_from_dict(self):
        e = SubtitleEntry.from_dict({
            "time": "00:00:30",
            "text": "テスト字幕",
            "voice": "ja-JP-NanamiNeural",
        })
        assert e.time == 30.0
        assert e.text == "テスト字幕"


class TestBGMEntry:
    def test_from_dict(self):
        e = BGMEntry.from_dict({
            "start": "00:00:00",
            "end": "00:01:00",
            "source": "bgm.mp3",
            "volume": -20,
        })
        assert e.duration == 60.0
        assert e.source == "bgm.mp3"

    def test_mute(self):
        e = BGMEntry.from_dict({
            "start": "00:00:00",
            "end": "00:01:00",
            "source": None,
        })
        assert e.source is None


class TestMosaicRegion:
    def test_from_dict(self):
        m = MosaicRegion.from_dict({
            "rect": [100, 200, 150, 150],
            "start": "00:00:10",
            "end": "00:00:45",
            "mode": "blur",
        })
        assert m.rect == (100, 200, 150, 150)
        assert m.mode == "blur"


class TestAnnotation:
    def test_circle(self):
        a = Annotation.from_dict({
            "type": "circle",
            "position": [500, 300, 50],
            "start": "00:00:15",
            "end": "00:00:20",
            "color": "#FF0000",
        })
        assert a.type == "circle"
        assert a.position == (500, 300, 50)


class TestProject:
    def test_from_dict(self):
        data = {
            "source": "test.mp4",
            "output": "out.mp4",
            "cuts": [
                {"start": "00:00:10", "end": "00:01:00"},
            ],
            "subtitle_track": [
                {"time": "00:00:05", "text": "Hello"},
            ],
            "bgm_track": [
                {"start": "00:00:00", "end": "00:01:00", "source": None},
            ],
        }
        p = Project.from_dict(data)
        assert p.source == "test.mp4"
        assert len(p.timeline.cuts) == 1
        assert len(p.subtitle_track) == 1
        assert len(p.bgm_track) == 1

    def test_roundtrip(self):
        data = {
            "source": "test.mp4",
            "cuts": [{"start": "00:00:10", "end": "00:01:00"}],
            "subtitle_track": [{"time": "00:00:05", "text": "Hello"}],
        }
        p = Project.from_dict(data)
        d = p.to_dict()
        p2 = Project.from_dict(d)
        assert p2.source == p.source
        assert len(p2.timeline.cuts) == len(p.timeline.cuts)

    def test_save_load_json(self):
        data = {
            "source": "test.mp4",
            "subtitle_track": [{"time": "00:00:05", "text": "テスト"}],
        }
        p = Project.from_dict(data)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            p.save_json(f.name)
            p2 = Project.from_json(f.name)

        assert p2.source == "test.mp4"
        assert p2.subtitle_track[0].text == "テスト"
        Path(f.name).unlink()
