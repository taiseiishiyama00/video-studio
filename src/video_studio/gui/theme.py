"""Video Studio ダークテーマ

DaVinci Resolve / Premiere Pro 風のプロフェッショナルUI。
"""

from __future__ import annotations


COLORS = {
    "bg_darkest": "#111115",
    "bg_dark": "#1a1a20",
    "bg_mid": "#232328",
    "bg_light": "#2b2b32",
    "bg_lighter": "#35353d",
    "border": "#3a3a42",
    "border_light": "#4a4a52",
    "text": "#d8d8dc",
    "text_dim": "#8a8a92",
    "text_bright": "#f0f0f4",
    "accent": "#00b4d8",
    "accent_dark": "#0077b6",
    "accent_hover": "#48cae4",
    "danger": "#ff4757",
    "success": "#2ed573",
    "warning": "#ffa502",
}


def get_stylesheet() -> str:
    """アプリ全体のQSSを返す"""
    c = COLORS
    return f"""
    /* === ベース === */
    QMainWindow, QDialog {{
        background-color: {c['bg_dark']};
        color: {c['text']};
    }}
    QWidget {{
        background-color: {c['bg_dark']};
        color: {c['text']};
        font-family: "-apple-system", "Helvetica Neue", "Hiragino Sans", sans-serif;
        font-size: 13px;
    }}

    /* === メニューバー === */
    QMenuBar {{
        background-color: {c['bg_darkest']};
        color: {c['text']};
        border-bottom: 1px solid {c['border']};
        padding: 2px 0;
    }}
    QMenuBar::item {{
        padding: 5px 12px;
        border-radius: 4px;
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {c['bg_lighter']};
    }}
    QMenu {{
        background-color: {c['bg_mid']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 28px 6px 12px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {c['accent_dark']};
        color: {c['text_bright']};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 8px;
    }}

    /* === ボタン === */
    QPushButton {{
        background-color: {c['bg_lighter']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        padding: 6px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c['border_light']};
        border-color: {c['accent']};
    }}
    QPushButton:pressed {{
        background-color: {c['accent_dark']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_mid']};
        color: {c['text_dim']};
        border-color: {c['bg_lighter']};
    }}
    QPushButton:checked {{
        background-color: {c['accent_dark']};
        color: {c['text_bright']};
        border-color: {c['accent']};
    }}

    /* === アクセントボタン (objectName="accentBtn") === */
    QPushButton#accentBtn {{
        background-color: {c['accent_dark']};
        color: {c['text_bright']};
        border: none;
        font-weight: bold;
    }}
    QPushButton#accentBtn:hover {{
        background-color: {c['accent']};
    }}

    /* === 入力 === */
    QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox {{
        background-color: {c['bg_darkest']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 5px 8px;
        selection-background-color: {c['accent_dark']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QAbstractSpinBox:focus {{
        border-color: {c['accent']};
    }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
        background-color: {c['bg_mid']};
        border: none;
        width: 18px;
        border-left: 1px solid {c['border']};
    }}
    QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
        background-color: {c['bg_lighter']};
    }}

    /* === コンボボックス === */
    QComboBox {{
        background-color: {c['bg_lighter']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 5px 8px;
        min-width: 100px;
    }}
    QComboBox:hover {{
        border-color: {c['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c['text_dim']};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_mid']};
        color: {c['text']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent_dark']};
        border-radius: 4px;
    }}

    /* === スライダー === */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c['bg_lighter']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        margin: -5px 0;
        background: {c['accent']};
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {c['accent_hover']};
    }}
    QSlider::sub-page:horizontal {{
        background: {c['accent_dark']};
        border-radius: 2px;
    }}
    QSlider::add-page:horizontal {{
        background: {c['bg_lighter']};
        border-radius: 2px;
    }}

    /* === チェックボックス === */
    QCheckBox {{
        color: {c['text']};
        spacing: 6px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {c['border_light']};
        border-radius: 3px;
        background-color: {c['bg_darkest']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent']};
        border-color: {c['accent']};
    }}

    /* === ラベル === */
    QLabel {{
        background: transparent;
        color: {c['text']};
    }}

    /* === プログレスバー === */
    QProgressBar {{
        background-color: {c['bg_darkest']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        text-align: center;
        color: {c['text']};
        height: 18px;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 3px;
    }}

    /* === スクロールバー === */
    QScrollBar:vertical {{
        background: {c['bg_dark']};
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {c['bg_lighter']};
        min-height: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['border_light']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: {c['bg_dark']};
        height: 10px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['bg_lighter']};
        min-width: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['border_light']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    /* === リストウィジェット === */
    QListWidget {{
        background-color: {c['bg_darkest']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 4px 8px;
        border-radius: 3px;
    }}
    QListWidget::item:selected {{
        background-color: {c['accent_dark']};
        color: {c['text_bright']};
    }}
    QListWidget::item:hover {{
        background-color: {c['bg_lighter']};
    }}

    /* === ステータスバー === */
    QStatusBar {{
        background-color: {c['bg_darkest']};
        color: {c['text_dim']};
        border-top: 1px solid {c['border']};
        font-size: 11px;
    }}
    QStatusBar::item {{
        border: none;
    }}

    /* === ダイアログボタンボックス === */
    QDialogButtonBox > QPushButton {{
        min-width: 80px;
    }}

    /* === ツールチップ === */
    QToolTip {{
        background-color: {c['bg_mid']};
        color: {c['text_bright']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    """
