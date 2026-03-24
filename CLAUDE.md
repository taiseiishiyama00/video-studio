# Video Studio - Development Guide

## Team Structure

This project uses a two-agent coding team:

- **Claude (Opus 4.6)** = リーダー / アーキテクト / レビュアー
  - 設計判断、タスク分解、コード品質の最終判断
  - 複雑なリファクタリング、アーキテクチャ変更
  - コードレビューと品質ゲート

- **Codex CLI (GPT-5.4 via ChatGPTサブスク)** = 開発者 / 実装担当
  - MCP経由で `mcp__multi__chat(model="cx-cli", message="...")` で呼び出し
  - 定型的な実装タスク、テスト作成、ボイラープレート生成
  - 追加APIコスト無し（ChatGPTサブスクリプション内）

## Delegation Rules

### Codexに委譲するタスク
- 新しいモジュール/関数の実装（設計はClaudeが行い、実装指示をCodexに渡す）
- テストコードの作成
- ドキュメント生成
- 定型的なリファクタリング（変数リネーム、型アノテーション追加等）
- FFmpegコマンド構築などのユーティリティ実装

### Claudeが直接行うタスク
- アーキテクチャ設計と判断
- Codexの出力レビューと修正
- セキュリティに関わる変更
- 複雑なバグ修正（デバッグ推論が必要なもの）
- Git操作（commit, branch管理）

## Workflow

1. ユーザーからのリクエストを受ける
2. Claudeがタスクを分解し、実装計画を立てる
3. 実装タスクをCodexに委譲（MCP tool経由）
4. Codexの出力をClaudeがレビュー
5. 必要に応じて修正・統合
6. ユーザーに結果を報告

## Important

- Codexが直接ファイルを変更した場合、必ずgit diffで差分確認してからコミット
- Codexへの指示は具体的に：ファイルパス、関数名、期待する振る舞いを明記
- Codexとの同時編集を避ける（同じファイルをClaudeとCodexが同時に触らない）

## Project Structure

```
src/video_studio/
├── core/          # Pipeline, project, timeline, ffmpeg utilities
├── gui/           # PySide6 GUI (main window, panels, dialogs)
├── audio/         # BGM, audio mixing
├── avatar/        # AI avatar (SadTalker, Wav2Lip)
├── subtitles/     # Subtitle rendering, TTS
├── mosaic/        # Mosaic/blur effects
├── annotation/    # Shape annotations
└── editor/        # Video trimming, concatenation
```

## Tech Stack
- Python 3.9+
- PySide6 (GUI)
- FFmpeg (video processing)
- pytest (testing)
