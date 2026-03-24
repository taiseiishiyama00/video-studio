"""強調マークのテスト"""

import numpy as np

from video_studio.annotation.shapes import draw_arrow, draw_circle, draw_rect_highlight, hex_to_bgr


class TestHexToBgr:
    def test_red(self):
        assert hex_to_bgr("#FF0000") == (0, 0, 255)

    def test_green(self):
        assert hex_to_bgr("#00FF00") == (0, 255, 0)

    def test_blue(self):
        assert hex_to_bgr("#0000FF") == (255, 0, 0)

    def test_no_hash(self):
        assert hex_to_bgr("FF0000") == (0, 0, 255)


class TestDrawShapes:
    def _frame(self):
        return np.zeros((500, 500, 3), dtype=np.uint8)

    def test_circle(self):
        frame = self._frame()
        result = draw_circle(frame, 250, 250, 50, "#FF0000", 3)
        assert result.shape == frame.shape
        # 円が描かれたので元と異なるはず
        assert not np.array_equal(result, frame)

    def test_arrow(self):
        frame = self._frame()
        result = draw_arrow(frame, 100, 100, 400, 400, "#00FF00", 3)
        assert not np.array_equal(result, frame)

    def test_rect_highlight(self):
        frame = self._frame()
        result = draw_rect_highlight(frame, 100, 100, 200, 200, "#0000FF", 3)
        assert not np.array_equal(result, frame)
