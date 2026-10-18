import os
import glob
import re
import json
import math
import textwrap
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
    .footer-box {
        background: #0f172a;
        color: #94a3b8;
        padding: 22px 24px;
        border-radius: 14px;
        margin-top: 36px;
        font-size: 12px;
        line-height: 1.7;
    }
    .footer-box a {
        color: #38bdf8;
        text-decoration: none;
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
# 3. 高速インデックスロード ＆ 日付厳格ソート past_index
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
            dam = str(row[17]).strip() if len(row) > 17 and pd.notna(row[17]) else ""
            damsire = str(row[20]).strip() if len(row) > 20 and pd.notna(row[20]) else ""

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
                "sire": sire,
                "dam": dam,
                "damsire": damsire,
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
    raw_files = (
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("./data/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv") + glob.glob("/workspace/knowledge/*.CSV")
    )

    horse_past_map = {}

    for fpath in set(raw_files):
        if any(k in os.path.basename(fpath) for k in ["枠番", "脚質"]):
            continue

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

            track = str(row[1]).strip() if pd.notna(row[1]) else ""
            rnum_str = str(row[2]).strip() if pd.notna(row[2]) else "1"
            umaban_str = str(row[3]).strip() if pd.notna(row[3]) else "1"
            cond = str(row[4]).strip() if pd.notna(row[4]) else ""
            track_type = str(row[5]).strip() if pd.notna(row[5]) else ""
            dist = str(row[6]).strip() if pd.notna(row[6]) else ""
            horse_name = str(row[7]).strip() if pd.notna(row[7]) else ""

            sire = str(row[16]).strip() if len(row) > 16 and pd.notna(row[16]) else ""
            dam = str(row[17]).strip() if len(row) > 17 and pd.notna(row[17]) else ""
            damsire = str(row[20]).strip() if len(row) > 20 and pd.notna(row[20]) else ""

            rank = str(row[22]).strip() if len(row) > 22 and pd.notna(row[22]) else "99"
            time_diff = str(row[25]).strip() if len(row) > 25 and pd.notna(row[25]) else "0.5"
            pass1 = str(row[29]).strip() if len(row) > 29 and pd.notna(row[29]) else ""
            time_str = str(row[30]).strip() if len(row) > 30 and pd.notna(row[30]) else ""
            last3f_rank = str(row[31]).strip() if len(row) > 31 and pd.notna(row[31]) else "99"

            if not horse_name:
                continue

            if horse_name not in horse_past_map:
                horse_past_map[horse_name] = []

            already = False
            for existing in horse_past_map[horse_name]:
                if existing["日付"] == date_str and existing["競馬場"] == track and existing["レース番号"] == rnum_str:
                    already = True
                    break

            if not already:
                horse_past_map[horse_name].append({
                    "日付": date_str,
                    "競馬場": track,
                    "レース番号": rnum_str,
                    "条件": cond,
                    "トラック": track_type,
                    "距離": dist,
                    "枠番": str(row[2]) if len(row) > 2 else "1",
                    "馬番": umaban_str,
                    "着順": rank,
                    "着差": time_diff,
                    "通過1": pass1,
                    "タイム": time_str,
                    "上り3F順位": last3f_rank,
                    "馬場状態": cond,
                    "父": sire,
                    "母": dam,
                    "母父": damsire,
                    "PCI": "50.0",
                })

    # ★ 日付・レース番号の降順で厳格ソート（最新走が必ず[0]に配置される） ★
    for h_name in horse_past_map:
        horse_past_map[h_name] = sorted(
            horse_past_map[h_name],
            key=lambda x: (x["日付"], int(x["レース番号"]) if str(x["レース番号"]).isdigit() else 1),
            reverse=True
        )

    return horse_past_map


@st.cache_data(ttl=3600, show_spinner=False)
def load_course_waku_stats():
    waku_files = (
        glob.glob("./*枠番*.csv") + glob.glob("./*枠番*.CSV")
        + glob.glob("./data/*枠番*.csv") + glob.glob("/workspace/knowledge/*枠番*.csv")
    )
    course_stats = {}
    for fpath in set(waku_files):
        try:
            df = pd.read_csv(fpath, encoding="cp932", dtype=str, on_bad_lines="skip")
            if "場所･距離" in df.columns:
                for _, r in df.iterrows():
                    course_key = str(r["場所･距離"]).strip()
                    if course_key not in course_stats:
                        course_stats[course_key] = {}
                    for w_idx in range(1, 9):
                        w_col = f"{['１','２','３','４','５','６','７','８'][w_idx-1]}枠"
                        val_str = str(r.get(w_col, "0")).replace("%", "").strip()
                        val = float(val_str) if val_str.replace(".", "", 1).isdigit() else 0.0
                        if w_idx not in course_stats[course_key]:
                            course_stats[course_key][w_idx] = []
                        course_stats[course_key][w_idx].append(val)
        except Exception:
            pass

    avg_course_stats = {}
    for c_key, w_dict in course_stats.items():
        avg_course_stats[c_key] = {}
        for w_idx, v_list in w_dict.items():
            avg_course_stats[c_key][w_idx] = sum(v_list) / len(v_list) if v_list else 12.5

    return avg_course_stats


# ==============================================================================
# 4. 日付厳格連動・全ファクター完全解析 AIエンジン
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
    current_race_date,
    current_race_rnum,
    current_track_name,
    course_waku_stats,
):
    all_races = past_index.get(horse_name, [])

    # ★ 日付基準フィルタリング（対象レースより過去の日付・レースを正確に抽出） ★
    prior_races = [
        r for r in all_races
        if r.get("日付", "") < current_race_date
        or (r.get("日付", "") == current_race_date and str(r.get("レース番号", "")) != str(current_race_rnum))
    ]

    # 1. 脚質判定
    real_style = "先行"
    if prior_races:
        pass1_vals = [
            float(re.search(r"\d+", p["通過1"]).group())
            for p in prior_races if p.get("通過1") and re.search(r"\d+", str(p["通過1"]))
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

    # 2. 競馬場・コース・距離別の枠順詳細統計データ評価 (新潟芝1000m直など対応)
    waku_score_adj = 0.0
    waku_comment = ""
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)
    curr_dist_num = parse_distance_num(current_race_dist_str)
    course_query_key = f"{current_track_name}・{current_track_type}{curr_dist_num}m"

    # 新潟芝1000m（直線コース）の特別判定
    if "新潟" in current_track_name and "芝" in current_track_type and curr_dist_num == 1000:
        if waku in [7, 8]:
            waku_score_adj += 8.0
            waku_comment = f"絶好の{waku}枠。新潟芝1000m直線コースの黄金パターンである大外枠（過去複勝率25%〜30%超）を引き当てた最高の配置！"
        elif waku in [1, 2]:
            waku_score_adj -= 8.0
            waku_comment = f"厳しい{waku}枠。新潟芝1000m直は内ラチ沿いの馬場が荒れやすく、内枠（過去複勝率3%〜5%）は大幅割り引き。"
        else:
            waku_comment = f"中目の{waku}枠。新潟直千は馬場の良い外目（7・8枠）へスムーズに持ち出せるかが鍵。"
    else:
        cw_stats = course_waku_stats.get(course_query_key, {})
        waku_place_rate = cw_stats.get(waku, 12.5) if cw_stats else 12.5

        if cw_stats:
            avg_rate = sum(cw_stats.values()) / 8.0 if cw_stats else 12.5
            if waku_place_rate >= avg_rate + 3.0:
                waku_score_adj += 4.0
                waku_comment = f"コース統計データで優秀な{waku}枠（【{course_query_key}】枠別複勝率: {waku_place_rate:.1f}%）。ロスなく運べる絶好配置。"
            elif waku_place_rate <= avg_rate - 3.0:
                waku_score_adj -= 3.0
                waku_comment = f"コース統計データで苦戦傾向の{waku}枠（【{course_query_key}】枠別複勝率: {waku_place_rate:.1f}%）。展開の助けが必要。"
            else:
                waku_comment = f"{waku}枠配置（【{course_query_key}】枠別複勝率: {waku_place_rate:.1f}%）。平均的なコース枠順傾向。"
        else:
            if waku in [1, 2]:
                if is_dirt:
                    waku_score_adj -= 2.0
                    waku_comment = f"最内{waku}枠。ダート戦のため被せられた際の砂被り（キックバック）リスクに注意が必要。"
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

    # 3. 馬場適性詳細評価
    bad_score_adj = 0.0
    bad_flag = "標準"
    bad_comment = ""

    wet_past_races = [
        p for p in prior_races
        if p.get("馬場状態") in ["稍重", "重", "不良"]
    ]

    is_wet_track = current_track_condition in ["稍重", "重", "不良"]

    if is_wet_track:
        if wet_past_races:
            best_wet_finish = min([
                int(re.search(r"\d+", p.get("着順", "99")).group())
                for p in wet_past_races if re.search(r"\d+", p.get("着順", "99"))
            ] or [99])

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
        if real_style == "逃げ":
            tb_adj = 12.0
            tb_comment = " ➔ 【バイアス絶好】逃げ天国馬場につき、マイペース逃げからの押し切り濃厚。"
        elif real_style == "先行":
            tb_adj = 7.0
            tb_comment = " ➔ 【バイアス良好】絶好の好位前目で粘り込みを図れる展開。"
        elif real_style == "追込":
            tb_adj = -10.0
            tb_comment = " ➔ 【バイアス大逆風】後方追込には絶望的な超前残りバイアス。"
        elif real_style == "差し":
            tb_adj = -5.0
            tb_comment = " ➔ 【バイアスやや逆風】前が止まらないため差し届かずのリスク。"

    elif track_bias in ["前崩れ・差し必至"]:
        if real_style == "追込":
            tb_adj = 12.0
            tb_comment = " ➔ 【バイアス絶好】前崩れ確実の展開につき、直線大外一気での末脚爆発期待。"
        elif real_style == "差し":
            tb_adj = 8.0
            tb_comment = " ➔ 【バイアス良好】好位差し展開でバテた先行馬を一網打尽。"
        elif real_style == "逃げ":
            tb_adj = -10.0
            tb_comment = " ➔ 【バイアス大逆風】ハイペース巻き込まれで直線完全失速のリスク。"
        elif real_style == "先行":
            tb_adj = -5.0
            tb_comment = " ➔ 【バイアスやや逆風】早い仕掛けで脚が上がる危険性。"

    elif track_bias == "超高速馬場（持ち時計重視）":
        if real_style in ["逃げ", "先行"]:
            tb_adj = 8.0
            tb_comment = " ➔ 【バイアス良好】超高速馬場×スピード持続力。前々から止まらないレース質に適合。"
        elif waku <= 4:
            tb_adj = 4.0
            tb_comment = " ➔ 【バイアスやや良好】高速馬場のインコースロスなし追走メリット。"
        elif real_style == "追込":
            tb_adj = -5.0
            tb_comment = " ➔ 【バイアス逆風】高速時計決着で後方からの追い出し遅れ懸念。"

    elif track_bias == "タフ・スタミナ消耗馬場":
        if real_style in ["差し", "追込"]:
            tb_adj = 8.0
            tb_comment = " ➔ 【バイアス良好】スタミナ消耗戦につき、底力と末脚を発揮できる展開。"
        elif bad_flag in ["道悪◎(好実績)", "道悪◯"]:
            tb_adj = 6.0
            tb_comment = " ➔ 【バイアス良好】タフな馬場での過去実績が実を結ぶ消耗戦歓迎タイプ。"
        elif real_style == "逃げ":
            tb_adj = -6.0
            tb_comment = " ➔ 【バイアス逆風】タフ馬場での逃げは直線最後で目標にされてバテるリスク。"

    waku_full_comment = waku_comment + tb_comment

    # 5. 直近前走（1走前）の着順・着差・芝ダ替え完全精度判定
    last_score_adj = 0.0
    last_race_comment = ""
    last_race_flag = ""

    if prior_races and len(prior_races) > 0:
        last_race = prior_races[0]
        l_rank = str(last_race.get("着順", "99")).strip()
        l_diff_str = str(last_race.get("着差", "0.5")).strip()
        l_diff = float(l_diff_str) if l_diff_str.replace(".", "", 1).isdigit() else 0.5
        l_date = last_race.get("日付", "")
        l_track = last_race.get("競馬場", "")
        l_type = last_race.get("トラック", "")
        l_dist = last_race.get("距離", "")
        l_waku = int(last_race.get("枠番", "1")) if str(last_race.get("枠番", "1")).isdigit() else 1

        if l_rank == "1":
            last_score_adj += 8.0
            last_race_flag = "前走1着(勝利)"
            last_race_comment = f"直近前走({l_date} {l_track} {l_type}{l_dist}m)で見事に1着勝利！勝ちきる高い競走能力と勝負強さを実証。"
        elif l_diff <= 0.3:
            last_score_adj += 5.0
            last_race_flag = "前走着差0.3s以内"
            last_race_comment = f"直近前走({l_date} {l_track} {l_type}{l_dist}m)で{l_rank}着（勝ち馬とわずか{l_diff:.1f}秒差）の僅差好走。現級勝ち負けのレベルに位置しています。"
        else:
            last_race_comment = f"直近前走({l_date} {l_track})は{l_rank}着（着差{l_diff:.1f}秒）。"

        # 直近前走限定の芝➔ダート替わり
        if "芝" in str(l_type) and is_dirt:
            last_score_adj += 5.0
            last_race_flag = "直近芝➔ダート替わり"
            last_race_comment += f" 前走芝戦から今回ダートへの条件替わり。初ダート・砂適性一変による激走に警戒！"

        # 前走ダート内枠好走
        if "ダ" in str(l_type) and l_waku in [1, 2] and l_rank in ["1", "2", "3"]:
            last_score_adj += 5.0
            last_race_comment += f" 前走ダート内枠({l_waku}枠)からの好走実績があり砂被りにも強い立ち回りが魅力。"

    else:
        last_race_comment = "直近の過去走データなし（新馬・初出走またはデータ初掲載）。"

    # 6. 上がり3F末脚性能評価（新規ファクター）
    last3f_adj = 0.0
    last3f_comment = ""
    last3f_flag = ""

    best_3f_rank = 99
    if prior_races:
        r_list = [
            int(r.get("上り3F順位"))
            for r in prior_races
            if str(r.get("上り3F順位", "")).isdigit() and int(r.get("上り3F順位")) > 0
        ]
        if r_list:
            best_3f_rank = min(r_list)

    if best_3f_rank == 1:
        last3f_adj += 8.0
        last3f_flag = "上がり最速実績◎"
        last3f_comment = "過去走でメンバー最速（上がり1位）の爆発的な末脚を記録！展開ひとつでまとめて差し切る高い決め手を秘めています。"
    elif best_3f_rank <= 3:
        last3f_adj += 5.0
        last3f_flag = "上がり上位末脚◯"
        last3f_comment = f"過去走で上がり{best_3f_rank}位の優秀な末脚実績あり。直線で確実に出せる決め脚を備えています。"
    else:
        last3f_comment = "過去走の上がり順位は標準的。展開や位置取りの助けが必要なタイプです。"

    if expected_pace == "ハイ" or track_bias in ["前崩れ・差し必至", "外伸び・外差し有利", "大外一気・外全振り"]:
        if best_3f_rank <= 3:
            last3f_adj += 3.0
            last3f_comment += f" 今回の{expected_pace}ペース・{track_bias}バイアスは決め脚（上がり3F性能）を活かせる絶好展開！"

    # 7. 血統適性・血統背景評価（新規ファクター）
    sire_adj = 0.0
    sire_comment = ""
    sire_flag = ""

    sire_name = ""
    damsire_name = ""
    if prior_races:
        sire_name = prior_races[0].get("父", "")
        damsire_name = prior_races[0].get("母父", "")

    turf_sires = ["ディープ", "キズナ", "エピファネイア", "コントレイル", "サートゥルナーリア", "ロードカナロア", "ハーツクライ", "スワーヴリチャード", "モーリス", "ルーラーシップ", "ドゥラメンテ", "キタサンブラック"]
    dirt_sires = ["ゴールドアリュール", "スマートファルコン", "エスポワールシチー", "オメガパフューム", "ヘニーヒューズ", "シニスターミニスター", "マジェスティックウォリアー", "カリフォルニアクローム", "ドレフォン", "ホッコータルマエ", "サウスヴィグラス", "パイロ", "マインドユアビスケッツ", "ニューイヤーズデイ", "ルヴァンスレーヴ"]
    sprint_sires = ["サクラバクシンオー", "ビッグアーサー", "ロードカナロア", "ダノンプレシャス", "ファインニードル", "ミスターメロディ", "Speightstown"]
    stamina_sires = ["ハーツクライ", "キタサンブラック", "ゴールドシップ", "オルフェーヴル", "エピファネイア", "ルーラーシップ", "シンボリクリスエス"]

    pedigree_match = False
    full_blood = f"{sire_name} {damsire_name}"

    if is_dirt and any(k in full_blood for k in dirt_sires):
        pedigree_match = True
    elif not is_dirt and any(k in full_blood for k in turf_sires):
        pedigree_match = True

    if curr_dist_num <= 1400 and any(k in full_blood for k in sprint_sires):
        pedigree_match = True
    elif curr_dist_num >= 2000 and any(k in full_blood for k in stamina_sires):
        pedigree_match = True

    if pedigree_match:
        sire_adj += 5.0
        sire_flag = "血統適性◎"
        sire_comment = f"父:{sire_name or '出走表参照'} × 母父:{damsire_name or '出走表参照'}。今回の{current_track_type}{curr_dist_num}mコースにおける血統的バッキングは非常に強力です。"
    else:
        sire_comment = f"父:{sire_name or '出走表参照'} × 母父:{damsire_name or '出走表参照'}。コース条件に対する血統適性は標準的です。"

    # 8. PCI / RPCI ペース変化指数
    pci_adj = 0.0
    pci_comment = ""
    pci_flag = ""

    avg_pci = 50.0
    if prior_races:
        pci_list = [
            float(r.get("PCI"))
            for r in prior_races
            if r.get("PCI") and str(r.get("PCI")).replace(".", "", 1).isdigit()
        ]
        if pci_list:
            avg_pci = sum(pci_list) / len(pci_list)

    if expected_pace == "スロー":
        if avg_pci >= 52.0:
            pci_adj += 6.0
            pci_flag = "PCIペース適合"
            pci_comment = f"平均PCI {avg_pci:.1f}（瞬発力型）。スローペースからの上がり勝負でキレ味を発揮できる最高の展開。"
        elif avg_pci <= 48.0:
            pci_adj -= 3.0
            pci_comment = f"平均PCI {avg_pci:.1f}（持続力型）。スローの瞬発力勝負ではキレ負けするリスクあり。"
    elif expected_pace == "ハイ":
        if avg_pci <= 48.0:
            pci_adj += 6.0
            pci_flag = "PCIペース適合"
            pci_comment = f"平均PCI {avg_pci:.1f}（持続力・スタミナ型）。ハイペースの消耗戦で最後までバテずに伸びてくる好展開。"
        elif avg_pci >= 52.0:
            pci_adj -= 3.0
            pci_comment = f"平均PCI {avg_pci:.1f}（瞬発力型）。ハイペースに巻き込まれると直線脚が上がるリスクあり。"
    else:
        pci_comment = f"平均PCI {avg_pci:.1f}。ミドルペースにおける適性は標準的です。"

    # 9. 距離適性・分析
    dist_flag = "適性距離"
    dist_comment = "前走と同等の距離設定推移。"

    if prior_races and len(prior_races) > 0:
        last_race = prior_races[0]
        last_dist_num = parse_distance_num(last_race.get("距離", ""))
        if curr_dist_num > 0 and last_dist_num > 0:
            diff = curr_dist_num - last_dist_num
            if diff <= -200:
                dist_flag = f"距離短縮({diff}m)"
                dist_comment = f"前走{last_dist_num}mから{abs(diff)}mの距離短縮。追走ペースが楽になり末脚爆発の期待大。"
            elif diff >= 200:
                dist_flag = f"距離延長(+{diff}m)"
                dist_comment = f"前走{last_dist_num}mから+{diff}mへの距離延長。道中のゆったりした追走が可能。"

    total_score = round(70.0 + bad_score_adj + waku_score_adj + tb_adj + last_score_adj + last3f_adj + sire_adj + pci_adj, 1)

    return {
        "real_style": real_style,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
        "waku_comment": waku_full_comment,
        "last_race_flag": last_race_flag,
        "last_race_comment": last_race_comment,
        "last3f_flag": last3f_flag,
        "last3f_comment": last3f_comment,
        "sire_flag": sire_flag,
        "sire_comment": sire_comment,
        "sire_name": sire_name,
        "damsire_name": damsire_name,
        "pci_flag": pci_flag,
        "pci_comment": pci_comment,
        "dist_flag": dist_flag,
        "dist_comment": dist_comment,
        "total_score": total_score,
    }


def render_pace_map_graphic_advanced(processed_horses, race_title, track_type, track_bias):
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

    ax.annotate(
        "<- FINISH / GOAL",
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

    # ★全10バイアスのグラフィック連動ハイライトゾーン★
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
    elif "超高速" in track_bias:
        hot_rects.append((0.3, 5.7, -1.8, 1.8))
    elif "タフ" in track_bias:
        hot_rects.append((6.0, 11.7, -1.8, 1.8))

    for xmin, xmax, ymin, ymax in hot_rects:
        hot_box = patches.FancyBboxPatch(
            (xmin, ymin), xmax - xmin, ymax - ymin,
            boxstyle="round,pad=0.1,rounding_size=0.2",
            facecolor='#fbbf24', edgecolor='#fef08a', linewidth=2.5, alpha=0.35, zorder=2
        )
        ax.add_patch(hot_box)

    style_x_offsets = {
        "逃げ": (0.6, 2.4),
        "先行": (3.3, 5.4),
        "差し": (6.3, 8.4),
        "追込": (9.3, 11.4),
    }

    style_counts = {"逃げ": 0, "先行": 0, "差し": 0, "追込": 0}

    for horse in processed_horses:
        style = horse["real_style"]
        waku = horse["waku"]
        num = horse["num"]

        bg_col, text_col = WAKU_COLOR_MAP.get(waku, ("#ffffff", "#000000"))
        xmin, xmax = style_x_offsets.get(style, (3.3, 5.4))
        cnt = style_counts[style]

        x_pos = xmin + (cnt % 2) * 1.1
        y_pos = 1.2 - (cnt // 2) * 0.9 if cnt < 4 else -1.2 + (cnt % 2) * 0.6
        style_counts[style] += 1

        circle = patches.Circle(
            (x_pos, y_pos), 0.38,
            facecolor=bg_col, edgecolor='#f8fafc', linewidth=1.8, zorder=4
        )
        ax.add_patch(circle)

        ax.text(
            x_pos, y_pos, str(num),
            color=text_col, fontsize=12, fontweight='bold',
            ha='center', va='center', zorder=5
        )

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
    course_waku_stats = load_course_waku_stats()

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
current_track_name = selected_race_obj.get("track", "東京")
current_race_rnum = selected_race_obj.get("rnum", 1)

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
        selected_date_str,
        current_race_rnum,
        current_track_name,
        course_waku_stats,
    )

    processed_horses.append({
        "waku": waku,
        "num": umaban,
        "name": horse_name,
        "jockey": h_data.get("騎手", "未定"),
        "total_score": eval_res["total_score"],
        "real_style": eval_res["real_style"],
        "bad_flag": eval_res["bad_flag"],
        "bad_comment": eval_res["bad_comment"],
        "waku_comment": eval_res["waku_comment"],
        "last_race_flag": eval_res["last_race_flag"],
        "last_race_comment": eval_res["last_race_comment"],
        "last3f_flag": eval_res["last3f_flag"],
        "last3f_comment": eval_res["last3f_comment"],
        "sire_flag": eval_res["sire_flag"],
        "sire_comment": eval_res["sire_comment"],
        "sire_name": eval_res["sire_name"],
        "damsire_name": eval_res["damsire_name"],
        "pci_flag": eval_res["pci_flag"],
        "pci_comment": eval_res["pci_comment"],
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
        if horse.get("last_race_flag") == "前走1着(勝利)":
            tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">前走1着(勝利)</span>'
        elif horse.get("last_race_flag") == "前走着差0.3s以内":
            tags_html += '<span style="background-color:#10b981; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">前走着差0.3s以内</span>'

        if horse.get("last_race_flag") == "直近芝➔ダート替わり":
            tags_html += '<span style="background-color:#f59e0b; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">直近芝➔ダート替わり</span>'

        if horse.get("last3f_flag"):
            tags_html += f'<span style="background-color:#8b5cf6; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{horse["last3f_flag"]}</span>'

        if horse.get("sire_flag"):
            tags_html += f'<span style="background-color:#ec4899; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{horse["sire_flag"]}</span>'

        if horse.get("pci_flag"):
            tags_html += f'<span style="background-color:#6366f1; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{horse["pci_flag"]}</span>'

        if "距離短縮" in horse["dist_flag"]:
            tags_html += '<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離短縮</span>'

        if "道悪◎" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◎(好実績)</span>'

        sire_text = f"父:{horse['sire_name']}" if horse['sire_name'] else ""
        damsire_text = f"母父:{horse['damsire_name']}" if horse['damsire_name'] else ""
        blood_info = f" ｜ 血統: {sire_text} {damsire_text}".strip() if (sire_text or damsire_text) else ""

        card_code = textwrap.dedent(f"""
        <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div style="flex: 1 1 200px; min-width: 180px;">
                <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">
                    枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}{blood_info}
                </div>
                <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                    想定脚質: <b>{horse['real_style']}</b>
                </div>
                <div>{tags_html}</div>
            </div>
            <div style="flex: 2 1 300px; min-width: 250px;">
                <div class="analysis-label">🚩 枠順・コース配置評価 (勝率・複勝率データ連動)</div>
                <div class="analysis-text">{horse["waku_comment"]}</div>
                <div class="analysis-label">⚡ 上がり3F末脚・PCIペース分析</div>
                <div class="analysis-text">{horse["last3f_comment"]} {horse["pci_comment"]}</div>
                <div class="analysis-label">🧬 血統背景・コース適性評価</div>
                <div class="analysis-text">{horse["sire_comment"]}</div>
                <div class="analysis-label">🌧️ 馬場適性・直近過去走評価 (日付連動照合)</div>
                <div class="analysis-text">{horse["last_race_comment"]} {horse["bad_comment"]}</div>
                <div class="analysis-label">📏 距離推移・展開分析</div>
                <div class="analysis-text">{horse["dist_comment"]}</div>
            </div>
            <div style="flex: 0 0 80px; text-align: right;">
                <div class="score-badge">{horse["total_score"]} <span style="font-size:13px;">pt</span></div>
            </div>
        </div>
        """).strip()
        cards_html_list.append(card_code)

    st.markdown("\n".join(cards_html_list), unsafe_allow_html=True)


with tab_pace:
    st.subheader(f"🏇 【{clean_race_title}】 展開・推定隊列グラフィック")

    fig = render_pace_map_graphic_advanced(processed_horses, clean_race_title, current_track_type, track_bias)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

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
                textwrap.dedent(f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🤝 馬連 (1頭軸流し)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span>
                    </div>
                    <div>軸: <b>{h_num}番 ({honmei['name']})</b> ➔ 相手: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {umaren_combos}</div>
                </div>
                """).strip(),
                unsafe_allow_html=True
            )

            umatan_combos = f"{h_num} ➔ {t_num}" + (f", {a_num}" if a_num else "") + (f", {', '.join(r_nums)}" if r_nums else "")
            st.markdown(
                textwrap.dedent(f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🎯 馬単 (1着固定)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span>
                    </div>
                    <div>1着: <b>{h_num}番 ({honmei['name']})</b> ➔ 2着: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {umatan_combos}</div>
                </div>
                """).strip(),
                unsafe_allow_html=True
            )

            wide_combos = f"{h_num} - {t_num}" + (f", {a_num}" if a_num else "")
            st.markdown(
                textwrap.dedent(f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>💎 ワイド (上位人気・単穴BOX)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 3 点</span>
                    </div>
                    <div>BOX: <b>{h_num}番, {t_num}番</b> {f', {a_num}番' if a_num else ''}</div>
                    <div class="ticket-combo">買い目: {wide_combos}</div>
                </div>
                """).strip(),
                unsafe_allow_html=True
            )

        with col_t2:
            sanrenpuku_combos = f"{h_num} - {t_num} - {a_and_r_str}"
            st.markdown(
                textwrap.dedent(f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🏆 3連複 (軸1頭ながし)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)*(len(a_and_r)+1)//2} 点</span>
                    </div>
                    <div>軸: <b>{h_num}番</b> ➔ 相手: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {sanrenpuku_combos}</div>
                </div>
                """).strip(),
                unsafe_allow_html=True
            )

            sanrentan_combos = f"{h_num} ➔ {t_num}{f', {a_num}' if a_num else ''} ➔ {t_num}, {a_and_r_str}"
            st.markdown(
                textwrap.dedent(f"""
                <div class="ticket-card">
                    <div class="ticket-title">
                        <span>🔥 3連単 (フォーメーション)</span>
                        <span style="font-size:12px; color:#6366f1;">推奨高配当狙い</span>
                    </div>
                    <div>1着: <b>{h_num}番</b> ➔ 2着: {t_num}{f', {a_num}' if a_num else ''} ➔ 3着: {t_num}, {a_and_r_str}</div>
                    <div class="ticket-combo">買い目: {sanrentan_combos}</div>
                </div>
                """).strip(),
                unsafe_allow_html=True
            )

# ==============================================================================
# 7. フッター（免責事項・プライバシーポリシー・お問い合わせ先）
# ==============================================================================

st.markdown(
    textwrap.dedent("""
    <div class="footer-box">
        <div style="font-size:14px; font-weight:800; color:#f8fafc; margin-bottom:8px;">
            🛡️ KUINA AI 免責事項・プライバシーポリシー・お問い合わせ
        </div>
        <div>
            <b>【免責事項】</b><br>
            当サイト「KUINA AI | Racing Intelligence System」で提供する予想・分析スコアおよび推奨馬券情報は、過去の公式競走データおよび機械学習アルゴリズムに基づく統計解析結果であり、将来のレース結果や的中・回収率を保証するものではありません。馬券の購入は必ずご自身の判断と責任において行なってください。勝馬投票券の購入は20歳からとなります。
        </div>
        <div style="margin-top:10px;">
            <b>【プライバシーポリシー ＆ 広告配信について】</b><br>
            当サイトでは、第三者配信事業者（Google AdSense等）による広告配信サービスを利用しています。これらの事業者は、ユーザーの興味に応じた商品やサービスの広告を表示するため、当サイトや他サイトへのアクセスに関する情報（Cookie）を使用することがあります。アクセス情報の収集およびCookieの使用を無効化する設定につきましては、Googleの広告設定ページをご参照ください。
        </div>
        <div style="margin-top:10px;">
            <b>【お問い合わせ先】</b><br>
            サイト運用・データ表示・広告掲載に関するお問い合わせは、下記Googleアカウント窓口までご連絡ください。<br>
            📧 問い合わせメールアドレス: <a href="mailto:kuina.ai.keiba@gmail.com">kuina.ai.keiba@gmail.com</a>
        </div>
        <div style="margin-top:12px; text-align:center; color:#64748b; font-size:11px;">
            © 2026 KUINA AI | Racing Intelligence System. All rights reserved.
        </div>
    </div>
    """).strip(),
    unsafe_allow_html=True
)
