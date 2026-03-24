"""レンダリングパイプライン

全処理を正しい順序で実行し、最終動画を書き出す。

処理順序:
  1. カット（不要区間削除・結合）→ マスタータイムライン確定
  2. TTS音声生成（字幕テキスト → 音声ファイル + 表示タイミング算出）
  3. アバター生成（TTS音声 + 静止画 → リップシンク動画）
  4. 映像合成（モザイク + 強調マーク + 字幕 + アバターをフレームに描画）
  5. 音声ミキシング（元音声 + TTS音声 + BGMをミックス）
  6. 最終エンコード → 出力ファイル
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from video_studio.core.ffmpeg_utils import get_duration, mux_audio_video
from video_studio.core.project import Project


class RenderPipeline:
    """レンダリングパイプライン"""

    def __init__(self, project: Project, work_dir: str | Path | None = None):
        self.project = project
        self.work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="vstudio_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def render(self, progress_callback=None) -> Path:
        """全ステップを実行して最終動画を書き出す"""

        def report(step: int, total: int, msg: str):
            if progress_callback:
                progress_callback(step, total, msg)

        total_steps = 6
        output_path = Path(self.project.output)

        # ① カット
        report(1, total_steps, "カット編集中...")
        cut_video = self._step_cut()

        # ② TTS音声生成
        report(2, total_steps, "TTS音声を生成中...")
        tts_results = self._step_tts()

        # ③ アバター準備
        report(3, total_steps, "アバターを準備中...")
        avatar_clips = self._step_avatar(tts_results)

        # ④ 映像合成（モザイク + 強調マーク + 字幕 + アバター）
        report(4, total_steps, "映像を合成中...")
        composed_video = self._step_compose_video(cut_video, tts_results, avatar_clips)

        # ⑤ 音声ミキシング
        report(5, total_steps, "音声をミキシング中...")
        mixed_audio = self._step_mix_audio(cut_video, tts_results)

        # ⑥ 最終エンコード
        report(6, total_steps, "最終エンコード中...")
        self._step_finalize(composed_video, mixed_audio, output_path)

        return output_path

    def _step_cut(self) -> Path:
        """カット編集"""
        from video_studio.editor.trimmer import apply_cuts

        source = Path(self.project.source)
        if not self.project.timeline.cuts:
            # カットなし: 元動画の尺を設定
            duration = get_duration(source)
            self.project.timeline.source_duration = duration
            return source

        output = self.work_dir / "cut.mp4"
        apply_cuts(source, self.project.timeline.cuts, output)
        self.project.timeline.source_duration = get_duration(source)
        return output

    def _step_tts(self) -> list[dict]:
        """TTS音声生成。戻り値: [{entry, audio_path, duration}, ...]"""
        if not self.project.subtitle_track:
            return []

        from video_studio.subtitles.tts import generate_tts

        results = []
        for i, entry in enumerate(self.project.subtitle_track):
            audio_path = self.work_dir / f"tts_{i:04d}.mp3"
            duration = generate_tts(
                entry.text,
                entry.voice,
                audio_path,
                rate=entry.tts_rate,
                pitch=entry.tts_pitch,
            )
            if entry.duration is None:
                entry.duration = duration
            results.append({
                "entry": entry,
                "audio_path": audio_path,
                "duration": duration,
            })
        return results

    def _step_avatar(self, tts_results: list[dict]) -> list[dict]:
        """アバター発話タイミングを準備。戻り値: [{entry, start, duration}, ...]"""
        if not self.project.avatar:
            return []

        clips = []
        for tts in tts_results:
            clips.append({
                "entry": tts["entry"],
                "start": tts["entry"].time,
                "duration": tts["duration"],
            })
        return clips

    def _step_compose_video(
        self,
        base_video: Path,
        tts_results: list[dict],
        avatar_clips: list[dict],
    ) -> Path:
        """映像合成: モザイク + 強調マーク + 字幕 + アバターをフレームに描画"""
        from video_studio.annotation.renderer import draw_annotations
        from video_studio.mosaic.blur import apply_mosaic_regions
        from video_studio.subtitles.renderer import burn_subtitles

        current = base_video

        # モザイク
        if self.project.mosaic_regions:
            mosaic_out = self.work_dir / "mosaic.mp4"
            apply_mosaic_regions(str(current), self.project.mosaic_regions, str(mosaic_out))
            current = mosaic_out

        # 強調マーク
        if self.project.annotations:
            annot_out = self.work_dir / "annotated.mp4"
            draw_annotations(str(current), self.project.annotations, str(annot_out))
            current = annot_out

        # 字幕バーンイン
        if tts_results:
            subs_out = self.work_dir / "subtitled.mp4"
            entries = [(r["entry"], r["duration"]) for r in tts_results]
            burn_subtitles(str(current), entries, self.project.subtitle_style, str(subs_out))
            current = subs_out

        # アバターオーバーレイ
        if self.project.avatar:
            from video_studio.avatar.compositor import overlay_avatar_clips

            avatar_out = self.work_dir / "with_avatar.mp4"
            overlay_avatar_clips(
                str(current),
                avatar_clips,
                self.project.avatar,
                str(avatar_out),
            )
            current = avatar_out

        return current

    def _step_mix_audio(self, cut_video: Path, tts_results: list[dict]) -> Path:
        """音声ミキシング"""
        from video_studio.audio.mixer import mix_audio

        output = self.work_dir / "mixed_audio.mp3"
        video_duration = get_duration(cut_video)

        mix_audio(
            base_video=str(cut_video),
            tts_entries=tts_results,
            bgm_entries=self.project.bgm_track,
            duration=video_duration,
            output_path=str(output),
        )
        return output

    def _step_finalize(self, video: Path, audio: Path, output: Path) -> None:
        """映像と音声を結合して最終出力"""
        output.parent.mkdir(parents=True, exist_ok=True)
        mux_audio_video(video, audio, output)
