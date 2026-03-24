"""字幕+TTS挿入ダイアログ"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QVBoxLayout,
)

from video_studio.core.project import SubtitleEntry
from video_studio.core.timeline import format_time

VOICES = [
    "ja-JP-NanamiNeural",
    "ja-JP-KeitaNeural",
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "zh-CN-XiaoxiaoNeural",
    "ko-KR-SunHiNeural",
]


class SubtitleDialog(QDialog):
    def __init__(self, source_time: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("字幕 + TTS 挿入")
        self.setMinimumWidth(400)
        self._settings = QSettings("VideoStudio", "VideoStudio")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"挿入位置: {format_time(source_time)}"))

        layout.addWidget(QLabel("テキスト:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("字幕テキストを入力...")
        layout.addWidget(self.text_input)

        layout.addWidget(QLabel("音声:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(VOICES)
        saved_voice = self._settings.value("subtitle/voice", "")
        if saved_voice and saved_voice in VOICES:
            self.voice_combo.setCurrentText(saved_voice)
        layout.addWidget(self.voice_combo)

        # TTS音量
        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("TTS音量:"))
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(-30, 0)
        saved_vol = int(self._settings.value("subtitle/tts_volume", -6))
        self.vol_slider.setValue(saved_vol)
        vol_row.addWidget(self.vol_slider)
        self.vol_label = QLabel(f"{saved_vol} dB")
        self.vol_slider.valueChanged.connect(lambda v: self.vol_label.setText(f"{v} dB"))
        self.vol_label.setFixedWidth(50)
        vol_row.addWidget(self.vol_label)
        layout.addLayout(vol_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._source_time = source_time
        self.text_input.setFocus()

    def get_entry(self) -> SubtitleEntry | None:
        text = self.text_input.text().strip()
        if not text:
            return None
        voice = self.voice_combo.currentText()
        # 設定を保存
        self._settings.setValue("subtitle/voice", voice)
        self._settings.setValue("subtitle/tts_volume", self.vol_slider.value())
        return SubtitleEntry(
            time=self._source_time,
            text=text,
            voice=voice,
            tts_volume=self.vol_slider.value(),
        )
