"""Streamlit GUIエントリポイント

ブラウザベースのタイムラインエディタUI。
起動: streamlit run src/video_studio/app.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Video Studio", layout="wide")
st.title("Video Studio")


def main():
    # サイドバー: プロジェクト管理
    with st.sidebar:
        st.header("プロジェクト")

        uploaded = st.file_uploader("動画をアップロード", type=["mp4", "mov", "avi", "mkv", "webm"])
        if uploaded:
            tmp = Path(tempfile.mkdtemp()) / uploaded.name
            tmp.write_bytes(uploaded.read())
            st.session_state["source_video"] = str(tmp)
            st.success(f"読み込み: {uploaded.name}")

        project_file = st.file_uploader("プロジェクトJSON", type=["json"])
        if project_file:
            data = json.loads(project_file.read())
            st.session_state["project_data"] = data
            st.success("プロジェクトを読み込みました")

    if "source_video" not in st.session_state:
        st.info("左のサイドバーから動画をアップロードしてください。")
        return

    source = st.session_state["source_video"]

    # 動画プレビュー
    st.subheader("動画プレビュー")
    st.video(source)

    # タブで各機能を切り替え
    tabs = st.tabs(["カット", "字幕 + TTS", "BGM", "モザイク", "強調マーク", "アバター", "レンダリング"])

    # --- カット ---
    with tabs[0]:
        _tab_cut(source)

    # --- 字幕 + TTS ---
    with tabs[1]:
        _tab_subtitle()

    # --- BGM ---
    with tabs[2]:
        _tab_bgm()

    # --- モザイク ---
    with tabs[3]:
        _tab_mosaic()

    # --- 強調マーク ---
    with tabs[4]:
        _tab_annotation()

    # --- アバター ---
    with tabs[5]:
        _tab_avatar()

    # --- レンダリング ---
    with tabs[6]:
        _tab_render(source)


def _tab_cut(source: str):
    st.subheader("カット編集")
    st.caption("残す区間を追加してください。未指定の場合は元動画全体を使用します。")

    if "cuts" not in st.session_state:
        st.session_state["cuts"] = []

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cut_start = st.text_input("開始時間", value="00:00:00", key="cut_start")
    with col2:
        cut_end = st.text_input("終了時間", value="00:01:00", key="cut_end")
    with col3:
        if st.button("区間追加", key="add_cut"):
            st.session_state["cuts"].append({"start": cut_start, "end": cut_end})

    if st.session_state["cuts"]:
        st.write("残す区間:")
        for i, c in enumerate(st.session_state["cuts"]):
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"{i+1}. {c['start']} - {c['end']}")
            if col_b.button("削除", key=f"del_cut_{i}"):
                st.session_state["cuts"].pop(i)
                st.rerun()


def _tab_subtitle():
    st.subheader("字幕 + TTS")
    st.caption("タイムライン上の時点にテキストを配置すると、字幕とTTS音声が同時に挿入されます。")

    if "subtitles" not in st.session_state:
        st.session_state["subtitles"] = []

    col1, col2 = st.columns([1, 3])
    with col1:
        sub_time = st.text_input("挿入時点", value="00:00:00", key="sub_time")
    with col2:
        sub_text = st.text_input("テキスト", key="sub_text")

    sub_voice = st.selectbox(
        "音声",
        ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural", "en-US-JennyNeural", "en-US-GuyNeural"],
        key="sub_voice",
    )

    if st.button("字幕追加", key="add_sub"):
        if sub_text:
            st.session_state["subtitles"].append({
                "time": sub_time,
                "text": sub_text,
                "voice": sub_voice,
            })

    if st.session_state["subtitles"]:
        st.write("字幕一覧:")
        for i, s in enumerate(st.session_state["subtitles"]):
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"{i+1}. [{s['time']}] {s['text']} ({s['voice']})")
            if col_b.button("削除", key=f"del_sub_{i}"):
                st.session_state["subtitles"].pop(i)
                st.rerun()


def _tab_bgm():
    st.subheader("BGM")
    st.caption("区間を指定してBGMを配置します。音源はその区間内でループ再生されます。")

    if "bgm_entries" not in st.session_state:
        st.session_state["bgm_entries"] = []

    col1, col2 = st.columns(2)
    with col1:
        bgm_start = st.text_input("開始時間", value="00:00:00", key="bgm_start")
    with col2:
        bgm_end = st.text_input("終了時間", value="00:01:00", key="bgm_end")

    bgm_file = st.file_uploader("BGM音源", type=["mp3", "wav", "ogg", "aac"], key="bgm_file")
    bgm_mute = st.checkbox("無音（音源なし）", key="bgm_mute")
    bgm_volume = st.slider("音量 (dB)", -30, 0, -18, key="bgm_volume")

    if st.button("BGM追加", key="add_bgm"):
        source = None
        if bgm_file and not bgm_mute:
            tmp = Path(tempfile.mkdtemp()) / bgm_file.name
            tmp.write_bytes(bgm_file.read())
            source = str(tmp)

        st.session_state["bgm_entries"].append({
            "start": bgm_start,
            "end": bgm_end,
            "source": source,
            "volume": bgm_volume,
        })

    if st.session_state["bgm_entries"]:
        st.write("BGM一覧:")
        for i, b in enumerate(st.session_state["bgm_entries"]):
            col_a, col_b = st.columns([4, 1])
            src = b["source"] if b["source"] else "(無音)"
            col_a.write(f"{i+1}. {b['start']} - {b['end']} | {src} | {b['volume']}dB")
            if col_b.button("削除", key=f"del_bgm_{i}"):
                st.session_state["bgm_entries"].pop(i)
                st.rerun()


def _tab_mosaic():
    st.subheader("モザイク")
    st.caption("画面上の矩形領域を指定し、モザイクを適用します。")

    if "mosaic_regions" not in st.session_state:
        st.session_state["mosaic_regions"] = []

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        mx = st.number_input("X", value=0, key="mosaic_x")
    with col2:
        my = st.number_input("Y", value=0, key="mosaic_y")
    with col3:
        mw = st.number_input("幅", value=100, key="mosaic_w")
    with col4:
        mh = st.number_input("高さ", value=100, key="mosaic_h")

    col5, col6 = st.columns(2)
    with col5:
        ms = st.text_input("開始時間", value="00:00:00", key="mosaic_start")
    with col6:
        me = st.text_input("終了時間", value="00:00:10", key="mosaic_end")

    mosaic_mode = st.selectbox("モード", ["pixelate", "blur"], key="mosaic_mode")

    if st.button("モザイク追加", key="add_mosaic"):
        st.session_state["mosaic_regions"].append({
            "rect": [int(mx), int(my), int(mw), int(mh)],
            "start": ms,
            "end": me,
            "mode": mosaic_mode,
        })

    if st.session_state["mosaic_regions"]:
        st.write("モザイク一覧:")
        for i, m in enumerate(st.session_state["mosaic_regions"]):
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"{i+1}. {m['rect']} | {m['start']}-{m['end']} | {m['mode']}")
            if col_b.button("削除", key=f"del_mosaic_{i}"):
                st.session_state["mosaic_regions"].pop(i)
                st.rerun()


def _tab_annotation():
    st.subheader("強調マーク")
    st.caption("丸囲み・矢印・ハイライト枠を配置します。")

    if "annotations" not in st.session_state:
        st.session_state["annotations"] = []

    annot_type = st.selectbox(
        "種類",
        ["circle", "arrow", "rect_highlight"],
        format_func=lambda x: {"circle": "丸囲み", "arrow": "矢印", "rect_highlight": "矩形ハイライト"}[x],
        key="annot_type",
    )

    if annot_type == "circle":
        col1, col2, col3 = st.columns(3)
        with col1:
            cx = st.number_input("中心X", value=500, key="annot_cx")
        with col2:
            cy = st.number_input("中心Y", value=300, key="annot_cy")
        with col3:
            cr = st.number_input("半径", value=50, key="annot_r")
        position = [int(cx), int(cy), int(cr)]
    elif annot_type == "arrow":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ax1 = st.number_input("始点X", value=200, key="annot_ax1")
        with col2:
            ay1 = st.number_input("始点Y", value=100, key="annot_ay1")
        with col3:
            ax2 = st.number_input("終点X", value=400, key="annot_ax2")
        with col4:
            ay2 = st.number_input("終点Y", value=300, key="annot_ay2")
        position = [int(ax1), int(ay1), int(ax2), int(ay2)]
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            rx = st.number_input("X", value=100, key="annot_rx")
        with col2:
            ry = st.number_input("Y", value=100, key="annot_ry")
        with col3:
            rw = st.number_input("幅", value=200, key="annot_rw")
        with col4:
            rh = st.number_input("高さ", value=150, key="annot_rh")
        position = [int(rx), int(ry), int(rw), int(rh)]

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        a_start = st.text_input("開始時間", value="00:00:00", key="annot_start")
    with col_t2:
        a_end = st.text_input("終了時間", value="00:00:05", key="annot_end")

    a_color = st.color_picker("色", value="#FF0000", key="annot_color")
    a_thickness = st.slider("線の太さ", 1, 10, 3, key="annot_thickness")

    if st.button("マーク追加", key="add_annot"):
        st.session_state["annotations"].append({
            "type": annot_type,
            "position": position,
            "start": a_start,
            "end": a_end,
            "color": a_color,
            "thickness": a_thickness,
        })

    if st.session_state["annotations"]:
        st.write("マーク一覧:")
        type_names = {"circle": "丸囲み", "arrow": "矢印", "rect_highlight": "矩形ハイライト"}
        for i, a in enumerate(st.session_state["annotations"]):
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"{i+1}. {type_names[a['type']]} | {a['start']}-{a['end']} | {a['color']}")
            if col_b.button("削除", key=f"del_annot_{i}"):
                st.session_state["annotations"].pop(i)
                st.rerun()


def _tab_avatar():
    st.subheader("アバター")
    st.caption("静止画からリップシンク付きアバターを生成します。字幕のTTS音声に連動して口を動かします。")

    avatar_img = st.file_uploader("アバター画像", type=["png", "jpg", "jpeg"], key="avatar_img")
    if avatar_img:
        tmp = Path(tempfile.mkdtemp()) / avatar_img.name
        tmp.write_bytes(avatar_img.read())
        st.session_state["avatar_image"] = str(tmp)
        st.image(str(tmp), width=200)

    avatar_pos = st.selectbox(
        "表示位置",
        ["bottom-right", "bottom-left", "top-right", "top-left"],
        format_func=lambda x: {"bottom-right": "右下", "bottom-left": "左下", "top-right": "右上", "top-left": "左上"}[x],
        key="avatar_pos",
    )
    st.session_state["avatar_position"] = avatar_pos

    avatar_scale = st.slider("サイズ（画面比率）", 0.1, 0.5, 0.25, key="avatar_scale")
    st.session_state["avatar_scale"] = avatar_scale

    from video_studio.avatar.sadtalker import is_available as sadtalker_available
    if sadtalker_available():
        st.success("SadTalker: 利用可能")
    else:
        st.warning("SadTalker: 未インストール（静止画フォールバックを使用）")


def _tab_render(source: str):
    st.subheader("レンダリング")
    st.caption("全要素を合成して最終動画を書き出します。")

    # プロジェクトデータを構築
    project_data = _build_project_data(source)

    st.write("プロジェクト設定:")
    st.json(project_data)

    if st.button("レンダリング開始", type="primary", key="render_btn"):
        from video_studio.core.pipeline import RenderPipeline
        from video_studio.core.project import Project

        proj = Project.from_dict(project_data)
        output_path = Path(tempfile.mkdtemp()) / "output.mp4"
        proj.output = str(output_path)

        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress(step, total, msg):
            progress_bar.progress(step / total)
            status_text.text(f"[{step}/{total}] {msg}")

        try:
            pipeline = RenderPipeline(proj)
            result = pipeline.render(progress_callback=progress)
            st.success(f"レンダリング完了!")
            st.video(str(result))

            with open(result, "rb") as f:
                st.download_button("ダウンロード", f.read(), file_name="output.mp4", mime="video/mp4")
        except Exception as e:
            st.error(f"エラー: {e}")


def _build_project_data(source: str) -> dict:
    """セッション状態からプロジェクトデータを構築"""
    data: dict = {"source": source}

    cuts = st.session_state.get("cuts", [])
    if cuts:
        data["cuts"] = cuts

    subtitles = st.session_state.get("subtitles", [])
    if subtitles:
        data["subtitle_track"] = subtitles

    bgm_entries = st.session_state.get("bgm_entries", [])
    if bgm_entries:
        data["bgm_track"] = bgm_entries

    mosaic_regions = st.session_state.get("mosaic_regions", [])
    if mosaic_regions:
        data["mosaic_regions"] = mosaic_regions

    annotations = st.session_state.get("annotations", [])
    if annotations:
        data["annotations"] = annotations

    if st.session_state.get("avatar_image"):
        data["avatar"] = {
            "image": st.session_state["avatar_image"],
            "position": st.session_state.get("avatar_position", "bottom-right"),
            "scale": st.session_state.get("avatar_scale", 0.25),
        }

    return data


if __name__ == "__main__":
    main()
else:
    main()
