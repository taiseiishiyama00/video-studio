"""SadTalkerリップシンク生成

静止画1枚 + 音声ファイル → リップシンク付きトーキングヘッド動画を生成。
SadTalkerがインストールされていない場合はフォールバック（静止画のみ）を提供。
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_available() -> bool:
    """SadTalkerが利用可能かチェック"""
    try:
        import torch  # noqa: F401
        sadtalker_dir = _find_sadtalker_dir()
        return sadtalker_dir is not None
    except ImportError:
        return False


def generate(
    image_path: str,
    audio_path: str,
    output_path: str,
    result_dir: str | None = None,
) -> str:
    """SadTalkerでリップシンク動画を生成

    Args:
        image_path: アバター画像パス
        audio_path: 音声ファイルパス
        output_path: 出力動画パス
        result_dir: SadTalker出力ディレクトリ

    Returns:
        生成された動画のパス
    """
    sadtalker_dir = _find_sadtalker_dir()
    if sadtalker_dir is None:
        raise RuntimeError(
            "SadTalkerが見つかりません。make download-models を実行してください。"
        )

    import tempfile
    result_dir = result_dir or tempfile.mkdtemp(prefix="sadtalker_")

    cmd = [
        "python",
        str(sadtalker_dir / "inference.py"),
        "--driven_audio", audio_path,
        "--source_image", image_path,
        "--result_dir", result_dir,
        "--still",
        "--preprocess", "crop",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(sadtalker_dir))
    if result.returncode != 0:
        raise RuntimeError(f"SadTalker failed: {result.stderr}")

    # 出力ファイルを探す
    result_path = Path(result_dir)
    generated = list(result_path.rglob("*.mp4"))
    if not generated:
        raise RuntimeError("SadTalkerの出力が見つかりません")

    # 出力パスにコピー
    import shutil
    shutil.copy2(str(generated[0]), output_path)
    return output_path


def _find_sadtalker_dir() -> Path | None:
    """SadTalkerのインストールディレクトリを検索"""
    from video_studio.config import MODELS_DIR

    candidates = [
        MODELS_DIR / "sadtalker" / "SadTalker",
        MODELS_DIR / "SadTalker",
        Path.home() / "SadTalker",
    ]
    for path in candidates:
        if path.exists() and (path / "inference.py").exists():
            return path
    return None
