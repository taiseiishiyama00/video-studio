"""字幕レンダラのテスト"""

from video_studio.config import SubtitleStyle
from video_studio.core.ffmpeg_utils import probe, run_ffmpeg
from video_studio.core.project import SubtitleEntry
from video_studio.subtitles.renderer import burn_subtitles


def test_burn_subtitles_renders_without_ffmpeg_text_filters(tmp_path):
    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "output.mp4"

    run_ffmpeg([
        "-f", "lavfi",
        "-i", "color=c=black:s=320x240:d=1",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        str(input_path),
    ])

    burn_subtitles(
        str(input_path),
        [(SubtitleEntry(time=0.0, text="テスト"), 0.8)],
        SubtitleStyle(size=24),
        str(output_path),
    )

    info = probe(output_path)
    assert output_path.exists()
    assert any(stream.get("codec_type") == "video" for stream in info["streams"])
    assert any(stream.get("codec_type") == "audio" for stream in info["streams"])
