"""FFmpegラッパー"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


class FFmpegError(Exception):
    pass


def _find_command(name: str) -> str:
    """ffmpeg/ffprobeのパスを探す"""
    # 1. 環境変数から取得
    env_var = f"{name.upper()}_PATH"
    if env_var in os.environ:
        return os.environ[env_var]

    # 2. 一般的なパス（.appバンドルではPATHが制限されるため先にチェック）
    for candidate in [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
    ]:
        if Path(candidate).exists():
            return candidate

    # 3. PATHから探す
    found = shutil.which(name)
    if found:
        return found

    # 4. デフォルトの名前を返す（失敗するが詳細なエラーが出る）
    return name


# キャッシュ
_FFMPEG_PATH = _find_command("ffmpeg")
_FFPROBE_PATH = _find_command("ffprobe")


def _prepend_command_dir(command_path: str) -> None:
    """コマンドの親ディレクトリをPATHの先頭へ追加"""
    path = Path(command_path)
    if not path.exists():
        return

    command_dir = str(path.parent)
    current_path = os.environ.get("PATH", "")
    parts = current_path.split(os.pathsep) if current_path else []
    if command_dir in parts:
        return

    os.environ["PATH"] = (
        command_dir if not current_path else f"{command_dir}{os.pathsep}{current_path}"
    )


def _configure_pydub(ffmpeg_path: str, ffprobe_path: str) -> None:
    """pydubがffmpeg/ffprobeを見つけられるよう設定"""
    try:
        from pydub import AudioSegment
        from pydub import utils as pydub_utils
    except ImportError:
        return

    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffmpeg = ffmpeg_path
    AudioSegment.ffprobe = ffprobe_path

    if Path(ffmpeg_path).exists():
        pydub_utils.get_encoder_name = lambda: ffmpeg_path
    if Path(ffprobe_path).exists():
        pydub_utils.get_prober_name = lambda: ffprobe_path


_prepend_command_dir(_FFMPEG_PATH)
_prepend_command_dir(_FFPROBE_PATH)
_configure_pydub(_FFMPEG_PATH, _FFPROBE_PATH)


def run_ffmpeg(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """FFmpegコマンドを実行"""
    cmd = [_FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "warning"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise FFmpegError(f"FFmpeg failed: {result.stderr}")
    return result


def probe(input_path: str | Path) -> dict:
    """ffprobeで動画情報を取得"""
    cmd = [
        _FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def get_duration(input_path: str | Path) -> float:
    """動画の長さ（秒）を取得"""
    info = probe(input_path)
    return float(info["format"]["duration"])


def get_resolution(input_path: str | Path) -> tuple[int, int]:
    """動画の解像度 (width, height) を取得"""
    info = probe(input_path)
    for stream in info["streams"]:
        if stream["codec_type"] == "video":
            return int(stream["width"]), int(stream["height"])
    raise FFmpegError("No video stream found")


def get_fps(input_path: str | Path) -> float:
    """動画のFPSを取得"""
    info = probe(input_path)
    for stream in info["streams"]:
        if stream["codec_type"] == "video":
            r = stream.get("r_frame_rate", "30/1")
            num, den = map(int, r.split("/"))
            return num / den if den else 30.0
    return 30.0


def trim_segment(
    input_path: str | Path,
    output_path: str | Path,
    start: float,
    end: float,
    reencode: bool = False,
) -> None:
    """動画の一部を切り出し"""
    args = ["-ss", str(start), "-to", str(end), "-i", str(input_path)]
    if reencode:
        args += ["-c:v", "libx264", "-c:a", "aac"]
    else:
        args += ["-c", "copy"]
    args.append(str(output_path))
    run_ffmpeg(args)


def concat_files(file_list: list[str | Path], output_path: str | Path) -> None:
    """FFmpeg concat demuxerで結合"""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in file_list:
            f.write(f"file '{Path(p).resolve()}'\n")
        list_path = f.name

    try:
        run_ffmpeg([
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            str(output_path),
        ])
    finally:
        Path(list_path).unlink(missing_ok=True)


def overlay_video(
    base_path: str | Path,
    overlay_path: str | Path,
    output_path: str | Path,
    x: int,
    y: int,
    start: float = 0,
    end: float | None = None,
) -> None:
    """動画を別の動画にオーバーレイ"""
    enable = f"between(t,{start},{end})" if end else f"gte(t,{start})"
    args = [
        "-i", str(base_path),
        "-i", str(overlay_path),
        "-filter_complex",
        f"[1:v]scale=-1:-1[ov];[0:v][ov]overlay={x}:{y}:enable='{enable}'",
        "-c:a", "copy",
        str(output_path),
    ]
    run_ffmpeg(args)


def mux_audio_video(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
) -> None:
    """映像と音声を結合"""
    run_ffmpeg([
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ])
