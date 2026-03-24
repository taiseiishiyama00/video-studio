"""アバター合成のテスト"""

import numpy as np

from video_studio.avatar.compositor import _overlay_frame


def test_overlay_frame_preserves_base_for_transparent_pixels():
    base = np.full((4, 4, 3), 50, dtype=np.uint8)
    overlay = np.zeros((2, 2, 4), dtype=np.uint8)
    overlay[:, :, :3] = 200
    overlay[:, :, 3] = 0

    result = _overlay_frame(base, overlay, 1, 1)

    assert np.array_equal(result, base)


def test_overlay_frame_blends_alpha_pixels():
    base = np.zeros((4, 4, 3), dtype=np.uint8)
    overlay = np.zeros((2, 2, 4), dtype=np.uint8)
    overlay[:, :, 0] = 120
    overlay[:, :, 1] = 180
    overlay[:, :, 2] = 240
    overlay[:, :, 3] = 128

    result = _overlay_frame(base, overlay, 1, 1)

    pixel = result[1, 1]
    assert 50 <= int(pixel[0]) <= 70
    assert 80 <= int(pixel[1]) <= 100
    assert 110 <= int(pixel[2]) <= 130
