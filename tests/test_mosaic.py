"""モザイク処理のテスト"""

import numpy as np

from video_studio.mosaic.blur import blur_region, pixelate_region
from video_studio.mosaic.region import validate_region
from video_studio.core.project import MosaicRegion


class TestPixelate:
    def test_pixelate(self):
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = pixelate_region(frame, 10, 10, 50, 50, 10)
        assert result.shape == frame.shape
        # ピクセレート後、元のフレームとは異なるはず
        assert not np.array_equal(result[10:60, 10:60], frame[10:60, 10:60])

    def test_empty_region(self):
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = pixelate_region(frame, 100, 100, 0, 0, 10)
        assert result.shape == frame.shape


class TestBlur:
    def test_blur(self):
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = blur_region(frame, 10, 10, 50, 50, 10)
        assert result.shape == frame.shape


class TestValidateRegion:
    def test_clamp(self):
        r = MosaicRegion(rect=(900, 900, 200, 200), start=0, end=10)
        clamped = validate_region(r, 1000, 1000)
        x, y, w, h = clamped.rect
        assert x + w <= 1000
        assert y + h <= 1000

    def test_negative(self):
        r = MosaicRegion(rect=(-10, -10, 50, 50), start=0, end=10)
        clamped = validate_region(r, 1000, 1000)
        assert clamped.rect[0] >= 0
        assert clamped.rect[1] >= 0
