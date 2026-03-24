# Video Studio

YouTube向け動画編集ツール。Python + FFmpegベースのタイムラインエディタ。
元動画をカットしながら、字幕・BGM・アバター・モザイク・強調マークをタイムライン上に配置して動画を仕上げます。

## コンセプト

```
元動画（タイムラインの基盤）
│
├─ カット: 不要部分を削除 → カット後の尺が動画全体の長さを決定
│
└─ カット後のタイムライン上に各要素を配置
    ├─ 字幕トラック: 任意の時点にテキストを配置 → 画面表示 + TTS音声を同時生成
    ├─ BGMトラック: 任意の区間に音源を配置 → 区間内でループ再生（音源 or 無音を選択）
    ├─ アバター: 字幕と連動してリップシンク付きアバターを表示
    ├─ モザイク: 画面上の領域を手動選択してモザイク適用（時間範囲指定）
    └─ 強調マーク: 丸囲み・矢印・ハイライトなどの注釈を配置
```

## 機能一覧

| 機能 | 説明 |
|------|------|
| **映像カット** | 不要区間を削除。カット後の尺が動画全体のタイムラインを決定する |
| **字幕 + TTS** | タイムライン上の任意の時点にテキストを配置すると、画面に字幕を表示しつつ同じ内容のTTS音声を自動生成・挿入 |
| **BGM** | タイムライン上の任意の区間にBGMを配置。音源ファイルを指定するとその区間でループ再生。音源なし（無音）も選択可 |
| **アバター** | 静止画1枚からリップシンク付きトーキングヘッドを生成。字幕のTTS音声に連動して口を動かす |
| **モザイク** | 画面上の任意の矩形領域を手動で選択し、指定した時間範囲でモザイク（ピクセレート/ブラー）を適用 |
| **強調マーク** | 丸囲み、矢印、ハイライト枠などの注釈を画面上に配置。時間範囲を指定して表示 |

## ユーザー体験の流れ

1. **動画を読み込む** — 元動画をインポート
2. **カット編集** — タイムライン上で不要区間を選択・削除。残った区間が最終的な動画の尺になる
3. **字幕を挿入** — タイムライン上の時点を選択 → テキストを入力 → 画面に字幕が表示され、同時にTTS音声が生成されて動画に挿入される
4. **BGMを挿入** — タイムライン上の区間を選択 → 音源ファイルを指定（または無音を選択）→ 区間内でBGMがループ再生される
5. **アバターを配置** — アバター画像を設定 → 字幕のTTS音声に合わせてリップシンク動画を自動生成・合成
6. **モザイクをかける** — 画面上の領域をドラッグで選択 → 時間範囲を指定 → その領域にモザイクが適用される
7. **強調マークを追加** — 丸囲みや矢印を画面上に配置 → 時間範囲を指定して表示
8. **レンダリング** — 全要素を合成して最終動画を書き出し

## アーキテクチャ

```
video-studio/
├── Makefile                        # インストール・ビルド自動化
├── pyproject.toml                  # Python依存関係
├── requirements.txt
├── README.md
│
├── src/video_studio/
│   ├── cli.py                      # CLIエントリポイント (click)
│   ├── app.py                      # Streamlit GUIエントリポイント
│   ├── config.py                   # グローバル設定
│   │
│   ├── core/
│   │   ├── project.py              # プロジェクトモデル（タイムライン・トラック管理）
│   │   ├── timeline.py             # タイムライン: カット情報と各トラックの時間管理
│   │   ├── pipeline.py             # レンダリングパイプライン
│   │   └── ffmpeg_utils.py         # FFmpegラッパー
│   │
│   ├── editor/
│   │   ├── trimmer.py              # 動画カット（区間削除）
│   │   └── concat.py               # カット後セグメントの結合
│   │
│   ├── subtitles/
│   │   ├── track.py                # 字幕トラック: 時点・テキスト・表示期間の管理
│   │   ├── renderer.py             # 字幕の画面バーンイン（ASS/SRT）
│   │   └── tts.py                  # edge-tts音声合成 + 字幕タイミング自動同期
│   │
│   ├── audio/
│   │   ├── bgm_track.py            # BGMトラック: 区間・音源・ループ・無音の管理
│   │   └── mixer.py                # 音声ミキシング（元音声 + TTS + BGM）
│   │
│   ├── avatar/
│   │   ├── sadtalker.py            # SadTalkerリップシンク生成
│   │   ├── wav2lip.py              # Wav2Lip（代替バックエンド）
│   │   └── compositor.py           # アバター合成・オーバーレイ
│   │
│   ├── mosaic/
│   │   ├── region.py               # 手動選択した矩形領域＋時間範囲の管理
│   │   └── blur.py                 # ブラー/ピクセレート処理
│   │
│   └── annotation/
│       ├── shapes.py               # 丸囲み・矢印・ハイライト枠の定義
│       └── renderer.py             # 強調マークの描画・合成
│
├── models/                         # モデルウェイト（gitignore対象）
├── assets/                         # サンプルアバター、BGM、フォント
└── tests/
```

## データモデル

プロジェクトは以下のトラック構造でタイムラインを管理します：

```
Project
├── source: 元動画ファイルパス
├── cuts: [Cut(start, end), ...]           # 残す区間のリスト → カット後の尺がマスター
│
├── subtitle_track: [                       # 字幕トラック
│     SubtitleEntry(
│       time: "00:00:30",                   # カット後タイムライン上の挿入時点
│       text: "ここがポイントです",
│       voice: "ja-JP-NanamiNeural",        # TTS音声（自動生成）
│       duration: auto                       # TTS音声の長さから自動決定
│     ), ...
│   ]
│
├── bgm_track: [                            # BGMトラック
│     BGMEntry(
│       start: "00:00:00",                  # 区間開始
│       end: "00:01:30",                    # 区間終了
│       source: "bgm/upbeat.mp3" | null,    # 音源ファイル（nullで無音）
│       volume: -18                          # 音量(dB)
│     ), ...
│   ]
│
├── avatar:                                 # アバター設定
│     image: "avatars/character.png",
│     position: "bottom-right",
│     enabled_with_subtitles: true           # 字幕があるときだけ表示
│
├── mosaic_regions: [                       # モザイク
│     MosaicRegion(
│       rect: [x, y, w, h],                # 画面上の矩形（手動選択）
│       start: "00:00:10",
│       end: "00:00:45",
│       mode: "pixelate"                    # pixelate | blur
│     ), ...
│   ]
│
└── annotations: [                          # 強調マーク
      Annotation(
        type: "circle" | "arrow" | "highlight",
        position: [x, y, w, h],
        start: "00:00:15",
        end: "00:00:20",
        color: "#FF0000",
        thickness: 3
      ), ...
    ]
```

## 技術スタック

| レイヤー | 技術 | 用途 |
|---------|------|------|
| 動画処理 | FFmpeg + MoviePy 2.x | カット、合成、エンコード |
| 画像処理 | OpenCV (cv2) | モザイク、強調マーク描画、フレーム操作 |
| 音声処理 | pydub | 音声ミキシング、BGMループ、音量調整 |
| 音声合成 | edge-tts | Microsoft音声エンジン（無料・高品質・多言語対応） |
| リップシンク | SadTalker / Wav2Lip | 静止画＋音声→トーキングヘッド動画 |
| GUI | Streamlit + streamlit-drawable-canvas | ブラウザベースUI、領域選択キャンバス |
| CLI | click | コマンドライン操作 |

## 必要環境

- Python 3.10+
- FFmpeg 6.0+
- GPU推奨（アバター生成用、CUDA対応NVIDIA GPU）

## インストール

```bash
# システム依存関係のインストール（FFmpeg等）
make install-system

# Python仮想環境の作成と依存関係インストール
make venv

# アバターモデルのダウンロード（オプション、数GB）
make download-models
```

## 使い方

### GUI（Streamlit）

```bash
make run-gui
# ブラウザで http://localhost:8501 を開く
```

### CLI

```bash
# 動画カット（残す区間を指定）
video-studio cut --input video.mp4 --keep 00:00:10-00:01:00 --keep 00:02:00-00:03:30 --output cut.mp4

# 字幕+TTS挿入（指定時点に字幕と音声を同時追加）
video-studio subtitle --input cut.mp4 --at 00:00:30 --text "ここがポイントです" --voice ja-JP-NanamiNeural --output sub.mp4

# BGM挿入（区間指定、ループ再生）
video-studio bgm --input cut.mp4 --start 00:00:00 --end 00:01:30 --source bgm.mp3 --volume -18 --output bgm.mp4

# BGM挿入（無音区間）
video-studio bgm --input cut.mp4 --start 00:01:30 --end 00:02:00 --mute --output bgm.mp4

# モザイク（手動領域指定 + 時間範囲）
video-studio mosaic --input cut.mp4 --region 100,200,300,400 --start 00:00:10 --end 00:00:45 --output mosaic.mp4

# 強調マーク（丸囲み）
video-studio annotate --input cut.mp4 --type circle --position 500,300,100,100 --start 00:00:15 --end 00:00:20 --color red --output annotated.mp4

# アバター生成（字幕のTTSに連動）
video-studio avatar --input sub.mp4 --image face.png --position bottom-right --output avatar.mp4

# フルパイプライン（プロジェクトファイルから一括レンダリング）
video-studio render --project project.json --output final.mp4
```

### プロジェクトファイル例（project.json）

```json
{
  "source": "raw_footage.mp4",
  "output": "final.mp4",
  "cuts": [
    {"start": "00:00:10", "end": "00:01:00"},
    {"start": "00:02:00", "end": "00:03:30"}
  ],
  "subtitle_track": [
    {"time": "00:00:05", "text": "はじめに", "voice": "ja-JP-NanamiNeural"},
    {"time": "00:00:30", "text": "ここが重要なポイントです", "voice": "ja-JP-NanamiNeural"},
    {"time": "00:01:50", "text": "まとめ", "voice": "ja-JP-NanamiNeural"}
  ],
  "bgm_track": [
    {"start": "00:00:00", "end": "00:01:00", "source": "assets/bgm/upbeat.mp3", "volume": -18},
    {"start": "00:01:00", "end": "00:01:30", "source": null},
    {"start": "00:01:30", "end": "00:02:30", "source": "assets/bgm/calm.mp3", "volume": -20}
  ],
  "avatar": {
    "image": "assets/avatars/character.png",
    "position": "bottom-right"
  },
  "mosaic_regions": [
    {"rect": [100, 200, 150, 150], "start": "00:00:10", "end": "00:00:45", "mode": "pixelate"}
  ],
  "annotations": [
    {"type": "circle", "position": [500, 300, 100, 100], "start": "00:00:15", "end": "00:00:20", "color": "#FF0000", "thickness": 3},
    {"type": "arrow", "position": [200, 100, 400, 300], "start": "00:00:50", "end": "00:00:55", "color": "#FFFF00", "thickness": 2}
  ],
  "subtitle_style": {
    "font": "assets/fonts/NotoSansJP-Bold.ttf",
    "size": 48,
    "color": "#FFFFFF",
    "outline_color": "#000000",
    "position": "bottom"
  }
}
```

## レンダリングパイプライン

```
元動画
  │
  ▼
① カット（不要区間削除・結合）→ マスタータイムライン確定
  │
  ▼
② TTS音声生成（字幕テキスト → 音声ファイル + 表示タイミング算出）
  │
  ▼
③ アバター生成（TTS音声 + 静止画 → リップシンク動画）
  │
  ▼
④ 映像合成（モザイク + 強調マーク + 字幕 + アバターをフレームに描画）
  │
  ▼
⑤ 音声ミキシング（元音声 + TTS音声 + BGMをミックス）
  │
  ▼
⑥ 最終エンコード → 出力ファイル
```

## 対応フォーマット

- **入力**: MP4, MOV, AVI, MKV, WebM
- **出力**: MP4 (H.264/H.265), WebM (VP9)
- **音声**: MP3, WAV, AAC, OGG
- **字幕**: SRT, ASS

## 注意事項

- edge-ttsはインターネット接続が必要です
- SadTalkerのモデルは数GBあるため、初回ダウンロードに時間がかかります
- GPU（CUDA）があるとアバター生成が大幅に高速化されます
- 字幕挿入時、TTS音声の長さ分だけ字幕が自動表示されます（手動で表示時間の調整も可）

## 開発

```bash
# テスト実行
make test

# リンター
make lint

# フォーマッター
make format
```

## ライセンス

MIT
