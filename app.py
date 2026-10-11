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
    if any(k in s for k in ["G1", "GⅠ", "GI"]): return 9
    if any(k in s for k in ["G2", "GⅡ", "GII"]): return 8
    if any(k in s for k in ["G3", "GⅢ", "GIII", "重賞"]): return 7
    if any(k in s for k in ["オープン", "OP", "リステッド", "L"]): return 6
    if "3勝" in s or "1600万" in s: return 5
    if "2勝" in s or "1000万" in s: return 4
    if "1勝" in s or "500万" in s: return 3
    if "未勝利" in s: return 2
    if "新馬" in s: return 1
    return 4


def parse_distance_num(dist_str):
    if not dist_str: return 0
    m = re.search(r"\d{4}", str(dist_str))
    if m: return int(m.group())
    m2 = re.search(r"\d{3,4}", str(dist_str))
    if m2: return int(m2.group())
    return 0


def get_jra_waku(umaban, total_horses):
    if total_horses <= 8: return umaban
    capacities = [1 for _ in range(8)]
    extras = total_horses - 8
    for i in range(7, -1, -1):
        if extras > 0:
            capacities[i] += 1
            extras -= 1
    curr = 0
    for waku_idx, cap in enumerate(capacities, start=1):
        if curr < umaban <= curr + cap: return waku_idx
        curr += cap
    return 8


WAKU_COLOR_MAP = {
    1: ("#ffffff", "#000000"), 2: ("#1e293b", "#ffffff"), 3: ("#ef4444", "#ffffff"), 4: ("#3b82f6", "#ffffff"),
    5: ("#eab308", "#000000"), 6: ("#22c55e", "#ffffff"), 7: ("#f97316", "#ffffff"), 8: ("#ec4899", "#ffffff"),
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
            except Exception: pass

        if df is None or df.empty or len(df.columns) < 11:
            continue

        races_by_key = {}
        for row in df.values:
            if len(row) < 11: continue

            col0_val = str(row[0]).strip().replace("-", "") if pd.notna(row[0]) else ""
            if not col0_val.isdigit(): continue

            if len(col0_val) == 6: date_str = f"20{col0_val[:2]}-{col0_val[2:4]}-{col0_val[4:6]}"
            elif len(col0_val) == 8: date_str = f"{col0_val[:4]}-{col0_val[4:6]}-{col0_val[6:8]}"
            else: continue

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

            if not horse_name: continue

            prize_money = float(str(row[27]).strip()) if len(row) > 27 and pd.notna(row[27]) and str(row[27]).strip().isdigit() else 0.0
            umaban_num = int(umaban_str) if umaban_str.isdigit() else 1

            key = (date_str, track, rnum)
            if key not in races_by_key:
                races_by_key[key] = {
                    "date": date_str, "track": track, "rnum": rnum,
                    "cond": cond, "track_type": track_type, "dist": dist, "horses": [],
                }

            races_by_key[key]["horses"].append({
                "馬番": umaban_num, "馬名": horse_name, "騎手": jockey,
                "父": sire, "母父": dam_sire, "prize_money": prize_money,
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
        date_races_map[d_str] = sorted(date_races_map[d_str], key=lambda x: (x["track"], x["rnum"]))

    return date_races_map


@st.cache_data(ttl=3600, show_spinner=False)
def load_course_stats_index():
    raw_files = (
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("./data/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv") + glob.glob("/workspace/knowledge/*.CSV")
    )

    waku_file = next((f for f in set(raw_files) if "枠番" in os.path.basename(f)), None)
    kyaku_file = next((f for f in set(raw_files) if "脚質" in os.path.basename(f) and "枠番" not in os.path.basename(f)), None)

    course_stats = {}

    if waku_file:
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df_w = pd.read_csv(waku_file, encoding=enc)
                if "場所･距離" in df_w.columns:
                    for c_name, g in df_w.groupby("場所･距離"):
                        w_dict = {}
                        tot_r = g["ﾚｰｽ数"].sum() if "ﾚｰｽ数" in g.columns else 1
                        for w_i in range(1, 9):
                            col = f"{['一','１','2','3','4','5','6','7','8'][w_i]}枠" if w_i == 1 else f"{w_i}枠"
                            col_full = next((c for c in g.columns if str(w_i) in c or (w_i==1 and "１" in c)), None)
                            if col_full and col_full in g.columns:
                                w_dict[w_i] = round(g[col_full].astype(float).mean(), 1)
                            else:
                                w_dict[w_i] = 12.5
                        course_stats[c_name] = {"waku": w_dict, "total_races": tot_r, "kyakushitsu": {}}
                break
            except Exception: pass

    if kyaku_file:
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df_k = pd.read_csv(kyaku_file, encoding=enc)
                if "場所･距離" in df_k.columns:
                    for c_name, g in df_k.groupby("場所･距離"):
                        k_dict = {}
                        for style in ["逃げ", "先行", "差し", "追込"]:
                            if style in g.columns:
                                k_dict[style] = round(g[style].astype(float).mean(), 1)
                            else:
                                k_dict[style] = 15.0
                        if c_name not in course_stats:
                            course_stats[c_name] = {"waku": {i: 12.5 for i in range(1, 9)}, "total_races": 0, "kyakushitsu": k_dict}
                        else:
                            course_stats[c_name]["kyakushitsu"] = k_dict
                break
            except Exception: pass

    return course_stats


@st.cache_data(ttl=3600, show_spinner=False)
def load_past_races_index():
    json_candidates = ["past_index.json", "./data/past_index.json", "/workspace/knowledge/past_index.json"]
    for jpath in json_candidates:
        if os.path.exists(jpath):
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data: return data
            except Exception: pass

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
            except Exception: pass

        if df is None or df.empty or "馬名" not in df.columns:
            continue

        for row in df.to_dict("records"):
            h_name = str(row.get("馬名", "")).strip()
            if not h_name: continue

            if h_name not in horse_past_map:
                horse_past_map[h_name] = []

            if len(horse_past_map[h_name]) < 5:
                horse_past_map[h_name].append({
                    "通過1": str(row.get("通過1", "")), "馬場状態": str(row.get("馬場状態", "良")),
                    "着順": str(row.get("着順", "99")), "距離": str(row.get("距離", "1800")),
                })

    return horse_past_map


# ==============================================================================
# 4. 全10バイアス ＆ 過去5年コース統計 ＆ 血統 AI解析エンジン
# ==============================================================================

def analyze_horse_with_index(
    horse_name, umaban, waku, total_horses, current_race_cond, current_race_dist_str,
    current_track_type, past_index, current_track_condition, weather, track_bias, expected_pace,
    track_location="東京", course_stats={}, sire="", dam_sire=""
):
    past_list = past_index.get(horse_name, [])

    # 1. 脚質判定
    real_style = "先行"
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
    else:
        styles = ["逃げ", "先行", "差し", "追込"]
        real_style = styles[(umaban * 3 + len(horse_name)) % 4]

    # 2. 馬場適性評価
    bad_score_adj = 0.0
    bad_flag = "標準"
    bad_comment = ""
    wet_past_races = [p for p in past_list if p.get("馬場状態") in ["稍重", "重", "不良"]]
    is_wet_track = current_track_condition in ["稍重", "重", "不良"]

    if is_wet_track:
        if wet_past_races:
            best_wet_finish = min([
                int(re.search(r"\d+", p.get("着順", "99")).group())
                for p in wet_past_races if re.search(r"\d+", p.get("着順", "99"))
            ] or (99,))

            if best_wet_finish <= 3:
                bad_score_adj += 8.0
                bad_flag = "道悪◎(好実績)"
                bad_comment = f"過去の道悪馬場で最高{best_wet_finish}着の好実績あり！タフな馬場適性は非常に高く、今回の{current_track_condition}馬場は絶好の勝機。"
            elif best_wet_finish <= 5:
                bad_score_adj += 4.0
                bad_flag = "道悪◯"
                bad_comment = f"過去の道悪馬場で掲示板（{best_wet_finish}着）獲得実績あり。崩れにくいパワーと重馬場適性を備えています。"
            else:
                bad_score_adj -= 5.0
                bad_flag = "道悪不安"
                bad_comment = f"過去の道悪馬場では凡走傾向（最高{best_wet_finish}着）。馬場悪化によるパフォーマンス低下に注意が必要。"
        else:
            if real_style in ["逃げ", "先行"]:
                bad_score_adj += 5.0
                bad_flag = "道悪注意(前行き)"
                bad_comment = f"道悪の過去走実績は少ないですが、{current_track_condition}馬場×前行き脚質（{real_style}）により前残り有利展開の恩恵を期待。"
            elif real_style == "追込":
                bad_score_adj -= 5.0
                bad_flag = "道悪懸念(後方)"
                bad_comment = f"{current_track_condition}馬場で後方からの追込脚質。水を含んだタフな馬場で前との差が縮まりにくく大幅割引。"
            else:
                bad_comment = f"{current_track_condition}馬場での走破実績はなく未知数。血統・パワー要求度の高まりに対応できるかが鍵。"
    else:
        bad_comment = "良馬場開催につき、スピード・瞬発力（上り性能）をフルに発揮できる好条件です。"

    # 3. 枠番配置 ＆ コース過去5年統計評価
    waku_score_adj = 0.0
    waku_comment = ""
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)

    if waku in (1, 2):
        if is_dirt:
            waku_score_adj -= 2.0
            waku_comment = f"最内{waku}枠。ダート戦のため被せられた際の砂被り（キックバック）リスクに注意が必要。"
        else:
            waku_score_adj += 3.0
            waku_comment = f"絶好の{waku}枠（内枠）。最短距離をロスなく立ち回れる経済コースの恩恵大。"
    elif waku in (3, 4, 5, 6):
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

    # コース統計連動
    dist_num = parse_distance_num(current_race_dist_str)
    tt_short = "ダ" if is_dirt else "芝"
    c_key = f"{track_location}・{tt_short}{dist_num}m"

    c_info = course_stats.get(c_key, {})
    stat_waku_pct = c_info.get("waku", {}).get(waku, 12.5)
    stat_kyaku_pct = c_info.get("kyakushitsu", {}).get(real_style, 20.0)

    stat_waku_adj = (stat_waku_pct - 12.5) * 0.4
    stat_kyaku_adj = (stat_kyaku_pct - 25.0) * 0.3
    stat_total_adj = round(stat_waku_adj + stat_kyaku_adj, 1)

    stat_comment = f" ➔ 【過去5年コース統計】{c_key}の実測複勝率：{waku}枠({stat_waku_pct}%)・脚質[{real_style}]({stat_kyaku_pct}%)(補正:{stat_total_adj:+.1f}pt)。"
    waku_full_comment = waku_comment + stat_comment

    # 4. 全10バイアスエンジン
    tb_adj = 0.0
    tb_comment = ""

    if track_bias == "フラット":
        tb_adj = 0.0
        tb_comment = " ➔ 【バイアス平穏】特定の枠・脚質への偏りがないフラット馬場。実力通りの力勝勝負が期待できます。"
    elif track_bias == "超イン伸び・最内ラチ有利":
        if waku in (1, 2) and real_style in ["逃げ", "先行"]: tb_adj, tb_comment = 12.0, f" ➔ 【バイアス絶好】{waku}枠の最内ラチ沿い×前行き脚質。最内を通れる最高の展開です。"
        elif waku in (1, 2): tb_adj, tb_comment = 6.0, f" ➔ 【バイアス良好】{waku}枠の最内枠。内目のグリーンベルトを通れる好位置。"
        elif waku in (3, 4) and real_style in ["逃げ", "先行"]: tb_adj, tb_comment = 4.0, f" ➔ 【バイアスやや良好】すんなり内に入れて先行できれば強みを発揮。"
        elif waku in (7, 8): tb_adj, tb_comment = -8.0, f" ➔ 【バイアス大逆風】{waku}枠の外枠によりインコースに入れず大幅不利。"
    elif track_bias in ["内伸び・内前有利", "内前有利"]:
        if waku <= 4 and real_style in ["逃げ", "先行"]: tb_adj, tb_comment = 10.0, f" ➔ 【バイアス絶好】{waku}枠×内前有利。内ラチ沿いを先手奪取できる絶好配置。"
        elif waku <= 4 and real_style == "差し": tb_adj, tb_comment = 4.0, f" ➔ 【バイアス良好】内枠からロスなく差してこれる有利ポジション。"
        elif waku >= 5 and real_style == "追込": tb_adj, tb_comment = -6.0, f" ➔ 【バイアス逆風】外枠×後方追込。内前有利な馬場に泣く厳しい展開。"
        elif waku >= 7: tb_adj, tb_comment = -4.0, f" ➔ 【バイアスやや逆風】外枠につきコーナーでの内入れ苦戦。"
    elif track_bias in ["外伸び・外差し有利", "外差し有利"]:
        if waku >= 5 and real_style in ["差し", "追込"]: tb_adj, tb_comment = 10.0, f" ➔ 【バイアス絶好】{waku}枠×外差し脚質。荒れた内を避けて一気に突き抜ける絶好機会。"
        elif waku >= 5 and real_style == "先行": tb_adj, tb_comment = 4.0, f" ➔ 【バイアス良好】外から被せるように前目をつけて馬場の良い部分を通過可能。"
        elif waku <= 2 and real_style in ["逃げ", "先行"]: tb_adj, tb_comment = -6.0, f" ➔ 【バイアス逆風】最内枠×逃げ・先行。痛んだ内目を通らされる懸念。"
    elif track_bias == "外前有利":
        if waku >= 5 and real_style in ["逃げ", "先行"]: tb_adj, tb_comment = 10.0, f" ➔ 【バイアス絶好】{waku}枠（外枠）×前行き脚質。揉まれず綺麗な外目を通って先行できる最高の展開。"
        elif waku <= 4 and real_style in ["逃げ", "先行"]: tb_adj, tb_comment = 4.0, f" ➔ 【バイアス普通】内前目の配置ですが、外から被せられる展開に注意。"
        elif real_style in ["差し", "追込"]: tb_adj, tb_comment = -6.0, f" ➔ 【バイアス逆風】前目の馬が綺麗な外目を通って止まらないバイアスにつき厳しい。"
    elif track_bias == "大外一気・外全振り":
        if waku in (7, 8) and real_style in ["差し", "追込"]: tb_adj, tb_comment = 12.0, f" ➔ 【バイアス絶好】{waku}枠×外全振り馬場。馬場のいい大外から一気に突き抜ける大チャンス。"
        elif waku in (5, 6) and real_style in ["差し", "追込"]: tb_adj, tb_comment = 8.0, f" ➔ 【バイアス良好】外目進出で外全振りバイアスの恩恵享受。"
        elif waku <= 2 and real_style in ["逃げ", "先行"]: tb_adj, tb_comment = -10.0, f" ➔ 【バイアス大逆風】最内枠×前行き。痛んだ内目通過で完全目標にされる展開。"
    elif track_bias in ["超前残り・逃げ天国", "前残り強"]:
        if real_style == "逃げ": tb_adj, tb_comment = 12.0, " ➔ 【バイアス絶好】逃げ天国馬場につき、マイペース逃げからの押し切り濃厚。"
        elif real_style == "先行": tb_adj, tb_comment = 7.0, " ➔ 【バイアス良好】絶好の好位前目で粘り込みを図れる展開。"
        elif real_style == "追込": tb_adj, tb_comment = -10.0, " ➔ 【バイアス大逆風】後方追込には絶望的な超前残りバイアス。"
        elif real_style == "差し": tb_adj, tb_comment = -5.0, " ➔ 【バイアスやや逆風】前が止まらないため差し届かずのリスク。"
    elif track_bias in ["前崩れ・差し必至"]:
        if real_style == "追込": tb_adj, tb_comment = 12.0, " ➔ 【バイアス絶好】前崩れ確実の展開につき、直線大外一気での末脚爆発期待。"
        elif real_style == "差し": tb_adj, tb_comment = 8.0, " ➔ 【バイアス良好】好位差し展開でバテた先行馬を一網打尽。"
        elif real_style == "逃げ": tb_adj, tb_comment = -10.0, " ➔ 【バイアス大逆風】ハイペース巻き込まれで直線完全失速のリスク。"
        elif real_style == "先行": tb_adj, tb_comment = -5.0, " ➔ 【バイアスやや逆風】早い仕掛けで脚が上がる危険性。"
    elif track_bias == "超高速馬場（持ち時計重視）":
        if real_style in ["逃げ", "先行"]: tb_adj, tb_comment = 8.0, " ➔ 【バイアス良好】超高速馬場×スピード持続力。前々から止まらないレース質に適合。"
        elif waku <= 4: tb_adj, tb_comment = 4.0, " ➔ 【バイアスやや良好】高速馬場のインコースロスなし追走メリット。"
        elif real_style == "追込": tb_adj, tb_comment = -5.0, " ➔ 【バイアス逆風】高速時計決着で後方からの追い出し遅れ懸念。"
    elif track_bias == "タフ・スタミナ消耗馬場":
        if real_style in ["差し", "追込"]: tb_adj, tb_comment = 8.0, " ➔ 【バイアス良好】スタミナ消耗戦につき、底力と末脚を発揮できる展開。"
        elif bad_flag in ["道悪◎(好実績)", "道悪◯"]: tb_adj, tb_comment = 6.0, " ➔ 【バイアス良好】タフな馬場での過去実績が実を結ぶ消耗戦歓迎タイプ。"
        elif real_style == "逃げ": tb_adj, tb_comment = -6.0, " ➔ 【バイアス逆風】タフ馬場での逃げは直線最後で目標にされてバテるリスク。"

    waku_full_comment = waku_full_comment + tb_comment

    # 5. 血統適性評価
    blood_adj = 0.0
    blood_comment = ""
    sire_str = sire or "不明"
    dam_sire_str = dam_sire or "不明"

    dirt_sires = ["ヘニーヒューズ", "シニスターミニスター", "マジェスティックウォリアー", "パイロ", "サウスヴィグラス", "ドレフォン", "エスポワールシチー", "カリフォルニアクローム", "ヴァンゴッホ", "オメガパフューム"]
    turf_sires = ["ディープインパクト", "ハーツクライ", "ロードカナロア", "エピファネイア", "キズナ", "モーリス", "ドゥラメンテ", "キタサンブラック", "サートゥルナーリア", "ロジャーバローズ"]

    if is_dirt:
        if any(ds in sire_str or ds in dam_sire_str for ds in dirt_sires):
            blood_adj += 4.0
            blood_comment = f"父{sire_str}×母父{dam_sire_str}。ダート適性の非常に高い血統構成でコース条件にベストマッチ。"
        else:
            blood_comment = f"父{sire_str}×母父{dam_sire_str}。コース適性は標準的。"
    else:
        if any(ts in sire_str or ts in dam_sire_str for ts in turf_sires):
            blood_adj += 4.0
            blood_comment = f"父{sire_str}×母父{dam_sire_str}。芝適性と決め手に優れた王道血統構成。"
        else:
            blood_comment = f"父{sire_str}×母父{dam_sire_str}のバランス型血統構成。コース条件への適応力は十分。"

    if is_wet_track and any(ps in sire_str or ps in dam_sire_str for ps in ["キズナ", "オルフェーヴル", "ルーラーシップ", "ドレフォン", "ゴールドシップ"]):
        blood_adj += 3.0
        blood_comment += f" さらに道悪パワー要求度の高い{current_track_condition}馬場は血統的に大歓迎！"

    # 6. 距離推移
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

    total_score = round(70.0 + bad_score_adj + waku_score_adj + stat_total_adj + tb_adj + blood_adj, 1)

    return {
        "real_style": real_style,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
        "waku_comment": waku_full_comment,
        "blood_comment": blood_comment,
        "dist_flag": dist_flag,
        "dist_comment": dist_comment,
        "total_score": total_score,
    }


def render_phase_graphic(processed_horses, race_title, track_type, track_bias, phase_type="backstretch"):
    fig, ax = plt.subplots(figsize=(12, 4.6), dpi=150)

    is_dirt = "ダ" in str(track_type) or "ダート" in str(track_type)
    bg_dark = '#381c0d' if is_dirt else '#064e3b'
    track_dark = '#542d17' if is_dirt else '#0f766e'
    lane_color = '#78350f' if is_dirt else '#14b8a6'

    fig.patch.set_facecolor(bg_dark)
    ax.set_facecolor(track_dark)

    ax.axhline(0, color=lane_color, linewidth=1.5, linestyle='--')
    ax.axhline(1.5, color=lane_color, linewidth=1, linestyle=':')
    ax.axhline(-1.5, color=lane_color, linewidth=1, linestyle=':')

    if phase_type == "backstretch":
        phase_label = "PHASE 1: BACKSTRETCH (EARLY - MID)"
    elif phase_type == "corner":
        phase_label = "PHASE 2: 3-4 CORNER (MID - TURN)"
    else:
        phase_label = "PHASE 3: HOME STRETCH (FINAL SPRINT)"

    ax.annotate(
        f"<- FINISH / GOAL | {phase_label}",
        xy=(0.5, 2.2),
        xytext=(0.8, 2.2),
        arrowprops=dict(facecolor='#fef08a', edgecolor='#fef08a', width=2, headwidth=8),
        fontsize=11,
        fontweight='bold',
        color='#fef08a',
        ha='left'
    )

    zones = [
        ("FRONT (NIGE)", 0.3, 2.7, '#f87171'),
        ("PACE (SENKO)", 3.0, 5.7, '#fbbf24'),
        ("MID (SASHI)", 6.0, 8.7, '#34d399'),
        ("BACK (OIKOMI)", 9.0, 11.7, '#818cf8'),
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
    elif "外前" in track_bias:
        hot_rects.append((3.0, 11.7, 0.2, 1.8))
    elif "大外一気" in track_bias:
        hot_rects.append((9.0, 11.7, -1.8, 1.8))
    elif any(k in track_bias for k in ["前残り", "逃げ天国"]):
        hot_rects.append((0.3, 2.7, -1.8, 1.8))
    elif any(k in track_bias for k in ["前崩れ", "差し必至"]):
        hot_rects.append((6.0, 11.7, -1.8, 1.8))

    for xmin, xmax, ymin, ymax in hot_rects:
        hot_box = patches.FancyBboxPatch(
            (xmin, ymin), xmax - xmin, ymax - ymin,
            boxstyle="round,pad=0.1,rounding_size=0.2",
            facecolor='#fbbf24', edgecolor='#fef08a', linewidth=2.0, alpha=0.3, zorder=2
        )
        ax.add_patch(hot_box)

    horses_by_style = {"逃げ": [], "先行": [], "差し": [], "追込": []}
    for h in processed_horses:
        style = h.get("real_style", "先行")
        if style in horses_by_style:
            horses_by_style[style].append(h)
        else:
            horses_by_style["先行"].append(h)

    style_bounds = {
        "逃げ": (0.4, 2.6),
        "先行": (3.1, 5.6),
        "差し": (6.1, 8.6),
        "追込": (9.1, 11.6),
    }

    if phase_type == "backstretch":
        for style, bounds in style_bounds.items():
            h_list = horses_by_style[style]
            if not h_list: continue
            xmin, xmax = bounds
            n = len(h_list)
            cols = 2 if n <= 6 else 3
            rows = (n + cols - 1) // cols
            dx = (xmax - xmin) / (cols + 1)
            dy = 3.2 / (rows + 1)
            r = 0.35 if n <= 6 else 0.28
            font_sz = 11 if n <= 6 else 9

            for i, horse in enumerate(h_list):
                c_idx = i % cols
                r_idx = i // cols
                x_pos = xmin + (c_idx + 1) * dx
                y_pos = 1.6 - (r_idx + 1) * dy

                bg_col, text_col = WAKU_COLOR_MAP.get(horse["waku"], ("#ffffff", "#000000"))
                circle = patches.Circle((x_pos, y_pos), r, facecolor=bg_col, edgecolor='#f8fafc', linewidth=1.8, zorder=4)
                ax.add_patch(circle)
                ax.text(x_pos, y_pos, str(horse["num"]), color=text_col, fontsize=font_sz, fontweight='bold', ha='center', va='center', zorder=5)

    elif phase_type == "corner":
        for style, bounds in style_bounds.items():
            h_list = horses_by_style[style]
            if not h_list: continue
            xmin, xmax = bounds
            n = len(h_list)
            cols = 2 if n <= 6 else 3
            rows = (n + cols - 1) // cols
            dx = (xmax - xmin) / (cols + 1)
            dy = 3.2 / (rows + 1)
            r = 0.32 if n <= 6 else 0.28
            font_sz = 10 if n <= 6 else 9

            for i, horse in enumerate(h_list):
                c_idx = i % cols
                r_idx = i // cols
                x_pos = xmin + (c_idx + 1) * dx
                y_pos = 1.6 - (r_idx + 1) * dy

                if style in ["差し", "追込"] and any(b in track_bias for b in ["外差し", "外伸び", "前崩れ", "大外一気"]):
                    x_pos -= 1.0
                    y_pos = -1.2 + (i % 3) * 0.8
                elif style in ["逃げ", "先行"] and any(b in track_bias for b in ["内伸び", "超イン伸び", "逃げ天国"]):
                    x_pos -= 0.3
                    y_pos = 1.2 - (i % 3) * 0.6

                bg_col, text_col = WAKU_COLOR_MAP.get(horse["waku"], ("#ffffff", "#000000"))
                circle = patches.Circle((x_pos, y_pos), r, facecolor=bg_col, edgecolor='#f8fafc', linewidth=1.8, zorder=4)
                ax.add_patch(circle)
                ax.text(x_pos, y_pos, str(horse["num"]), color=text_col, fontsize=font_sz, fontweight='bold', ha='center', va='center', zorder=5)

    else:
        sorted_horses = sorted(processed_horses, key=lambda x: x.get("total_score", 70.0), reverse=True)
        r = 0.32
        font_sz = 10

        for rank_idx, horse in enumerate(sorted_horses, start=1):
            if rank_idx == 1: x_pos, y_pos = 0.8, 0.5
            elif rank_idx == 2: x_pos, y_pos = 1.6, -0.5
            elif rank_idx == 3: x_pos, y_pos = 2.4, 1.2
            elif rank_idx <= 6:
                x_pos = 3.2 + (rank_idx - 4) * 1.0
                y_pos = 1.0 - (rank_idx % 3) * 0.9
            elif rank_idx <= 12:
                x_pos = 6.2 + ((rank_idx - 7) // 2) * 1.1
                y_pos = 1.2 - (rank_idx % 3) * 1.0
            else:
                x_pos = 9.5 + ((rank_idx - 13) // 2) * 1.1
                y_pos = 1.0 - (rank_idx % 3) * 1.0

            x_pos = min(11.4, max(0.6, x_pos))
            bg_col, text_col = WAKU_COLOR_MAP.get(horse["waku"], ("#ffffff", "#000000"))
            circle = patches.Circle((x_pos, y_pos), r, facecolor=bg_col, edgecolor='#f8fafc', linewidth=1.8, zorder=4)
            ax.add_patch(circle)
            ax.text(x_pos, y_pos, str(horse["num"]), color=text_col, fontsize=font_sz, fontweight='bold', ha='center', va='center', zorder=5)

    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(-2.5, 2.7)
    ax.axis('off')
    plt.tight_layout()
    return fig


# ==============================================================================
# 5. メイン画面 UI構築
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
    course_stats = load_course_stats_index()

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
current_track_location = selected_race_obj.get("track", "東京")

st.markdown(
    f"""
<div class="race-banner">
    <div class="race-banner-title">
        🔍 選択レース: {selected_date_str} 【 {clean_race_title} 】
    </div>
    <div class="race-banner-sub">
        出走頭数: <b>{len(current_race_horses)}頭 AI完全解析</b>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

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
        track_condition,
        weather,
        track_bias,
        expected_pace,
        current_track_location,
        course_stats,
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
# 6. タブ別表示
# ==============================================================================

tab_rank, tab_pace, tab_tickets = st.tabs([
    "🏆 AI分析スコア",
    "🏇 展開・推定隊列グラフィック",
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
        if "距離短縮" in horse["dist_flag"]:
            tags_html += '<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離短縮</span>'

        if "道悪◎" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◎(好実績)</span>'
        elif "道悪◯" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#10b981; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◯</span>'
        elif "道悪不安" in horse["bad_flag"] or "懸念" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#dc2626; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪割り引き</span>'

        blood_info = f"父: {horse['sire']} ｜ 母父: {horse['dam_sire']}" if horse['sire'] else "血統データ準備中"

        card_code = f"""
        <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div style="flex: 1 1 200px; min-width: 180px;">
                <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 2px;">
                    枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}
                </div>
                <div style="font-size: 11px; color: #475569; margin-bottom: 4px;">
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
                <div class="analysis-label">🌧️ 馬場適性・過去実績評価</div>
                <div class="analysis-text">{horse["bad_comment"]}</div>
                <div class="analysis-label">🧬 血統・コース適性評価</div>
                <div class="analysis-text">{horse["blood_comment"]}</div>
                <div class="analysis-label">📏 距離推移・展開分析</div>
                <div class="analysis-text">{horse["dist_comment"]}</div>
            </div>
            <div style="flex: 0 0 80px; text-align: right;">
                <div class="score-badge">{horse["total_score"]} <span style="font-size:13px;">pt</span></div>
            </div>
        </div>
        """
        cards_html_list.append(card_code)

    st.markdown("\n".join(cards_html_list), unsafe_allow_html=True)


with tab_pace:
    st.subheader(f"🏇 【{clean_race_title}】 展開・推定隊列グラフィック (3フェーズ詳細分析)")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "📍 ① 向こう正面 (スタート〜中盤)",
        "🌀 ② 3・4コーナー (勝負所・進出)",
        "🏁 ③ 最終直線 (ゴール前・決め手)"
    ])

    with sub_tab1:
        st.markdown("##### 📍 向こう正面（スタート直後〜中盤ポジション）")
        fig1 = render_phase_graphic(processed_horses, clean_race_title, current_track_type, track_bias, "backstretch")
        st.pyplot(fig1, width='stretch')
        plt.close(fig1)

    with sub_tab2:
        st.markdown("##### 🌀 3・4コーナー（勝負所でのポジション押し上げ・外回し想定）")
        fig2 = render_phase_graphic(processed_horses, clean_race_title, current_track_type, track_bias, "corner")
        st.pyplot(fig2, width='stretch')
        plt.close(fig2)

    with sub_tab3:
        st.markdown("##### 🏁 最終直線（AIスコア＆バイアス順 予想ゴール前位置取り）")
        fig3 = render_phase_graphic(processed_horses, clean_race_title, current_track_type, track_bias, "straight")
        st.pyplot(fig3, width='stretch')
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
        a_num = str(tanana['num']) if tanana else ""
        r_nums = [str(h['num']) for h in renka]

        a_and_r = ([a_num] if a_num else []) + r_nums
        a_and_r_str = ", ".join(a_and_r)

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            umaren_combos = f"{h_num} - {t_num}" + (f", {a_num}" if a_num else "") + (f", {', '.join(r_nums)}" if r_nums else "")
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🤝 馬連 (1頭軸流し)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span>
                    </div>
                    <div>軸: <b>{h_num}番 ({honmei['name']})</b> ➔ 相手: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {umaren_combos}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            umatan_combos = f"{h_num} ➔ {t_num}" + (f", {a_num}" if a_num else "") + (f", {', '.join(r_nums)}" if r_nums else "")
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🎯 馬単 (1着固定)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span>
                    </div>
                    <div>1着: <b>{h_num}番 ({honmei['name']})</b> ➔ 2着: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {umatan_combos}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            wide_combos = f"{h_num} - {t_num}" + (f", {a_num}" if a_num else "")
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>💎 ワイド (上位人気・単穴BOX)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 3 点</span>
                    </div>
                    <div>BOX: <b>{h_num}番, {t_num}番</b> {f', {a_num}番' if a_num else ''}</div>
                    <div class="ticket-combo">買い目: {wide_combos}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_t2:
            sanrenpuku_combos = f"{h_num} - {t_num} - {a_and_r_str}"
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🏆 3連複 (軸1頭ながし)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)*(len(a_and_r)+1)//2} 点</span>
                    </div>
                    <div>軸: <b>{h_num}番</b> ➔ 相手: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {sanrenpuku_combos}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            sanrentan_combos = f"{h_num} ➔ {t_num}{f', {a_num}' if a_num else ''} ➔ {t_num}, {a_and_r_str}"
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🔥 3連単 (フォーメーション)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨高配当狙い</span>
                    </div>
                    <div>1着: <b>{h_num}番</b> ➔ 2着: {t_num}{f', {a_num}' if a_num else ''} ➔ 3着: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {sanrentan_combos}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
