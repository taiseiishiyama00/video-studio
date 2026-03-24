"""強調マークの図形定義: 丸囲み・矢印・ハイライト枠"""

from __future__ import annotations

import cv2
import numpy as np


def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB → (B, G, R) for OpenCV"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


def draw_circle(
    frame: np.ndarray,
    cx: int,
    cy: int,
    r: int,
    color: str = "#FF0000",
    thickness: int = 3,
) -> np.ndarray:
    """丸囲みを描画"""
    result = frame.copy()
    bgr = hex_to_bgr(color)
    cv2.circle(result, (cx, cy), r, bgr, thickness, cv2.LINE_AA)
    return result


def draw_arrow(
    frame: np.ndarray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: str = "#FF0000",
    thickness: int = 3,
) -> np.ndarray:
    """矢印を描画"""
    result = frame.copy()
    bgr = hex_to_bgr(color)
    cv2.arrowedLine(result, (x1, y1), (x2, y2), bgr, thickness, cv2.LINE_AA, tipLength=0.05)
    return result


def draw_rect_highlight(
    frame: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    color: str = "#FF0000",
    thickness: int = 3,
) -> np.ndarray:
    """矩形ハイライト枠を描画"""
    result = frame.copy()
    bgr = hex_to_bgr(color)
    cv2.rectangle(result, (x, y), (x + w, y + h), bgr, thickness, cv2.LINE_AA)
    return result
