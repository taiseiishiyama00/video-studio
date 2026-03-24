"""字幕トラックのテスト"""

from video_studio.core.project import SubtitleEntry
from video_studio.subtitles.track import generate_ass, generate_srt


class TestGenerateSrt:
    def test_basic(self):
        entries = [
            (SubtitleEntry(time=5.0, text="Hello"), 3.0),
            (SubtitleEntry(time=10.0, text="World"), 2.5),
        ]
        srt = generate_srt(entries)
        assert "1" in srt
        assert "Hello" in srt
        assert "2" in srt
        assert "World" in srt
        assert "-->" in srt

    def test_timing(self):
        entries = [(SubtitleEntry(time=90.5, text="Test"), 2.0)]
        srt = generate_srt(entries)
        assert "00:01:30" in srt


class TestGenerateAss:
    def test_basic(self):
        entries = [
            (SubtitleEntry(time=5.0, text="テスト"), 3.0),
        ]
        ass = generate_ass(entries)
        assert "[Script Info]" in ass
        assert "テスト" in ass
        assert "Dialogue:" in ass

    def test_custom_style(self):
        entries = [(SubtitleEntry(time=0, text="Test"), 1.0)]
        style = "Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1"
        ass = generate_ass(entries, style_line=style)
        assert "Arial" in ass
