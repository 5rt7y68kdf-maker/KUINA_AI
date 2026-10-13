import os
import glob
import re
import json
import math
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ==============================================================================
# 1. ページ基本設定 ＆ スタイリッシュ＆スマホ最適化CSS
# ==============================================================================
st.set_page_config(
    page_title="KUINA AI | Racing Intelligence",
    page_icon="💎",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .kuina-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        color: #ffffff;
        padding: 20px 24px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .kuina-header h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 900;
        letter-spacing: -0.5px;
        background: linear-gradient(to right, #ffffff, #a5f3fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .race-banner {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 6px solid #6366f1;
        padding: 16px 20px;
        border-radius: 14px;
        margin-bottom: 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .race-banner-title {
        font-size: 19px;
        font-weight: 800;
        color: #1e1b4b;
    }
    .race-banner-sub {
        font-size: 13px;
        color: #64748b;
        margin-top: 4px;
    }
    .horse-card {
        background-color: #ffffff;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        transition: all 0.2s ease-in-out;
    }
    .horse-card:hover {
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
    }
    section[data-testid="stSidebar"] {
        display: none;
    }
    .score-badge {
        font-size: 26px;
        font-weight: 900;
        color: #4f46e5;
    }
    .analysis-label {
        font-weight: 800;
        color: #0f172a;
        font-size: 13px;
        margin-top: 8px;
    }
    .analysis-text {
        color: #475569;
        font-size: 12px;
        margin-bottom: 6px;
        line-height: 1.5;
    }
    .ticket-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .ticket-title {
        font-size: 15px;
        font-weight: 800;
        color: #1e1b4b;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
    }
    .ticket-combo {
        font-size: 14px;
        font-weight: 700;
        color: #4338ca;
        background: #eef2ff;
        padding: 6px 10px;
        border-radius: 8px;
        display: inline-block;
        margin-top: 4px;
    }
    @media (max-width: 768px) {
        .kuina-header { padding: 16px 18px; border-radius: 12px; }
        .kuina-header h1 { font-size: 20px; }
        .race-banner { padding: 14px 16px; }
        .race-banner-title { font-size: 16px; }
        .horse-card { padding: 14px; margin-bottom: 12px; }
        .score-badge { font-size: 22px; text-align: left; margin-top: 8px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. ユーティリティ ＆ パース関数
# ==============================================================================

def parse_class_rank(class_str):
    s = str(class_str)
    if any(k in s for k in ["G1", "GⅠ", "GI"]):
        return 9
    if any(k in s for k in ["G2", "GⅡ", "GII"]):
        return 8
    if any(k in s for k in ["G3", "GⅢ", "GIII", "重賞"]):
        return 7
    if any(k in s for k in ["オープン", "OP", "リステッド", "L"]):
        return 6
    if "3勝" in s or "1600万" in s:
        return 5
    if "2勝" in s or "1000万" in s:
        return 4
    if "1勝" in s or "500万" in s:
        return 3
    if "未勝利" in s:
        return 2
    if "新馬" in s:
        return 1
    return 4


def parse_distance_num(dist_str):
    if not dist_str:
        return 0
    m = re.search(r"\d{4}", str(dist_str))
    if m:
        return int(m.group())
    m2 = re.search(r"\d{3,4}", str(dist_str))
    if m2:
        return int(m2.group())
    return 0


def get_jra_waku(umaban, total_horses):
    if total_horses <= 8:
        return umaban
    capacities = [1, 1, 1, 1, 1, 1, 1, 1]
    extras = total_horses - 8
    for i in range(7, -1, -1):
        if extras > 0:
            capacities[i] += 1
            extras -= 1
    curr = 0
    for waku_idx, cap in enumerate(capacities, start=1):
        if curr < umaban <= curr + cap:
            return waku_idx
        curr += cap
    return 8


WAKU_COLOR_MAP = {
    1: ("#ffffff", "#000000"),
    2: ("#1e293b", "#ffffff"),
    3: ("#ef4444", "#ffffff"),
    4: ("#3b82f6", "#ffffff"),
    5: ("#eab308", "#000000"),
    6: ("#22c55e", "#ffffff"),
    7: ("#f97316", "#ffffff"),
    8: ("#ec4899", "#ffffff"),
}

# ==============================================================================
# 3. 高速インデックス ＆ コース統計ロード
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def scan_and_load_all_csvs():
    raw_files = (
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("./data/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv") + glob.glob("/workspace/knowledge/*.CSV")
    )
    raw_files = sorted(list(set(raw_files)))
    all_csv_files = [
        f for f in raw_files
        if not any(k in os.path.basename(f) for k in ["枠番", "脚質", "過去走"])
    ]

    date_races_map = {}

    for fpath in all_csv_files:
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, header=None, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass

        if df is None or df.empty or len(df.columns) < 11:
            continue

        races_by_key = {}
        for row in df.values:
            if len(row) < 11:
                continue

            col0_val = str(row[0]).strip().replace("-", "") if pd.notna(row[0]) else ""
            if not col0_val.isdigit():
                continue

            if len(col0_val) == 6:
                date_str = f"20{col0_val[:2]}-{col0_val[2:4]}-{col0_val[4:6]}"
            elif len(col0_val) == 8:
                date_str = f"{col0_val[:4]}-{col0_val[4:6]}-{col0_val[6:8]}"
            else:
                continue

            track = str(row[1]).strip() if pd.notna(row[1]) else ""
            rnum_str = str(row[2]).strip() if pd.notna(row[2]) else "1"
            rnum = int(rnum_str) if rnum_str.isdigit() else 1
            umaban_str = str(row[3]).strip() if pd.notna(row[3]) else "1"
            cond = str(row[4]).strip() if pd.notna(row[4]) else ""
            track_type = str(row[5]).strip() if pd.notna(row[5]) else ""
            dist = str(row[6]).strip() if pd.notna(row[6]) else ""
            
            horse_name = str(row[7]).strip() if pd.notna(row[7]) else ""
            jockey = str(row[10]).strip() if len(row) > 10 and pd.notna(row[10]) else "未定"
            sire = str(row[16]).strip() if len(row) > 16 and pd.notna(row[16]) else ""
            dam_sire = str(row[20]).strip() if len(row) > 20 and pd.notna(row[20]) else ""

            if not horse_name:
                continue

            prize_money = 0.0
            if len(row) > 27 and pd.notna(row[27]) and str(row[27]).strip().isdigit():
                prize_money = float(str(row[27]).strip())

            umaban_num = int(umaban_str) if umaban_str.isdigit() else 1

            key = (date_str, track, rnum)
            if key not in races_by_key:
                races_by_key[key] = {
                    "date": date_str,
                    "track": track,
                    "rnum": rnum,
                    "cond": cond,
                    "track_type": track_type,
                    "dist": dist,
                    "horses": [],
                }

            races_by_key[key]["horses"].append({
                "馬番": umaban_num,
                "馬名": horse_name,
                "騎手": jockey,
                "父": sire,
                "母父": dam_sire,
                "prize_money": prize_money,
            })

        for key, rdata in races_by_key.items():
            tot = len(rdata["horses"])
            for h in rdata["horses"]:
                if "枠番" not in h:
                    h["枠番"] = get_jra_waku(h["馬番"], tot)

            d_str = rdata["date"]
            if d_str not in date_races_map:
                date_races_map[d_str] = []
            date_races_map[d_str].append(rdata)

    for d_str in date_races_map:
        date_races_map[d_str] = sorted(
            date_races_map[d_str], key=lambda x: (x["track"], x["rnum"])
        )

    return date_races_map


@st.cache_data(ttl=3600, show_spinner=False)
def load_past_races_index():
    json_candidates = ["past_index.json", "./data/past_index.json", "/workspace/knowledge/past_index.json"]
    for jpath in json_candidates:
        if os.path.exists(jpath):
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                pass

    past_files = (
        glob.glob("./*過去走*.csv") + glob.glob("./*過去走*.CSV")
        + glob.glob("./data/*過去走*.csv") + glob.glob("/workspace/knowledge/*過去走*.csv")
    )
    horse_past_map = {}

    for fpath in set(past_files):
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass

        if df is None or df.empty or "馬名" not in df.columns:
            continue

        for row in df.to_dict("records"):
            h_name = str(row.get("馬名", "")).strip()
            if not h_name:
                continue

            if h_name not in horse_past_map:
                horse_past_map[h_name] = []

            if len(horse_past_map[h_name]) < 5:
                horse_past_map[h_name].append({
                    "日付": str(row.get("日付", "")),
                    "競馬場": str(row.get("競馬場", "")),
                    "レース名": str(row.get("レース名", "")),
                    "距離": str(row.get("距離", "")),
                    "馬場状態": str(row.get("馬場状態", "")),
                    "着順": str(row.get("着順", "")),
                    "頭数": str(row.get("頭数", "")),
                    "通過1": str(row.get("通過1", "")),
                    "上り3F": str(row.get("上り3F", "")),
                    "上り順位": str(row.get("上り順位", "")),
                    "着差": str(row.get("着差", "")),
                    "PCI": str(row.get("PCI", "")),
                })

    return horse_past_map


@st.cache_data(ttl=3600, show_spinner=False)
def load_course_stats_index():
    raw_files = (
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("./data/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv") + glob.glob("/workspace/knowledge/*.CSV")
    )
    
    waku_file = None
    kyaku_file = None
    for f in raw_files:
        fname = os.path.basename(f)
        if "枠番" in fname: waku_file = f
        if "脚質" in fname: kyaku_file = f

    stats_map = {}
    if not waku_file or not kyaku_file:
        return stats_map

    try:
        w_df = None
        k_df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                if w_df is None: w_df = pd.read_csv(waku_file, encoding=enc)
                if k_df is None: k_df = pd.read_csv(kyaku_file, encoding=enc)
            except Exception:
                pass

        if w_df is not None and k_df is not None:
            w_df.columns = [str(c).strip().replace("'", "") for c in w_df.columns]
            k_df.columns = [str(c).strip().replace("'", "") for c in k_df.columns]

            courses = w_df["場所･距離"].dropna().unique()
            for c in courses:
                w_sub = w_df[w_df["場所･距離"] == c]
                k_sub = k_df[k_df["場所･距離"] == c]

                tot_races = w_sub["ﾚｰｽ数"].sum() if "ﾚｰｽ数" in w_sub.columns else 1

                w_stats = {}
                for w_num in range(1, 9):
                    col_name = f"{w_num}枠" if f"{w_num}枠" in w_sub.columns else f"{['１','２','３','４','５','６','７','８'][w_num-1]}枠"
                    if col_name in w_sub.columns:
                        val = pd.to_numeric(w_sub[col_name], errors="coerce").mean()
                        w_stats[w_num] = round(float(val), 1) if pd.notna(val) else 12.5
                    else:
                        w_stats[w_num] = 12.5

                k_stats = {}
                for k_name in ["逃げ", "先行", "差し", "追込"]:
                    if k_name in k_sub.columns:
                        val = pd.to_numeric(k_sub[k_name], errors="coerce").mean()
                        k_stats[k_name] = round(float(val), 1) if pd.notna(val) else 25.0
                    else:
                        k_stats[k_name] = 25.0

                stats_map[c] = {
                    "total_races": tot_races,
                    "waku": w_stats,
                    "kyakushitsu": k_stats
                }
    except Exception:
        pass

    return stats_map

# ==============================================================================
# 4. 血統 & AI自動判定 & 馬個別分析エンジン
# ==============================================================================

def determine_ai_track_bias(current_track_condition, current_track_type, current_race_dist_str, expected_pace):
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)
    dist_num = parse_distance_num(current_race_dist_str)

    if current_track_condition in ["重", "不良"]:
        if is_dirt:
            return "超前残り・逃げ天国", "🤖 AI自動判定: 水分を含む足抜き良いダート馬場（逃げ・先行超有利）"
        else:
            return "タフ・スタミナ消耗馬場", "🤖 AI自動判定: 荒れた道悪芝馬場（スタミナ・パワー消耗戦）"
    elif current_track_condition == "稍重":
        if is_dirt:
            return "前残り強", "🤖 AI自動判定: やや時計の出る稍重ダート（前目優勢）"
        else:
            return "外伸び・外差し有利", "🤖 AI自動判定: 稍重で傷んだ内目を避ける（外差し展開）"
    else:
        if is_dirt:
            if expected_pace == "ハイ":
                return "前崩れ・差し必至", "🤖 AI自動判定: ダートハイペース消耗戦（差し・追込有利）"
            else:
                return "内前有利", "🤖 AI自動判定: 標準良馬場ダート（内目・好位有利）"
        else:
            if dist_num <= 1400:
                return "超高速馬場（持ち時計重視）", "🤖 AI自動判定: 芝短距離スピード勝負（高速時計重視）"
            elif expected_pace == "スロー":
                return "超イン伸び・最内ラチ有利", "🤖 AI自動判定: 芝スローペース（最内・イン先行絶好）"
            elif expected_pace == "ハイ":
                return "前崩れ・差し必至", "🤖 AI自動判定: 芝ハイペース展開（外差し・決め手重視）"
            else:
                return "フラット", "🤖 AI自動判定: 標準良馬場（フラット・能力発揮）"


def analyze_bloodline_suitability(sire, dam_sire, current_track_type, current_track_condition, current_race_dist_str):
    sire_str = str(sire) + " " + str(dam_sire)
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)
    is_wet = current_track_condition in ["稍重", "重", "不良"]

    dirt_sires = ["ヘニーヒューズ", "シニスターミニスター", "マジェスティックウォリアー", "パイロ", "ドレフォン", "サウスヴィグラス", "オメガパフューム", "ロードカナロア", "Flatter"]
    power_sires = ["キズナ", "オルフェーヴル", "ルーラーシップ", "バゴ", "ハービンジャー", "ゴールドシップ", "エピファネイア"]

    blood_score = 0.0
    comment = ""

    is_dirt_blood = any(s in sire_str for s in dirt_sires)
    is_power_blood = any(s in sire_str for s in power_sires)

    if is_dirt:
        if is_dirt_blood:
            blood_score += 5.0
            comment = f"父{sire}×母父{dam_sire}。ダート適性の非常に高い血統構成でコース条件にベストマッチ。"
        else:
            comment = f"父{sire}×母父{dam_sire}のダート適性バランス型血統。"
    else:
        if is_wet and is_power_blood:
            blood_score += 6.0
            comment = f"父{sire}×母父{dam_sire}。道悪・タフな芝馬場で真価を発揮するパワー血統構成！"
        else:
            comment = f"父{sire}×母父{dam_sire}のバランス型血統構成。コース条件への適応力は十分。"

    return blood_score, comment


def analyze_horse_with_index(
    horse_name,
    umaban,
    waku,
    total_horses,
    current_race_cond,
    current_race_dist_str,
    current_track_type,
    past_index,
    course_stats_index,
    current_track_condition,
    weather,
    track_bias,
    expected_pace,
    sire="",
    dam_sire="",
):
    past_list = past_index.get(horse_name, [])

    # 1. 脚質 & テン3F推計
    real_style = "先行"
    est_ten3f = 35.0
    pci_vals = []

    if past_list:
        pass1_vals = [
            float(re.search(r"\d+", p["通過1"]).group())
            for p in past_list if p.get("通過1") and re.search(r"\d+", str(p["通過1"]))
        ]
        if pass1_vals:
            avg_p1 = sum(pass1_vals) / len(pass1_vals)
            if avg_p1 <= 2.0: real_style = "逃げ"
            elif avg_p1 <= 5.0: real_style = "先行"
            elif avg_p1 <= 10.0: real_style = "差し"
            else: real_style = "追込"

        for p in past_list:
            pci_str = p.get("PCI", "")
            m = re.search(r"\d+\.\d*", str(pci_str))
            if m:
                pci_vals.append(float(m.group()))

        if real_style == "逃げ": est_ten3f = 33.8
        elif real_style == "先行": est_ten3f = 34.6
        elif real_style == "差し": est_ten3f = 35.5
        else: est_ten3f = 36.2
    else:
        styles = ["逃げ", "先行", "差し", "追込"]
        real_style = styles[(umaban * 3 + len(horse_name)) % 4]

    avg_pci = sum(pci_vals) / len(pci_vals) if pci_vals else 50.0

    # 2. コース5年統計参照スコアリング
    track_name_match = re.search(r"(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)", current_race_cond)
    track_name = track_name_match.group(1) if track_name_match else "東京"
    tt_short = "ダ" if ("ダ" in str(current_track_type) or "ダート" in str(current_track_type)) else "芝"
    dist_num = parse_distance_num(current_race_dist_str)
    course_key = f"{track_name}・{tt_short}{dist_num}m"

    course_stat = course_stats_index.get(course_key, None)
    waku_stat_val = 12.5
    kyaku_stat_val = 25.0
    stat_comment = ""

    if course_stat:
        waku_stat_val = course_stat["waku"].get(waku, 12.5)
        kyaku_stat_val = course_stat["kyakushitsu"].get(real_style, 25.0)
        stat_comment = f" ➔ 【過去5年コース統計】{course_key}の実測複勝率：{waku}枠({waku_stat_val}%)・脚質[{real_style}]({kyaku_stat_val}%)。"

    stat_waku_adj = (waku_stat_val - 12.5) * 0.4
    stat_kyaku_adj = (kyaku_stat_val - 25.0) * 0.2

    # 3. 血統・パワー適性
    blood_score, blood_comment = analyze_bloodline_suitability(sire, dam_sire, current_track_type, current_track_condition, current_race_dist_str)

    # 4. 馬場状態適性
    bad_score_adj = 0.0
    bad_flag = "標準"
    bad_comment = ""
    is_wet_track = current_track_condition in ["稍重", "重", "不良"]

    wet_past_races = [p for p in past_list if p.get("馬場状態") in ["稍重", "重", "不良"]]
    if is_wet_track:
        if wet_past_races:
            best_wet_finish = min([
                int(re.search(r"\d+", p.get("着順", "99")).group())
                for p in wet_past_races if re.search(r"\d+", p.get("着順", "99"))
            ] or [99])
            if best_wet_finish <= 3:
                bad_score_adj += 8.0
                bad_flag = "道悪◎(好実績)"
                bad_comment = f"過去道悪で最高{best_wet_finish}着の実績あり。タフな{current_track_condition}馬場はプラス絶好機。"
            else:
                bad_score_adj += 3.0
                bad_flag = "道悪◯"
                bad_comment = f"道悪経験あり。水を含んだ馬場への対応力向上に期待。"
        else:
            if real_style in ["逃げ", "先行"]:
                bad_score_adj += 4.0
                bad_flag = "道悪注意(前行き)"
                bad_comment = f"{current_track_condition}馬場×前行き脚質（{real_style}）により前残りメリット大。"
            else:
                bad_comment = f"{current_track_condition}馬場での走破実績はなく未知数。"
    else:
        bad_comment = "良馬場開催。軽い馬場でスピードと切れ味を存分に発揮可能。"

    # 5. 枠順 × 脚質クロス判定 ＆ トラックバイアス連動
    waku_score_adj = 0.0
    waku_comment = ""
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)
    cross_flag = ""

    if waku in [1, 2]:
        if is_dirt:
            if real_style in ["差し", "追込"]:
                waku_score_adj -= 3.0
                waku_comment = f"最内{waku}枠。ダート戦で砂被りリスクが高く、後方からの追い上げ苦戦の懸念。"
                cross_flag = "【ダート内枠×後方不向き】最内枠で砂被りのリスクが高く、後方から追う形となり展開不向き（-3.0pt）。"
            else:
                waku_score_adj += 4.0
                waku_comment = f"最内{waku}枠×前行き脚質。砂被りを最小限に抑えてハナ・好位を奪える黄金配置。"
                cross_flag = "【枠×脚質黄金パターン】最内枠から好位を奪いやすくロスなく運べる絶好配置（+4.0pt）。"
        else:
            waku_score_adj += 3.0
            waku_comment = f"絶好の{waku}枠（内枠）。最短距離をロスなく立ち回れる経済コースの恩恵大。"
    elif waku in [7, 8]:
        if is_dirt and real_style in ["逃げ", "先行"]:
            waku_score_adj += 4.0
            waku_comment = f"ダート外{waku}枠×先行。砂被りを完全に回避し外から被せて進出できる黄金パターン。"
            cross_flag = "【ダート外枠×先行黄金パターン】砂被りゼロで外からポジションを取れる理想的配置（+4.0pt）。"
        else:
            waku_comment = f"外枠の{waku}枠。被せられずスムーズに立ち回れる配置。"
    else:
        waku_score_adj += 2.0
        waku_comment = f"自在性の高い{waku}枠（中枠）。展開に応じたポジション取りが可能。"

    # トラックバイアス補正
    tb_adj = 0.0
    tb_comment = ""
    eff_bias = track_bias
    if eff_bias.startswith("🤖"):
        auto_bias, auto_reason = determine_ai_track_bias(current_track_condition, current_track_type, current_race_dist_str, expected_pace)
        eff_bias = auto_bias
        tb_comment = f" ➔ {auto_reason}"

    if "イン伸び" in eff_bias or "内前" in eff_bias:
        if waku <= 4 and real_style in ["逃げ", "先行"]:
            tb_adj = 10.0
            tb_comment += " 【バイアス絶好】内枠×内前展開。グリーンベルトを先手通過。"
        elif waku <= 4:
            tb_adj = 5.0
            tb_comment += " 【バイアス良好】内枠ロスなし追走メリット。"
    elif "外差し" in eff_bias or "外伸び" in eff_bias:
        if waku >= 5 and real_style in ["差し", "追込"]:
            tb_adj = 10.0
            tb_comment += " 【バイアス絶好】外枠×外差し脚質。伸びる外目を一気に強襲。"
    elif "前残り" in eff_bias or "逃げ天国" in eff_bias:
        if real_style == "逃げ":
            tb_adj = 12.0
            tb_comment += " 【バイアス絶好】逃げ天国。マイペース逃げ切り濃厚。"
        elif real_style == "先行":
            tb_adj = 7.0
            tb_comment += " 【バイアス良好】好位前目粘り込み期待。"
    elif "前崩れ" in eff_bias:
        if real_style in ["差し", "追込"]:
            tb_adj = 10.0
            tb_comment += " 【バイアス絶好】前崩れ展開。直線一網打尽の末脚。"

    waku_full_comment = waku_comment + stat_comment + tb_comment

    # 6. 想定ペース × 過去PCI連動 ＆ ラップバランス
    pace_adj = 0.0
    pace_comment = ""
    if expected_pace == "ハイ":
        if avg_pci < 48.0 or real_style in ["差し", "追込"]:
            pace_adj = 4.0
            pace_comment = f"【ハイペース適合】過去平均PCI {avg_pci:.1f}（タフ戦経験あり）。激しいペースでのバテ差し・底力勝負に強い展開好適！（+4.0pt）"
        elif real_style == "逃げ":
            pace_adj = -3.0
            pace_comment = f"【ハイペース注意】他と同型競り合いで前半ハロン消耗のリスク（-3.0pt）。"
    elif expected_pace == "スロー":
        if avg_pci > 52.0 or real_style in ["逃げ", "先行"]:
            pace_adj = 4.0
            pace_comment = f"【スローペース適合】過去平均PCI {avg_pci:.1f}（キレ勝負型）。前半ゆったり流れて楽に先手・瞬発力を発揮可能！（+4.0pt）"
        elif real_style == "追込":
            pace_adj = -3.0
            pace_comment = f"【スローペース不向き】前半ペースが緩むため後方から届かず前残り警戒（-3.0pt）。"
    else:
        pace_comment = f"【平均ペース適合】過去平均PCI {avg_pci:.1f}。淀みのないペースで実力を安定発揮（+2.0pt）。"
        pace_adj = 2.0

    # 7. 前走上がり3F ＆ 着差パフォーマンス
    agari_adj = 0.0
    agari_flag = ""
    agari_comment = ""

    if past_list and len(past_list) > 0:
        last_race = past_list[0]
        agari_rank_str = last_race.get("上り順位", "")
        m_a = re.search(r"\d+", str(agari_rank_str))
        if m_a:
            a_rank = int(m_a.group())
            if a_rank == 1:
                agari_adj += 5.0
                agari_flag = "⚡上がり最速"
                agari_comment = "前走でメンバー最速（上がり1位）の強烈な末脚をマーク！"
            elif a_rank <= 3:
                agari_adj += 2.5
                agari_flag = "⚡上がり上位"
                agari_comment = f"前走上がり{a_rank}位の優秀なキレを維持。"

        margin_str = last_race.get("着差", "")
        m_m = re.search(r"\d+\.\d+", str(margin_str))
        if m_m:
            margin_val = float(m_m.group())
            finish_str = last_race.get("着順", "99")
            finish_num = int(re.search(r"\d+", finish_str).group()) if re.search(r"\d+", finish_str) else 99
            if finish_num >= 5 and margin_val <= 0.5:
                agari_adj += 4.0
                if not agari_flag: agari_flag = "🎯巻き返し注意"
                agari_comment += f" 前走{finish_num}着も勝負どころの着差はわずか{margin_val}秒差！展開不向きでの敗戦で巻き返し有力。"

    # 8. 距離適性・分析
    dist_flag = "適性距離"
    dist_comment = "前走と同等の距離設定推移。"
    curr_dist_num = parse_distance_num(current_race_dist_str)

    if past_list and len(past_list) > 0:
        last_race = past_list[0]
        last_dist_num = parse_distance_num(last_race.get("距離", ""))
        if curr_dist_num > 0 and last_dist_num > 0:
            diff = curr_dist_num - last_dist_num
            if diff <= -200:
                dist_flag = f"距離短縮({diff}m)"
                dist_comment = f"前走{last_dist_num}mから{abs(diff)}mの距離短縮。追走ペースが楽になり末脚爆発の期待大。"
            elif diff >= 200:
                dist_flag = f"距離延長(+{diff}m)"
                dist_comment = f"前走{last_dist_num}mから+{diff}mへの距離延長。道中のゆったりした追走が可能。"

    total_score = round(70.0 + bad_score_adj + waku_score_adj + tb_adj + stat_waku_adj + stat_kyaku_adj + blood_score + pace_adj + agari_adj, 1)

    lap_analysis_comment = f"{pace_comment} {cross_flag}".strip()

    return {
        "real_style": real_style,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
        "waku_comment": waku_full_comment,
        "blood_comment": blood_comment,
        "lap_comment": lap_analysis_comment,
        "agari_flag": agari_flag,
        "agari_comment": agari_comment if agari_comment else "前走での上り脚色推移は標準的。",
        "dist_flag": dist_flag,
        "dist_comment": dist_comment,
        "total_score": total_score,
        "est_ten3f": est_ten3f,
    }

# ==============================================================================
# 5. 3フェーズ展開グラフィック描画エンジン
# ==============================================================================

def render_pace_map_graphic_phase(processed_horses, race_title, track_type, track_bias, phase="向こう正面"):
    fig, ax = plt.subplots(figsize=(12, 4.8), dpi=150)

    is_dirt = "ダ" in str(track_type) or "ダート" in str(track_type)
    bg_dark = '#381c0d' if is_dirt else '#064e3b'
    track_dark = '#542d17' if is_dirt else '#0f766e'
    lane_color = '#78350f' if is_dirt else '#14b8a6'

    fig.patch.set_facecolor(bg_dark)
    ax.set_facecolor(track_dark)

    ax.axhline(0, color=lane_color, linewidth=1.5, linestyle='--')
    ax.axhline(1.5, color=lane_color, linewidth=1, linestyle=':')
    ax.axhline(-1.5, color=lane_color, linewidth=1, linestyle=':')

    phase_label = f"【{phase}】 展開シミュレーション"
    ax.annotate(
        phase_label,
        xy=(0.5, 2.3),
        xytext=(3.5, 2.3),
        arrowprops=dict(facecolor='#fef08a', edgecolor='#fef08a', width=2, headwidth=8),
        fontsize=11,
        fontweight='bold',
        color='#fef08a',
        ha='left'
    )

    zones = [
        ("NIGE (FRONT)", 0.3, 2.7, '#f87171'),
        ("SENKO (PACE)", 3.0, 5.7, '#fbbf24'),
        ("SASHI (MID)", 6.0, 8.7, '#34d399'),
        ("OIKOMI (BACK)", 9.0, 11.7, '#818cf8'),
    ]

    for ztitle, xmin, xmax, zcolor in zones:
        rect = patches.Rectangle((xmin, -2.2), xmax - xmin, 4.2, linewidth=0, facecolor=zcolor, alpha=0.1)
        ax.add_patch(rect)
        ax.text((xmin + xmax)/2, -2.0, ztitle, color=zcolor, fontsize=10, fontweight='bold', ha='center')

    hot_rects = []
    if any(k in track_bias for k in ["イン伸び", "内前", "超イン伸び"]):
        hot_rects.append((0.3, 5.7, 0.2, 1.8))
    elif any(k in track_bias for k in ["外差し", "外伸び"]):
        hot_rects.append((6.0, 11.7, -1.8, 1.8))

    for xmin, xmax, ymin, ymax in hot_rects:
        hot_box = patches.FancyBboxPatch(
            (xmin, ymin), xmax - xmin, ymax - ymin,
            boxstyle="round,pad=0.1,rounding_size=0.2",
            facecolor='#fbbf24', edgecolor='#fef08a', linewidth=2.5, alpha=0.35, zorder=2
        )
        ax.add_patch(hot_box)

    style_groups = {"逃げ": [], "先行": [], "差し": [], "追込": []}
    for h in processed_horses:
        st_name = h["real_style"]
        if st_name not in style_groups: st_name = "先行"
        style_groups[st_name].append(h)

    if phase == "3・4コーナー":
        for st_key in ["差し", "追込"]:
            style_groups[st_key] = sorted(style_groups[st_key], key=lambda x: x["total_score"], reverse=True)
    elif phase == "最終直線":
        all_h = sorted(processed_horses, key=lambda x: x["total_score"], reverse=True)
        style_groups = {"逃げ": all_h[:3], "先行": all_h[3:7], "差し": all_h[7:12], "追込": all_h[12:]}

    zone_x_ranges = {
        "逃げ": (0.6, 2.5),
        "先行": (3.3, 5.5),
        "差し": (6.3, 8.5),
        "追込": (9.3, 11.5),
    }

    for style, h_list in style_groups.items():
        xmin, xmax = zone_x_ranges.get(style, (3.3, 5.5))
        n_horses = len(h_list)
        if n_horses == 0:
            continue

        cols = 2 if n_horses <= 4 else 3
        rows = math.ceil(n_horses / cols)

        x_step = (xmax - xmin) / max(cols - 1, 1) if cols > 1 else 0
        y_step = 0.8 if rows <= 2 else 0.65

        for idx, horse in enumerate(h_list):
            c_idx = idx % cols
            r_idx = idx // cols

            x_pos = xmin + c_idx * x_step if cols > 1 else (xmin + xmax) / 2
            y_pos = 1.2 - r_idx * y_step

            waku = horse["waku"]
            num = horse["num"]
            bg_col, text_col = WAKU_COLOR_MAP.get(waku, ("#ffffff", "#000000"))

            circle = patches.Circle(
                (x_pos, y_pos), 0.36,
                facecolor=bg_col, edgecolor='#f8fafc', linewidth=1.8, zorder=4
            )
            ax.add_patch(circle)

            ax.text(
                x_pos, y_pos, str(num),
                color=text_col, fontsize=11, fontweight='bold',
                ha='center', va='center', zorder=5
            )

    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(-2.5, 2.7)
    ax.axis('off')
    plt.tight_layout()
    return fig

# ==============================================================================
# 6. メイン画面 UI構築
# ==============================================================================

st.markdown(
    """
<div class="kuina-header">
    <h1>💎 KUINA AI | Racing Intelligence System</h1>
</div>
""",
    unsafe_allow_html=True,
)

with st.spinner("データを読み込んでいます..."):
    date_races_map = scan_and_load_all_csvs()
    past_index = load_past_races_index()
    course_stats_index = load_course_stats_index()

available_dates = sorted(list(date_races_map.keys()))

st.markdown("##### レース選択")

if not available_dates:
    st.error("⚠️ 読み込める出走表CSV（20261003.csvなど）が見つかりません。")
    st.stop()

col_search_date, col_search_race = st.columns([1.2, 2.8])

with col_search_date:
    selected_date_str = st.selectbox(
        "📅 開催日を選択",
        available_dates,
        index=len(available_dates) - 1,
    )

races_for_date = date_races_map.get(selected_date_str, [])

race_options = [
    {
        "idx": idx,
        "label": f"【{r['track']}】 {r['rnum']}R {r['cond']} [{r['track_type']}{r['dist']}m] ({len(r['horses'])}頭立)",
        "data": r,
    }
    for idx, r in enumerate(races_for_date)
]

with col_search_race:
    selected_race_combo_idx = st.selectbox(
        "🏇 レースを選択",
        range(len(race_options)),
        format_func=lambda x: race_options[x]["label"],
    )

selected_race_obj = race_options[selected_race_combo_idx]["data"]
clean_race_title = race_options[selected_race_combo_idx]["label"]

current_race_horses = selected_race_obj["horses"]
current_race_cond_name = selected_race_obj.get("cond", "一般特別")
current_race_dist_str = selected_race_obj.get("dist", "1800")
current_track_type = selected_race_obj.get("track_type", "芝")

st.markdown("##### ⚙️ コンディション・バイアス設定")
col_env1, col_env2, col_env3, col_env4 = st.columns(4)

with col_env1:
    weather = st.selectbox("🌤️ 天気", ["晴", "曇", "雨", "雪"])

with col_env2:
    track_condition = st.select_slider(
        "🌧️ 馬場状態", options=["良", "稍重", "重", "不良"]
    )

with col_env3:
    track_bias = st.selectbox(
        "🚩 トラックバイアス",
        [
            "🤖 AI自動判定（馬場・コース連動）",
            "フラット",
            "超イン伸び・最内ラチ有利",
            "内伸び・内前有利",
            "外伸び・外差し有利",
            "外前有利",
            "大外一気・外全振り",
            "超前残り・逃げ天国",
            "前崩れ・差し必至",
            "超高速馬場（持ち時計重視）",
            "タフ・スタミナ消耗馬場",
        ],
    )

with col_env4:
    expected_pace = st.radio(
        "⏱️ 想定ペース",
        ["スロー", "ミドル", "ハイ"],
        index=1,
        horizontal=True,
    )

effective_bias_name = track_bias
ai_reason_text = ""
if track_bias.startswith("🤖"):
    effective_bias_name, ai_reason_text = determine_ai_track_bias(
        track_condition, current_track_type, current_race_dist_str, expected_pace
    )

st.markdown(
    f"""
<div class="race-banner">
    <div class="race-banner-title">
        🔍 選択レース: {selected_date_str} 【 {clean_race_title} 】
    </div>
    <div class="race-banner-sub">
        出走頭数: <b>{len(current_race_horses)}頭 AI完全解析</b> ｜ {ai_reason_text if ai_reason_text else f'設定バイアス: <b>{track_bias}</b>'}
    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.divider()

# --- インデックス参照型 全馬スコア演算 ---
processed_horses = []
tot_horses_count = len(current_race_horses)

for h_data in current_race_horses:
    horse_name = h_data.get("馬名", "不明馬")
    waku = h_data["枠番"]
    umaban = h_data["馬番"]
    sire = h_data.get("父", "")
    dam_sire = h_data.get("母父", "")

    eval_res = analyze_horse_with_index(
        horse_name,
        umaban,
        waku,
        tot_horses_count,
        current_race_cond_name,
        current_race_dist_str,
        current_track_type,
        past_index,
        course_stats_index,
        track_condition,
        weather,
        track_bias,
        expected_pace,
        sire,
        dam_sire,
    )

    processed_horses.append({
        "waku": waku,
        "num": umaban,
        "name": horse_name,
        "jockey": h_data.get("騎手", "未定"),
        "sire": sire,
        "dam_sire": dam_sire,
        "total_score": eval_res["total_score"],
        "real_style": eval_res["real_style"],
        "bad_flag": eval_res["bad_flag"],
        "bad_comment": eval_res["bad_comment"],
        "waku_comment": eval_res["waku_comment"],
        "blood_comment": eval_res["blood_comment"],
        "lap_comment": eval_res["lap_comment"],
        "agari_flag": eval_res["agari_flag"],
        "agari_comment": eval_res["agari_comment"],
        "dist_flag": eval_res["dist_flag"],
        "dist_comment": eval_res["dist_comment"],
    })

ranked_horses = sorted(
    processed_horses, key=lambda x: x["total_score"], reverse=True
)

honmei = ranked_horses[0] if len(ranked_horses) > 0 else None
taikou = ranked_horses[1] if len(ranked_horses) > 1 else None
tanana = ranked_horses[2] if len(ranked_horses) > 2 else None
renka = ranked_horses[3:6] if len(ranked_horses) >= 6 else ranked_horses[3:]

# ==============================================================================
# 7. タブ別表示
# ==============================================================================

tab_rank, tab_pace, tab_tickets = st.tabs([
    "🏆 AI分析スコア",
    "🏇 展開・隊列グラフィック",
    "🎯 AI推奨馬券",
])

with tab_rank:
    st.subheader(f"🏆 【{clean_race_title}】 KUINA AI分析スコア")

    cards_html_list = []
    for rank, horse in enumerate(ranked_horses, start=1):
        crown = (
            "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))
        )

        tags_html = ""
        if horse.get("agari_flag"):
            tags_html += f'<span style="background-color:#8b5cf6; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{horse["agari_flag"]}</span>'

        if "距離短縮" in horse["dist_flag"]:
            tags_html += '<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離短縮</span>'

        if "道悪◎" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◎(好実績)</span>'
        elif "道悪◯" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#10b981; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◯</span>'

        blood_info = f"父: {horse['sire']} ｜ 母父: {horse['dam_sire']}" if horse['sire'] else ""

        card_code = f"""
        <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div style="flex: 1 1 200px; min-width: 180px;">
                <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">
                    枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}
                </div>
                <div style="font-size: 12px; color: #4338ca; font-weight: 700; margin-bottom: 4px;">
                    🧬 {blood_info}
                </div>
                <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                    想定脚質: <b>{horse['real_style']}</b>
                </div>
                <div>{tags_html}</div>
            </div>
            <div style="flex: 2 1 300px; min-width: 250px;">
                <div class="analysis-label">🚩 枠順・展開配置・コース統計評価</div>
                <div class="analysis-text">{horse["waku_comment"]}</div>
                <div class="analysis-label">⏱️ ラップ展開 ＆ クロス適性分析</div>
                <div class="analysis-text">{horse["lap_comment"]}</div>
                <div class="analysis-label">⚡ 前走上がり3F ＆ 着差パフォーマンス</div>
                <div class="analysis-text">{horse["agari_comment"]}</div>
                <div class="analysis-label">🧬 血統・コース適性評価</div>
                <div class="analysis-text">{horse["blood_comment"]}</div>
                <div class="analysis-label">🌧️ 馬場適性・実績評価</div>
                <div class="analysis-text">{horse["bad_comment"]}</div>
            </div>
            <div style="flex: 0 0 80px; text-align: right;">
                <div class="score-badge">{horse["total_score"]} <span style="font-size:13px;">pt</span></div>
            </div>
        </div>
        """
        cards_html_list.append(card_code)

    st.markdown("\n".join(cards_html_list), unsafe_allow_html=True)


with tab_pace:
    st.subheader(f"🏇 【{clean_race_title}】 3フェーズ展開シミュレーショングラフィック")

    phase_tab1, phase_tab2, phase_tab3 = st.tabs([
        "📍 1. 向こう正面 (スタート〜中盤)",
        "🌀 2. 3・4コーナー (勝負所・進出)",
        "🏁 3. 最終直線 (ゴール前・決め手)"
    ])

    with phase_tab1:
        fig1 = render_pace_map_graphic_phase(processed_horses, clean_race_title, current_track_type, effective_bias_name, phase="向こう正面")
        st.pyplot(fig1, use_container_width=True)
        plt.close(fig1)

    with phase_tab2:
        fig2 = render_pace_map_graphic_phase(processed_horses, clean_race_title, current_track_type, effective_bias_name, phase="3・4コーナー")
        st.pyplot(fig2, use_container_width=True)
        plt.close(fig2)

    with phase_tab3:
        fig3 = render_pace_map_graphic_phase(processed_horses, clean_race_title, current_track_type, effective_bias_name, phase="最終直線")
        st.pyplot(fig3, use_container_width=True)
        plt.close(fig3)

    st.markdown("##### 📋 出走馬 枠色連動一覧")

    legend_html_list = []
    for h in sorted(processed_horses, key=lambda x: x["num"]):
        bg_col, text_col = WAKU_COLOR_MAP.get(h["waku"], ("#ffffff", "#000000"))
        item_html = (
            f'<div style="display:inline-flex; align-items:center; background:#ffffff; border:1px solid #cbd5e1; '
            f'border-radius:8px; padding:5px 12px; margin:3px; font-size:13px; font-weight:700;">'
            f'<span style="width:22px; height:22px; border-radius:50%; background-color:{bg_col}; color:{text_col}; '
            f'display:inline-flex; align-items:center; justify-content:center; font-weight:900; font-size:11px; '
            f'margin-right:8px; border:1px solid rgba(0,0,0,0.15);">{h["num"]}</span>'
            f'<span style="color:#1e1b4b;">{h["name"]}</span>'
            f'<span style="color:#64748b; font-size:11px; margin-left:6px;">({h["jockey"]})</span></div>'
        )
        legend_html_list.append(item_html)

    st.markdown(
        f'<div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:8px;">{"".join(legend_html_list)}</div>',
        unsafe_allow_html=True
    )


with tab_tickets:
    st.subheader(f"🎯 【{clean_race_title}】 AI推奨 馬券フォーメーション")

    if honmei and taikou:
        col_mark1, col_mark2, col_mark3, col_mark4 = st.columns(4)
        with col_mark1:
            st.info(f"**◎ 本命**: {honmei['num']}番 **{honmei['name']}**\n\nスコア: {honmei['total_score']} pt")
        with col_mark2:
            st.success(f"**◯ 対抗**: {taikou['num']}番 **{taikou['name']}**\n\nスコア: {taikou['total_score']} pt")
        with col_mark3:
            st.warning(f"**▲ 単穴**: {tanana['num']}番 **{tanana['name']}**\n\nスコア: {tanana['total_score']} pt" if tanana else "なし")
        with col_mark4:
            renka_nums = [str(h['num']) for h in renka]
            st.error(f"**△ 紐・穴**: {', '.join([f'{n}番' for n in renka_nums])}\n\n展開好転予想馬")

        st.divider()
        st.markdown("##### 🎰 推奨馬券フォーメーション (全5種類)")

        h_num = str(honmei['num'])
        t_num = str(taikou['num'])
        a_num = str(tanana['num']) if tanana else ''
        r_nums = [str(h['num']) for h in renka]

        a_and_r = ([a_num] if a_num else []) + r_nums
        a_and_r_str = ", ".join(a_and_r)

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title"><span>馬連 本命・対抗軸</span> <span style="color:#059669;">基本セット</span></div>
                    <div class="ticket-combo">◎ - ◯, ▲ ({h_num} - {t_num}{', ' + a_num if a_num else ''})</div>
                </div>
                <div class="ticket-card">
                    <div class="ticket-title"><span>3連複 軸1頭流し</span> <span style="color:#2563eb;">高回収狙い</span></div>
                    <div class="ticket-combo">軸: ◎ ({h_num}) ➔ 相手: ◯, ▲, △ ({a_and_r_str})</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_t2:
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title"><span>3連単 フォーメーション</span> <span style="color:#7c3aed;">一発逆転</span></div>
                    <div class="ticket-combo">1着: ◎ ({h_num}) ➔ 2着: ◯, ▲ ➔ 3着: ◯, ▲, △</div>
                </div>
                <div class="ticket-card">
                    <div class="ticket-title"><span>ワイド 穴目押さえ</span> <span style="color:#d97706;">安全カバー</span></div>
                    <div class="ticket-combo">◎ - ▲, △ ({h_num} - {', '.join(r_nums)})</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
