"""動画カット（区間削除）

元動画から指定した区間のみを残し、それ以外を削除する。
"""

from __future__ import annotations

from pathlib import Path

from video_studio.core.ffmpeg_utils import concat_files, trim_segment
from video_studio.core.timeline import Cut


def apply_cuts(
    input_path: str | Path,
    cuts: list[Cut],
    output_path: str | Path,
    work_dir: str | Path | None = None,
) -> None:
    """カットを適用して出力

    Args:
        input_path: 元動画パス
        cuts: 残す区間のリスト
        output_path: 出力パス
        work_dir: 中間ファイル用ディレクトリ
    """
    import tempfile

    if not cuts:
        # カットなし: そのままコピー
        import shutil
        shutil.copy2(str(input_path), str(output_path))
        return

    if len(cuts) == 1:
        # 単一区間: 直接トリム
        trim_segment(input_path, output_path, cuts[0].start, cuts[0].end)
        return

    # 複数区間: 各区間をトリムしてから結合
    tmp_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="vstudio_trim_"))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    segments = []
    for i, cut in enumerate(cuts):
        seg_path = tmp_dir / f"seg_{i:04d}.mp4"
        trim_segment(input_path, seg_path, cut.start, cut.end, reencode=True)
        segments.append(seg_path)

    concat_files(segments, output_path)

    # 中間ファイルを削除
    for seg in segments:
        seg.unlink(missing_ok=True)
