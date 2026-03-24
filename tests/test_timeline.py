"""タイムラインのテスト"""

from video_studio.core.timeline import Cut, Timeline, format_time, parse_time


class TestParseTime:
    def test_hhmmss(self):
        assert parse_time("01:30:00") == 5400.0

    def test_hhmmss_with_ms(self):
        assert parse_time("00:01:30.500") == 90.5

    def test_mmss(self):
        assert parse_time("01:30") == 90.0

    def test_float(self):
        assert parse_time("90.5") == 90.5

    def test_numeric(self):
        assert parse_time(90) == 90.0


class TestFormatTime:
    def test_basic(self):
        assert format_time(90.5) == "00:01:30.500"

    def test_zero(self):
        assert format_time(0) == "00:00:00.000"

    def test_hours(self):
        assert format_time(3661.0) == "01:01:01.000"


class TestCut:
    def test_duration(self):
        c = Cut(start=10.0, end=30.0)
        assert c.duration == 20.0

    def test_from_dict(self):
        c = Cut.from_dict({"start": "00:00:10", "end": "00:00:30"})
        assert c.start == 10.0
        assert c.end == 30.0


class TestTimeline:
    def test_duration_no_cuts(self):
        t = Timeline(cuts=[], source_duration=120.0)
        assert t.duration == 120.0

    def test_duration_with_cuts(self):
        t = Timeline(cuts=[Cut(10, 30), Cut(50, 70)], source_duration=100.0)
        assert t.duration == 40.0  # 20 + 20

    def test_source_to_timeline(self):
        t = Timeline(cuts=[Cut(10, 30), Cut(50, 70)])
        assert t.source_to_timeline(20.0) == 10.0  # 10秒目のカット内で+10
        assert t.source_to_timeline(55.0) == 25.0  # 20 + 5
        assert t.source_to_timeline(5.0) is None   # カット外

    def test_timeline_to_source(self):
        t = Timeline(cuts=[Cut(10, 30), Cut(50, 70)])
        assert t.timeline_to_source(10.0) == 20.0   # カット1内
        assert t.timeline_to_source(25.0) == 55.0   # カット2内

    def test_full(self):
        t = Timeline.full(60.0)
        assert t.duration == 60.0
        assert t.source_to_timeline(30.0) == 30.0
