"""Video Studio - YouTube向け動画編集ツール"""

from __future__ import annotations

__version__ = "0.1.0"

# pydubがffmpegを見つけられるよう、パッケージ読み込み時にパスを設定
# macOSの.appバンドルではPATHが制限されるため必要
import video_studio.core.ffmpeg_utils as _  # noqa: F401
