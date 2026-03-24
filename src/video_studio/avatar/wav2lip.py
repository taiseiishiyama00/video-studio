"""Wav2Lip（代替バックエンド）

既存動画の口元をリップシンクで置き換える。
SadTalkerの代替として利用可能。
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_available() -> bool:
    """Wav2Lipが利用可能かチェック"""
    try:
        import torch  # noqa: F401
        wav2lip_dir = _find_wav2lip_dir()
        return wav2lip_dir is not None
    except ImportError:
        return False


def generate(
    face_video_path: str,
    audio_path: str,
    output_path: str,
) -> str:
    """Wav2Lipでリップシンク動画を生成

    Args:
        face_video_path: 顔が含まれる動画パス
        audio_path: 音声ファイルパス
        output_path: 出力動画パス

    Returns:
        生成された動画のパス
    """
    wav2lip_dir = _find_wav2lip_dir()
    if wav2lip_dir is None:
        raise RuntimeError("Wav2Lipが見つかりません。")

    checkpoint = wav2lip_dir / "checkpoints" / "wav2lip_gan.pth"
    if not checkpoint.exists():
        raise RuntimeError(f"Wav2Lipモデルが見つかりません: {checkpoint}")

    cmd = [
        "python",
        str(wav2lip_dir / "inference.py"),
        "--checkpoint_path", str(checkpoint),
        "--face", face_video_path,
        "--audio", audio_path,
        "--outfile", output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(wav2lip_dir))
    if result.returncode != 0:
        raise RuntimeError(f"Wav2Lip failed: {result.stderr}")

    return output_path


def _find_wav2lip_dir() -> Path | None:
    """Wav2Lipのインストールディレクトリを検索"""
    from video_studio.config import MODELS_DIR

    candidates = [
        MODELS_DIR / "Wav2Lip",
        Path.home() / "Wav2Lip",
    ]
    for path in candidates:
        if path.exists() and (path / "inference.py").exists():
            return path
    return None
