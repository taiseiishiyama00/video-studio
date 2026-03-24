"""FFmpegユーティリティのテスト"""

from pathlib import Path

from pydub import AudioSegment
from pydub import utils as pydub_utils

from video_studio.core import ffmpeg_utils


def test_pydub_uses_resolved_ffmpeg_paths():
    assert AudioSegment.converter == ffmpeg_utils._FFMPEG_PATH
    assert AudioSegment.ffprobe == ffmpeg_utils._FFPROBE_PATH
    assert pydub_utils.get_encoder_name() == ffmpeg_utils._FFMPEG_PATH
    assert pydub_utils.get_prober_name() == ffmpeg_utils._FFPROBE_PATH


def test_ffmpeg_dirs_are_in_path():
    path_parts = __import__("os").environ.get("PATH", "").split(":")

    assert str(Path(ffmpeg_utils._FFMPEG_PATH).parent) in path_parts
    assert str(Path(ffmpeg_utils._FFPROBE_PATH).parent) in path_parts
