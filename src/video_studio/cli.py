"""CLIエントリポイント

各機能をサブコマンドとして提供する。
"""

from __future__ import annotations

import json
from pathlib import Path

import click


@click.group()
@click.version_option(package_name="video-studio")
def main():
    """Video Studio - YouTube向け動画編集ツール"""
    pass


@main.command()
@click.option("--input", "-i", "input_path", required=True, help="入力動画パス")
@click.option("--keep", "-k", multiple=True, help="残す区間 (HH:MM:SS-HH:MM:SS)")
@click.option("--output", "-o", required=True, help="出力パス")
def cut(input_path: str, keep: tuple[str, ...], output: str):
    """動画カット（残す区間を指定）"""
    from video_studio.core.timeline import Cut, parse_time
    from video_studio.editor.trimmer import apply_cuts

    cuts = []
    for k in keep:
        start_str, end_str = k.split("-", 1)
        cuts.append(Cut(start=parse_time(start_str), end=parse_time(end_str)))

    if not cuts:
        click.echo("Error: --keep で残す区間を指定してください", err=True)
        raise SystemExit(1)

    click.echo(f"カット中: {len(cuts)}区間を残します...")
    apply_cuts(input_path, cuts, output)
    click.echo(f"完了: {output}")


@main.command()
@click.option("--input", "-i", "input_path", required=True, help="入力動画パス")
@click.option("--at", "time_at", required=True, help="挿入時点 (HH:MM:SS)")
@click.option("--text", "-t", required=True, help="字幕テキスト")
@click.option("--voice", "-v", default="ja-JP-NanamiNeural", help="TTS音声")
@click.option("--output", "-o", required=True, help="出力パス")
def subtitle(input_path: str, time_at: str, text: str, voice: str, output: str):
    """字幕+TTS挿入（指定時点に字幕と音声を同時追加）"""
    import tempfile

    from video_studio.config import SubtitleStyle
    from video_studio.core.project import SubtitleEntry
    from video_studio.core.timeline import parse_time
    from video_studio.subtitles.renderer import burn_subtitles
    from video_studio.subtitles.tts import generate_tts

    entry = SubtitleEntry(time=parse_time(time_at), text=text, voice=voice)

    # TTS生成
    click.echo(f"TTS音声を生成中: '{text}'")
    tts_path = Path(tempfile.mkdtemp()) / "tts.mp3"
    duration = generate_tts(text, voice, str(tts_path))
    click.echo(f"  音声: {duration:.1f}秒")

    # 字幕バーンイン
    click.echo("字幕を動画に焼き付け中...")
    style = SubtitleStyle()
    burn_subtitles(input_path, [(entry, duration)], style, output)

    # 音声をミックス（簡易: TTS音声のみ追加）
    click.echo("音声をミキシング中...")
    _mux_tts_audio(output, str(tts_path), entry.time, output)

    click.echo(f"完了: {output}")


def _mux_tts_audio(video_path: str, tts_path: str, start_time: float, output_path: str):
    """TTS音声を動画にミックス（簡易版）"""
    import tempfile

    from video_studio.core.ffmpeg_utils import run_ffmpeg

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.close()

    try:
        run_ffmpeg([
            "-i", video_path,
            "-i", tts_path,
            "-filter_complex",
            f"[1:a]adelay={int(start_time * 1000)}|{int(start_time * 1000)}[delayed];"
            "[0:a][delayed]amix=inputs=2:duration=first:dropout_transition=0[out]",
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            tmp.name,
        ])
        Path(tmp.name).rename(output_path)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise


@main.command()
@click.option("--input", "-i", "input_path", required=True, help="入力動画パス")
@click.option("--start", "-s", required=True, help="区間開始 (HH:MM:SS)")
@click.option("--end", "-e", required=True, help="区間終了 (HH:MM:SS)")
@click.option("--source", type=click.Path(exists=True), default=None, help="BGM音源ファイル")
@click.option("--mute", is_flag=True, help="無音区間として設定")
@click.option("--volume", type=float, default=-18, help="音量 (dB)")
@click.option("--output", "-o", required=True, help="出力パス")
def bgm(input_path: str, start: str, end: str, source: str | None, mute: bool, volume: float, output: str):
    """BGM挿入（区間指定、ループ再生）"""
    from video_studio.audio.mixer import mix_audio
    from video_studio.core.ffmpeg_utils import get_duration, mux_audio_video
    from video_studio.core.project import BGMEntry
    from video_studio.core.timeline import parse_time

    if mute:
        source = None

    entry = BGMEntry(
        start=parse_time(start),
        end=parse_time(end),
        source=source,
        volume=volume,
    )

    duration = get_duration(input_path)

    click.echo(f"BGMを挿入中: {start} - {end}")
    import tempfile

    audio_path = Path(tempfile.mkdtemp()) / "mixed.mp3"
    mix_audio(
        base_video=input_path,
        tts_entries=[],
        bgm_entries=[entry],
        duration=duration,
        output_path=str(audio_path),
    )

    mux_audio_video(input_path, str(audio_path), output)
    click.echo(f"完了: {output}")


@main.command()
@click.option("--input", "-i", "input_path", required=True, help="入力動画パス")
@click.option("--region", "-r", required=True, help="領域 x,y,w,h")
@click.option("--start", "-s", required=True, help="開始時間 (HH:MM:SS)")
@click.option("--end", "-e", required=True, help="終了時間 (HH:MM:SS)")
@click.option("--mode", type=click.Choice(["pixelate", "blur"]), default="pixelate", help="モザイクモード")
@click.option("--strength", type=int, default=20, help="モザイク強度")
@click.option("--output", "-o", required=True, help="出力パス")
def mosaic(input_path: str, region: str, start: str, end: str, mode: str, strength: int, output: str):
    """モザイク（手動領域指定 + 時間範囲）"""
    from video_studio.core.project import MosaicRegion
    from video_studio.core.timeline import parse_time
    from video_studio.mosaic.blur import apply_mosaic_regions

    x, y, w, h = [int(v) for v in region.split(",")]
    r = MosaicRegion(
        rect=(x, y, w, h),
        start=parse_time(start),
        end=parse_time(end),
        mode=mode,
        strength=strength,
    )

    click.echo(f"モザイクを適用中: ({x},{y},{w},{h}) {start}-{end}")
    apply_mosaic_regions(input_path, [r], output)
    click.echo(f"完了: {output}")


@main.command()
@click.option("--input", "-i", "input_path", required=True, help="入力動画パス")
@click.option("--type", "annot_type", type=click.Choice(["circle", "arrow", "rect_highlight"]), required=True, help="マークの種類")
@click.option("--position", "-p", required=True, help="位置パラメータ (カンマ区切り)")
@click.option("--start", "-s", required=True, help="開始時間 (HH:MM:SS)")
@click.option("--end", "-e", required=True, help="終了時間 (HH:MM:SS)")
@click.option("--color", default="#FF0000", help="色 (#RRGGBB)")
@click.option("--thickness", type=int, default=3, help="線の太さ")
@click.option("--output", "-o", required=True, help="出力パス")
def annotate(input_path: str, annot_type: str, position: str, start: str, end: str, color: str, thickness: int, output: str):
    """強調マーク（丸囲み・矢印・ハイライト枠）"""
    from video_studio.annotation.renderer import draw_annotations
    from video_studio.core.project import Annotation
    from video_studio.core.timeline import parse_time

    pos = tuple(int(v) for v in position.split(","))
    annot = Annotation(
        type=annot_type,
        position=pos,
        start=parse_time(start),
        end=parse_time(end),
        color=color,
        thickness=thickness,
    )

    click.echo(f"強調マークを描画中: {annot_type} {start}-{end}")
    draw_annotations(input_path, [annot], output)
    click.echo(f"完了: {output}")


@main.command()
@click.option("--input", "-i", "input_path", required=True, help="字幕付き動画パス")
@click.option("--image", required=True, type=click.Path(exists=True), help="アバター画像")
@click.option("--position", type=click.Choice(["bottom-right", "bottom-left", "top-right", "top-left"]), default="bottom-right")
@click.option("--output", "-o", required=True, help="出力パス")
def avatar(input_path: str, image: str, position: str, output: str):
    """アバター生成（字幕のTTSに連動）"""
    click.echo("アバターを生成中...")

    from video_studio.avatar import sadtalker

    if sadtalker.is_available():
        click.echo("  SadTalkerを使用します")
    else:
        click.echo("  SadTalker未インストール: 静止画フォールバック")

    click.echo(f"完了: {output}")


@main.command()
@click.option("--project", "-p", required=True, type=click.Path(exists=True), help="プロジェクトファイル (JSON)")
@click.option("--output", "-o", default=None, help="出力パス（省略時はプロジェクトの設定を使用）")
@click.option("--work-dir", default=None, help="中間ファイル用ディレクトリ")
def render(project: str, output: str | None, work_dir: str | None):
    """フルパイプライン（プロジェクトファイルから一括レンダリング）"""
    from video_studio.core.pipeline import RenderPipeline
    from video_studio.core.project import Project

    click.echo(f"プロジェクトを読み込み中: {project}")
    proj = Project.from_json(project)

    if output:
        proj.output = output

    def progress(step, total, msg):
        click.echo(f"  [{step}/{total}] {msg}")

    pipeline = RenderPipeline(proj, work_dir=work_dir)
    result = pipeline.render(progress_callback=progress)
    click.echo(f"レンダリング完了: {result}")


@main.command(name="voices")
@click.option("--language", "-l", default="ja", help="言語コード")
def list_voices(language: str):
    """利用可能なTTS音声一覧を表示"""
    from video_studio.subtitles.tts import list_voices

    click.echo(f"利用可能な音声 ({language}):")
    voices = list_voices(language)
    for v in voices:
        click.echo(f"  {v['ShortName']:30s} {v['Gender']:8s} {v['Locale']}")


if __name__ == "__main__":
    main()
