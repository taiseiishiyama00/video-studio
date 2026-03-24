"""プロジェクト保存時のシリアライズテスト"""

from video_studio.core.project import Project


def test_subtitle_duration_roundtrip():
    project = Project.from_dict({
        "source": "test.mp4",
        "subtitle_track": [
            {
                "time": "00:00:05",
                "text": "字幕",
                "voice": "ja-JP-NanamiNeural",
                "duration": 4.25,
                "tts_volume": -3,
            }
        ],
    })

    data = project.to_dict()
    restored = Project.from_dict(data)

    assert restored.subtitle_track[0].duration == 4.25
    assert restored.subtitle_track[0].tts_volume == -3


def test_mosaic_strength_roundtrip():
    project = Project.from_dict({
        "source": "test.mp4",
        "mosaic_regions": [
            {
                "rect": [10, 20, 30, 40],
                "start": "00:00:01",
                "end": "00:00:03",
                "mode": "blur",
                "strength": 12,
            }
        ],
    })

    data = project.to_dict()
    restored = Project.from_dict(data)

    assert data["mosaic_regions"][0]["strength"] == 12
    assert restored.mosaic_regions[0].strength == 12
