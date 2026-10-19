import os
import glob
import re
import json
import math
import textwrap
import numpy as np
import pandas as pd
import streamlit as st

import matplotlib
matplotlib.use('Agg')
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
    .footer-box {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 18px 22px;
        margin-top: 30px;
        margin-bottom: 20px;
        font-size: 12px;
        color: #64748b;
        line-height: 1.6;
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


# JRA標準枠色マップ (背景色, 文字色)
WAKU_COLOR_MAP = {
    1: ("#ffffff", "#000000"),  # 1枠: 白
    2: ("#1e293b", "#ffffff"),  # 2枠: 黒
    3: ("#ef4444", "#ffffff"),  # 3枠: 赤
    4: ("#3b82f6", "#ffffff"),  # 4枠: 青
    5: ("#eab308", "#000000"),  # 5枠: 黄
    6: ("#22c55e", "#ffffff"),  # 6枠: 緑
    7: ("#f97316", "#ffffff"),  # 7枠: 橙
    8: ("#ec4899", "#ffffff"),  # 8枠: 桃
}

# ==============================================================================
# 3. 高速インデックスロード（確定順位＆血統安全抽出）
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
            
            # 馬名=Index 7, 騎手=Index 10
            horse_name = str(row[7]).strip() if pd.notna(row[7]) else ""
            jockey = str(row[10]).strip() if len(row) > 10 and pd.notna(row[10]) else "未定"

            sire = str(row[16]).strip() if len(row) > 16 and pd.notna(row[16]) else ""
            damsire = str(row[20]).strip() if len(row) > 20 and pd.notna(row[20]) else ""

            if not horse_name:
                continue

            prize_money = 0.0
            if len(row) > 27 and pd.notna(row[27]) and str(row[27]).strip().isdigit():
                prize_money = float(str(row[27]).strip())

            umaban_num = int(umaban_str) if umaban_str.isdigit() else 1
            waku_num = int(row[22]) if len(row) > 22 and str(row[22]).strip().isdigit() else get_jra_waku(umaban_num, 16)
            rank_num = int(row[31]) if len(row) > 31 and str(row[31]).strip().isdigit() else 0
            time_margin = str(row[30]).strip() if len(row) > 30 and pd.notna(row[30]) else "0.0"
            pass1 = str(row[29]).strip() if len(row) > 29 and pd.notna(row[29]) else "0"

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
                "枠番": waku_num,
                "馬名": horse_name,
                "騎手": jockey,
                "prize_money": prize_money,
                "sire": sire,
                "damsire": damsire,
                "確定順位": rank_num,
                "着差": time_margin,
                "通過1": pass1,
            })

        for key, rdata in races_by_key.items():
            tot = len(rdata["horses"])
            for h in rdata["horses"]:
                if "枠番" not in h or h["枠番"] == 0:
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
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("/workspace/knowledge/*.csv")
    )
    horse_past_map = {}

    for fpath in set(past_files):
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, header=None, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass

        if df is None or df.empty or len(df.columns) < 11:
            continue

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

            h_name = str(row[7]).strip() if pd.notna(row[7]) else ""
            if not h_name:
                continue

            rnum_num = int(str(row[2]).strip()) if str(row[2]).strip().isdigit() else 1
            rank_num = int(row[31]) if len(row) > 31 and str(row[31]).strip().isdigit() else 0
            waku_num = int(row[22]) if len(row) > 22 and str(row[22]).strip().isdigit() else 1

            if h_name not in horse_past_map:
                horse_past_map[h_name] = []

            # 日付順でソートできるように格納
            horse_past_map[h_name].append({
                "date": date_str,
                "日付": date_str,
                "rnum": rnum_num,
                "レース番号": rnum_num,
                "通過1": str(row[29]).strip() if len(row) > 29 else "0",
                "馬場状態": "良",
                "確定順位": rank_num,
                "着順": str(rank_num),
                "上り3F順位": "0",
                "PCI": "50.0",
                "クラス": str(row[4]).strip() if len(row) > 4 else "未勝利",
                "着差": str(row[30]).strip() if len(row) > 30 else "0.0",
                "距離": str(row[6]).strip() if len(row) > 6 else "1800",
                "トラック": str(row[5]).strip() if len(row) > 5 else "芝",
                "枠番": waku_num,
                "馬番": int(row[3]) if len(row) > 3 and str(row[3]).strip().isdigit() else 1,
                "sire": str(row[16]).strip() if len(row) > 16 else "",
                "damsire": str(row[20]).strip() if len(row) > 20 else "",
            })

    # 各馬の過去走を日付・レース番号の降順（最新順）にソート
    for h in horse_past_map:
        horse_past_map[h] = sorted(
            horse_past_map[h],
            key=lambda x: (x.get("date", x.get("日付", "")), x.get("rnum", x.get("レース番号", 1))),
            reverse=True
        )

    return horse_past_map


# ==============================================================================
# 4. 全12予想ファクター完全連動 AI解析エンジン
# ==============================================================================

def analyze_horse_with_index(
    horse_name,
    umaban,
    waku,
    total_horses,
    current_race_cond,
    current_race_dist_str,
    current_track_type,
    past_index,
    current_track_condition,
    weather,
    track_bias,
    expected_pace,
    current_race_date="2099-12-31",
    current_race_rnum=99,
    sire="",
    damsire="",
):
    full_past_list = past_index.get(horse_name, [])

    # 当該レース以前の過去走のみ抽出（厳密な直近フィルタリング）
    past_list = [
        p for p in full_past_list
        if p.get("date", p.get("日付", "")) < current_race_date or (
            p.get("date", p.get("日付", "")) == current_race_date and p.get("rnum", p.get("レース番号", 1)) < current_race_rnum
        )
    ]

    # 1. 脚質判定
    real_style = "先行"
    if past_list:
        pass1_vals = [
            float(re.search(r"\d+", str(p.get("通過1", "0"))).group())
            for p in past_list if p.get("通過1") and re.search(r"\d+", str(p.get("通過1", "0")))
        ]
        if pass1_vals and any(v > 0 for v in pass1_vals):
            valid_p1 = [v for v in pass1_vals if v > 0]
            avg_p1 = sum(valid_p1) / len(valid_p1)
            if avg_p1 <= 2.0: real_style = "逃げ"
            elif avg_p1 <= 5.0: real_style = "先行"
            elif avg_p1 <= 10.0: real_style = "差し"
            else: real_style = "追込"
    else:
        styles = ["逃げ", "先行", "差し", "追込"]
        real_style = styles[(umaban * 3 + len(horse_name)) % 4]

    # 2. 直近前走（1走前）パフォーマンス＆着順分析
    last_perf_adj = 0.0
    last_perf_flag = "標準"
    last_perf_comment = ""

    if past_list and len(past_list) > 0:
        last_race = past_list[0]
        last_rank = int(last_race.get("確定順位", last_race.get("着順", "0")))
        last_track = str(last_race.get("トラック", ""))
        last_waku = int(last_race.get("枠番", 0))

        # 前走確定着順判定
        if last_rank == 1:
            last_perf_adj += 8.0
            last_perf_flag = "前走1着(勝利)"
            last_perf_comment += "前走勝ち切る見事なレースで勢い最高潮。 "
        elif 2 <= last_rank <= 5:
            last_perf_adj += 4.0
            last_perf_flag = "前走掲示板"
            last_perf_comment += f"前走掲示板（{last_rank}着）を確保。崩れにくい堅実な競走能力を発揮。 "
        elif last_rank > 0:
            last_perf_comment += f"前走は{last_rank}着と着順を落としましたが、巻き返しの条件揃う。 "

        # 直近の芝➔ダート替わり
        is_curr_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)
        is_last_turf = "芝" in last_track
        if is_curr_dirt and is_last_turf:
            last_perf_adj += 5.0
            last_perf_comment += "前走芝からのダート条件替わり！砂適性発揮による一変に大注目。 "

        # 前走ダート内枠好走
        if "ダ" in last_track and last_waku in [1, 2] and 1 <= last_rank <= 3:
            last_perf_adj += 5.0
            last_perf_comment += f"前走ダート内枠({last_waku}枠)からの好走歴({last_rank}着)あり。キックバックに強い精神力を提示。 "
    else:
        last_perf_comment = "前走データ十分蓄積なし。高いポテンシャルに期待。"

    # 3. 枠番・配置基礎評価（競馬場・コース勝率対応）
    waku_score_adj = 0.0
    waku_comment = ""
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)

    if waku in [1, 2]:
        if is_dirt:
            waku_score_adj -= 2.0
            waku_comment = f"最内{waku}枠。ダート戦のため被せられた際の砂被り（キックバック）リスクに注意。"
        else:
            waku_score_adj += 3.0
            waku_comment = f"絶好の{waku}枠（内枠）。最短距離をロスなく立ち回れる経済コースの恩恵大。"
    elif waku in [3, 4, 5, 6]:
        waku_score_adj += 2.0
        waku_comment = f"自在性の高い{waku}枠（中枠）。展開に応じたポジション取りがしやすく包まれるリスクも低い好配置。"
    else:
        if is_dirt:
            waku_score_adj += 4.0
            waku_comment = f"ダート好走の黄金パターンである外{waku}枠。砂被りを回避しスムーズに外から進出可能。"
        else:
            if total_horses >= 15:
                waku_score_adj -= 3.0
                waku_comment = f"多頭数（{total_horses}頭立）の外{waku}枠。終始外を回らされる距離ロスの懸念あり。"
            else:
                waku_comment = f"外枠の{waku}枠。スムーズに包まれず運べる反面、コーナーでの距離ロスには注意。"

    # 4. 全10バイアス完全連動・高感度加減点エンジン
    tb_adj = 0.0
    tb_comment = ""

    if track_bias == "超イン伸び・最内ラチ有利":
        if waku in [1, 2] and real_style in ["逃げ", "先行"]:
            tb_adj = 12.0
            tb_comment = f" ➔ 【バイアス絶好】{waku}枠の最内ラチ沿い×前行き脚質。最内を通れる最高の展開です。"
        elif waku in [1, 2]:
            tb_adj = 6.0
            tb_comment = f" ➔ 【バイアス良好】{waku}枠の最内枠。内目のグリーンベルトを通れる好位置。"
        elif waku in [3, 4] and real_style in ["逃げ", "先行"]:
            tb_adj = 4.0
            tb_comment = f" ➔ 【バイアスやや良好】{waku}枠からすんなり内に入れて先行できれば強みを発揮。"
        elif waku in [7, 8]:
            tb_adj = -8.0
            tb_comment = f" ➔ 【バイアス大逆風】{waku}枠の外枠によりインコースに入れず大幅不利。"

    elif track_bias in ["内伸び・内前有利", "内前有利"]:
        if waku <= 4 and real_style in ["逃げ", "先行"]:
            tb_adj = 10.0
            tb_comment = f" ➔ 【バイアス絶好】{waku}枠×内前有利。内ラチ沿いを先手奪取できる絶好配置。"
        elif waku <= 4 and real_style == "差し":
            tb_adj = 4.0
            tb_comment = f" ➔ 【バイアス良好】内枠からロスなく差してこれる有利ポジション。"
        elif waku >= 5 and real_style == "追込":
            tb_adj = -6.0
            tb_comment = f" ➔ 【バイアス逆風】外枠×後方追込。内前有利な馬場に泣く厳しい展開。"
        elif waku >= 7:
            tb_adj = -4.0
            tb_comment = f" ➔ 【バイアスやや逆風】外枠につきコーナーでの内入れ苦戦。"

    elif track_bias in ["外伸び・外差し有利", "外差し有利"]:
        if waku >= 5 and real_style in ["差し", "追込"]:
            tb_adj = 10.0
            tb_comment = f" ➔ 【バイアス絶好】{waku}枠×外差し脚質。荒れた内を避けて一気に突き抜ける絶好機会。"
        elif waku >= 5 and real_style == "先行":
            tb_adj = 4.0
            tb_comment = f" ➔ 【バイアス良好】外から被せるように前目をつけて馬場の良い部分を通過可能。"
        elif waku <= 2 and real_style in ["逃げ", "先行"]:
            tb_adj = -6.0
            tb_comment = f" ➔ 【バイアス逆風】最内枠×逃げ・先行。痛んだ内目を通らされる懸念。"

    elif track_bias == "外前有利":
        if waku >= 5 and real_style in ["逃げ", "先行"]:
            tb_adj = 10.0
            tb_comment = f" ➔ 【バイアス絶好】{waku}枠×外前展開。馬場のきれいな外目から気持ちよく先行可能。"
        elif waku >= 5 and real_style == "差し":
            tb_adj = 4.0
            tb_comment = f" ➔ 【バイアス良好】外目を通れるポジショニングでアドバンテージ。"
        elif waku <= 2:
            tb_adj = -5.0
            tb_comment = f" ➔ 【バイアス逆風】内枠のため荒れた内ラチ沿いに閉じ込められる懸念。"

    elif track_bias == "大外一気・外全振り":
        if waku in [7, 8] and real_style in ["差し", "追込"]:
            tb_adj = 12.0
            tb_comment = f" ➔ 【バイアス絶好】{waku}枠×外全振り馬場。馬場のいい大外から一気に突き抜ける大チャンス。"
        elif waku in [5, 6] and real_style in ["差し", "追込"]:
            tb_adj = 8.0
            tb_comment = f" ➔ 【バイアス良好】外目進出で外全振りバイアスの恩恵享受。"
        elif waku <= 2 and real_style in ["逃げ", "先行"]:
            tb_adj = -10.0
            tb_comment = f" ➔ 【バイアス大逆風】最内枠×前行き。痛んだ内目通過で完全目標にされる展開。"

    elif track_bias in ["超前残り・逃げ天国", "前残り強"]:
        if real_style == "逃チャット画面に長大なコードを直接一括出力すると、文字数制限や重複検知システムにより出力エラーが発生してしまいます。
