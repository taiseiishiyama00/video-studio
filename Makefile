SHELL := /bin/bash
PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin
APP_NAME := Video Studio

.PHONY: help install-system venv install install-avatar install-dev \
        download-models run build-app test lint format clean

help: ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# システム依存関係
# ==============================================================================

install-system: ## システム依存関係をインストール（FFmpeg等）
	@echo "==> システム依存関係をインストール中..."
ifeq ($(shell uname), Darwin)
	brew install ffmpeg
else ifeq ($(shell cat /etc/os-release 2>/dev/null | grep -c ubuntu), 1)
	sudo apt-get update && sudo apt-get install -y ffmpeg
else ifeq ($(shell cat /etc/os-release 2>/dev/null | grep -c debian), 1)
	sudo apt-get update && sudo apt-get install -y ffmpeg
else
	@echo "未対応のOS。FFmpegを手動でインストールしてください: https://ffmpeg.org/download.html"
endif
	@echo "==> 完了"

# ==============================================================================
# Python環境
# ==============================================================================

venv: ## Python仮想環境を作成
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	@echo "==> 仮想環境を作成しました: $(VENV)"

install: venv ## 依存関係をインストール
	$(BIN)/pip install -e .
	@echo "==> インストール完了"

install-avatar: install ## アバター依存関係を追加インストール（PyTorch等）
	$(BIN)/pip install -e ".[avatar]"
	@echo "==> アバター依存関係をインストール完了"

install-dev: install ## 開発用依存関係を追加インストール
	$(BIN)/pip install -e ".[dev]"
	@echo "==> 開発用依存関係をインストール完了"

# ==============================================================================
# モデルダウンロード
# ==============================================================================

download-models: ## アバター用モデルをダウンロード
	@echo "==> SadTalkerモデルをダウンロード中..."
	@mkdir -p models/sadtalker
	@echo "TODO: SadTalkerモデルのダウンロードスクリプトを実装"
	@echo "==> 完了"

# ==============================================================================
# 実行
# ==============================================================================

run: ## GUIアプリを起動
	$(BIN)/video-studio

# ==============================================================================
# macOS .app パッケージング
# ==============================================================================

build-app: install-dev ## macOS .appバンドルを作成
	@echo "==> .appバンドルを作成中..."
	$(BIN)/pyinstaller \
		--name "Video Studio" \
		--windowed \
		--noconfirm \
		--clean \
		--add-data "assets:assets" \
		--hidden-import video_studio.gui \
		--hidden-import video_studio.gui.panels \
		--hidden-import video_studio.core \
		--hidden-import video_studio.editor \
		--hidden-import video_studio.subtitles \
		--hidden-import video_studio.audio \
		--hidden-import video_studio.mosaic \
		--hidden-import video_studio.annotation \
		--hidden-import video_studio.avatar \
		--hidden-import PySide6.QtMultimedia \
		--hidden-import PySide6.QtMultimediaWidgets \
		--collect-all PySide6 \
		src/video_studio/gui/main.py
	@echo "==> 完了: dist/Video Studio.app"
	@echo "==> /Applications にコピーするには: make install-app"

install-app: build-app ## .appを/Applicationsにコピー
	@echo "==> /Applications にコピー中..."
	rm -rf "/Applications/$(APP_NAME).app"
	cp -R "dist/$(APP_NAME).app" "/Applications/$(APP_NAME).app"
	@echo "==> 完了: /Applications/$(APP_NAME).app"

# ==============================================================================
# 開発
# ==============================================================================

test: ## テストを実行
	$(BIN)/pytest tests/ -v

lint: ## リンターを実行
	$(BIN)/ruff check src/ tests/

format: ## コードフォーマット
	$(BIN)/ruff format src/ tests/

clean: ## ビルド成果物をクリーン
	rm -rf build/ dist/ *.egg-info src/*.egg-info *.spec
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
