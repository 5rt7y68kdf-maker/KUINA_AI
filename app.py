import os
import glob
import re
import numpy as np
import pandas as pd
import streamlit as st

# ページ設定
st.set_page_config(
    page_title="KUINA AI | Racing Intelligence",
    page_icon="💎",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    .kuina-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        color: #ffffff; padding: 20px 24px; border-radius: 14px; margin-bottom: 20px;
    }
    .kuina-header h1 { margin: 0; font-size: 24px; font-weight: 800; color: #a5f3fc; }
    .race-banner {
        background: #ffffff; border-left: 5px solid #6366f1; padding: 14px 18px;
        border-radius: 12px; margin-bottom: 16px; border: 1px solid #e2e8f0;
    }
    .horse-card {
        background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0;
        padding: 16px; margin-bottom: 12px;
    }
    .score-badge { font-size: 24px; font-weight: 900; color: #4f46e5; }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def scan_and_load_all_csvs():
    """出走表CSVの軽量高速ロード"""
    raw_files = glob.glob("./*.csv") + glob.glob("./*.CSV")
    all_csv_files = [
        f for f in raw_files
        if "枠番" not in f and "脚質" not in f
    ]

    date_races_map = {}
    for fpath in sorted(all_csv_files):
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, header=None, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass

        if df is None or df.empty or len(df.columns) < 12:
            continue

        races_by_key = {}
        for row in df.values:
            col0 = str(row[0]).strip() if pd.notna(row[0]) else ""
            clean_date = col0.replace("-", "")
            if not clean_date.isdigit():
                continue

            if len(clean_date) == 6:
                date_str = f"20{clean_date[:2]}-{clean_date[2:4]}-{clean_date[4:6]}"
            elif len(clean_date) == 8:
                date_str = f"{clean_date[:4]}-{clean_date[4:6]}-{clean_date[6:8]}"
            else:
                continue

            track = str(row[1]).strip() if pd.notna(row[1]) else ""
            rnum_str = str(row[2]).strip() if pd.notna(row[2]) else "1"
            rnum = int(rnum_str) if rnum_str.isdigit() else 1
            cond = str(row[4]).strip() if pd.notna(row[4]) else ""
            track_type = str(row[5]).strip() if pd.notna(row[5]) else ""
            dist = str(row[6]).strip() if pd.notna(row[6]) else ""
            horse_name = str(row[7]).strip() if pd.notna(row[7]) else ""
            jockey = str(row[10]).strip() if pd.notna(row[10]) else "未定"

            if not horse_name:
                continue

            key = (date_str, track, rnum)
            if key not in races_by_key:
                races_by_key[key] = {
                    "date": date_str, "track": track, "rnum": rnum,
                    "cond": cond, "track_type": track_type, "dist": dist,
                    "horses": []
                }

            races_by_key[key]["horses"].append({
                "馬番": len(races_by_key[key]["horses"]) + 1,
                "枠番": (len(races_by_key[key]["horses"]) // 2) + 1,
                "馬名": horse_name,
                "騎手": jockey,
            })

        for key, rdata in races_by_key.items():
            d_str = rdata["date"]
            if d_str not in date_races_map:
                date_races_map[d_str] = []
            date_races_map[d_str].append(rdata)

    return date_races_map


st.markdown("""
<div class="kuina-header">
    <h1>💎 KUINA AI | Racing Intelligence</h1>
    <p>Render最適化高速版エンジン動作中</p>
</div>
""", unsafe_allow_html=True)

date_races_map = scan_and_load_all_csvs()
available_dates = sorted(list(date_races_map.keys()))

if not available_dates:
    st.warning("⚠️ 出走表CSVデータを読み込み中または未配置です。")
    st.stop()

selected_date_str = st.selectbox("📅 開催日を選択", available_dates, index=len(available_dates)-1)
races_for_date = date_races_map.get(selected_date_str, [])

race_options = [
    {"idx": i, "label": f"🏇 【{r['track']}】 {r['rnum']}R {r['cond']} [{r['track_type']}{r['dist']}m] ({len(r['horses'])}頭立)", "data": r}
    for i, r in enumerate(races_for_date)
]

selected_idx = st.selectbox("🏇 レースを選択", range(len(race_options)), format_func=lambda x: race_options[x]["label"])
selected_race = race_options[selected_idx]["data"]

st.markdown(f"""
<div class="race-banner">
    <h4>🔍 選択レース: {selected_date_str} {selected_race['track']} {selected_race['rnum']}R ({selected_race['cond']})</h4>
</div>
""", unsafe_allow_html=True)

# 簡易計算表示
horses = selected_race["horses"]
for idx, h in enumerate(horses, 1):
    score = round(80.0 - idx * 2.5 + (len(h["馬名"]) % 3), 1)
    st.markdown(f"""
    <div class="horse-card">
        <b>#{idx} {h['馬名']}</b> (枠{h['枠番']} {h['馬番']}番) ｜ 騎手: {h['騎手']} ｜ スコア: <b>{score} pt</b>
    </div>
    """, unsafe_allow_html=True)
