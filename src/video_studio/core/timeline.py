"""タイムライン管理

元動画のカット情報と各トラックの時間管理を行う。
カット後のタイムラインが動画全体の尺を支配する。
"""

from __future__ import annotations

from dataclasses import dataclass


def parse_time(time_str: str) -> float:
    """時間文字列をfloat秒に変換。"HH:MM:SS" or "HH:MM:SS.mmm" or float秒"""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(time_str)


def format_time(seconds: float) -> str:
    """float秒を"HH:MM:SS.mmm"に変換"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


@dataclass
class Cut:
    """残す区間（元動画の時間軸）"""

    start: float  # 秒
    end: float  # 秒

    @property
    def duration(self) -> float:
        return self.end - self.start

    @classmethod
    def from_dict(cls, d: dict) -> Cut:
        return cls(start=parse_time(d["start"]), end=parse_time(d["end"]))


@dataclass
class SpeedRegion:
    """速度変更区間（元動画の時間軸）"""

    start: float  # 秒
    end: float  # 秒
    speed: float  # 倍速 (1.0=通常, 2.0=2倍速, 0.5=0.5倍速)

    @property
    def duration(self) -> float:
        """元動画上での長さ"""
        return self.end - self.start

    @property
    def timeline_duration(self) -> float:
        """出力タイムライン上での長さ"""
        return self.duration / self.speed

    @classmethod
    def from_dict(cls, d: dict) -> SpeedRegion:
        return cls(
            start=parse_time(d["start"]),
            end=parse_time(d["end"]),
            speed=float(d.get("speed", 1.0))
        )


@dataclass
class Timeline:
    """カット・速度調整後のタイムライン

    cuts: 元動画から残す区間のリスト（元動画の時間軸）
    speed_regions: 元動画の速度変更区間（元動画の時間軸）

    タイムラインの尺は:
      - カット後に残った部分の合計
      - さらに速度変更を適用（2倍速なら半分の長さ）
    """

    cuts: list[Cut]
    speed_regions: list[SpeedRegion] = None
    source_duration: float = 0.0  # 元動画の長さ

    def __post_init__(self):
        if self.speed_regions is None:
            self.speed_regions = []

    @property
    def duration(self) -> float:
        """カット・速度調整後の総尺"""
        if not self.cuts:
            base_dur = self.source_duration
        else:
            base_dur = sum(c.duration for c in self.cuts)

        # 速度変更を適用
        total_dur = 0.0
        if not self.cuts:
            cuts_list = [Cut(0.0, self.source_duration)]
        else:
            cuts_list = self.cuts

        for cut in cuts_list:
            # この区間内の速度変更を探す
            cur_time = cut.start
            for speed_r in sorted(self.speed_regions, key=lambda x: x.start):
                # speed_region と cut が重複する部分を計算
                overlap_start = max(cur_time, speed_r.start)
                overlap_end = min(cut.end, speed_r.end)
                if overlap_start < overlap_end:
                    # 速度変更区間
                    total_dur += (overlap_end - overlap_start) / speed_r.speed
                    cur_time = overlap_end

            # 速度変更のない部分
            if cur_time < cut.end:
                total_dur += cut.end - cur_time

        return total_dur

    def source_to_timeline(self, source_time: float) -> float | None:
        """元動画の時間 → カット後タイムラインの時間に変換。カット区間外ならNone"""
        if not self.cuts:
            return source_time
        offset = 0.0
        for cut in self.cuts:
            if cut.start <= source_time <= cut.end:
                return offset + (source_time - cut.start)
            offset += cut.duration
        return None

    def timeline_to_source(self, timeline_time: float) -> float:
        """カット後タイムラインの時間 → 元動画の時間に変換"""
        if not self.cuts:
            return timeline_time
        remaining = timeline_time
        for cut in self.cuts:
            if remaining <= cut.duration:
                return cut.start + remaining
            remaining -= cut.duration
        # タイムライン末尾を超えた場合、最後のカットの終了時間を返す
        return self.cuts[-1].end if self.cuts else timeline_time

    @classmethod
    def from_dict_list(cls, cuts_data: list[dict], source_duration: float = 0.0) -> Timeline:
        cuts = [Cut.from_dict(c) for c in cuts_data]
        cuts.sort(key=lambda c: c.start)
        return cls(cuts=cuts, source_duration=source_duration)

    @classmethod
    def full(cls, source_duration: float) -> Timeline:
        """カットなし（元動画全体を使用）"""
        return cls(cuts=[], source_duration=source_duration)

    def to_dict(self) -> dict:
        """タイムラインを辞書に変換"""
        d = {}
        if self.cuts:
            d["cuts"] = [
                {"start": format_time(c.start), "end": format_time(c.end)}
                for c in self.cuts
            ]
        if self.speed_regions:
            d["speed_regions"] = [
                {
                    "start": format_time(r.start),
                    "end": format_time(r.end),
                    "speed": r.speed,
                }
                for r in self.speed_regions
            ]
        return d
