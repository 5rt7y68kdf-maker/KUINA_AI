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
# 3. 高速インデックスロード ＆ コース統計インデックス
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_course_stats_index():
    waku_files = glob.glob("./*枠番*.csv") + glob.glob("./data/*枠番*.csv") + glob.glob("/workspace/knowledge/*枠番*.csv")
    kyaku_files = glob.glob("./*脚質*.csv") + glob.glob("./data/*脚質*.csv") + glob.glob("/workspace/knowledge/*脚質*.csv")

    stats_map = {}

    waku_df = None
    for f in set(waku_files):
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                waku_df = pd.read_csv(f, encoding=enc, on_bad_lines="skip")
                break
            except Exception:
                pass
        if waku_df is not None:
            break

    kyaku_df = None
    for f in set(kyaku_files):
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                kyaku_df = pd.read_csv(f, encoding=enc, on_bad_lines="skip")
                break
            except Exception:
                pass
        if kyaku_df is not None:
            break

    if waku_df is not None and "場所･距離" in waku_df.columns:
        for _, row in waku_df.iterrows():
            loc_dist = str(row.get("場所･距離", "")).strip()
            if not loc_dist or loc_dist == "nan":
                continue
            r_cnt = int(row.get("ﾚｰｽ数", 1)) if str(row.get("ﾚｰｽ数", "")).isdigit() else 1
            if loc_dist not in stats_map:
                stats_map[loc_dist] = {"total_races": 0, "waku_sum": {w: 0.0 for w in range(1, 9)}, "kyaku_sum": {"逃げ": 0.0, "先行": 0.0, "差し": 0.0, "追込": 0.0}}

            stats_map[loc_dist]["total_races"] += r_cnt
            for w_idx in range(1, 9):
                col_name = f"{w_idx}枠" if f"{w_idx}枠" in waku_df.columns else f"（{w_idx}枠）"
                if col_name in row and str(row[col_name]).replace(".", "", 1).isdigit():
                    val = float(row[col_name])
                    stats_map[loc_dist]["waku_sum"][w_idx] += val * r_cnt

    if kyaku_df is not None and "場所･距離" in kyaku_df.columns:
        for _, row in kyaku_df.iterrows():
            loc_dist = str(row.get("場所･距離", "")).strip()
            if not loc_dist or loc_dist == "nan":
                continue
            r_cnt = int(row.get("ﾚｰｽ数", 1)) if str(row.get("ﾚｰｽ数", "")).isdigit() else 1
            if loc_dist not in stats_map:
                stats_map[loc_dist] = {"total_races": 0, "waku_sum": {w: 0.0 for w in range(1, 9)}, "kyaku_sum": {"逃げ": 0.0, "先行": 0.0, "差し": 0.0, "追込": 0.0}}

            for k in ["逃げ", "先行", "差し", "追込"]:
                if k in row and str(row[k]).replace(".", "", 1).isdigit():
                    val = float(row[k])
                    stats_map[loc_dist]["kyaku_sum"][k] += val * r_cnt

    final_stats = {}
    for loc_dist, sdata in stats_map.items():
        tot = max(sdata["total_races"], 1)
        final_stats[loc_dist] = {
            "waku": {w: round(sdata["waku_sum"][w] / tot, 1) for w in range(1, 9)},
            "kyakushitsu": {k: round(sdata["kyaku_sum"][k] / tot, 1) for k in ["逃げ", "先行", "差し", "追込"]},
        }

    return final_stats


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
                    "通過1": str(row.get("通過1", "")),
                    "馬場状態": str(row.get("馬場状態", "良")),
                    "着順": str(row.get("着順", "99")),
                    "上り3F順位": str(row.get("上り3F順位", "99")),
                    "PCI": str(row.get("PCI", "50.0")),
                    "RPCI": str(row.get("RPCI", row.get("レースPCI", "50.0"))),
                    "クラス": str(row.get("クラス", row.get("前走クラス", ""))),
                    "着差": str(row.get("着差", "0.5")),
                    "距離": str(row.get("距離", "1800")),
                    "トラック": str(row.get("トラック", row.get("芝ダ", "芝"))),
                })

    return horse_past_map


# ==============================================================================
# 4. 全10バイアス ＆ 精密PCI/RPCI連動 AI解析エンジン
# ==============================================================================

def evaluate_pci_rpci_precision(past_list, current_track_type, curr_dist_num, expected_pace):
    if not past_list:
        return 0.0, "過去走のPCI/RPCIデータなし（標準適性評価）。", []

    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)

    filtered_races = []
    for p in past_list:
        p_dist = parse_distance_num(p.get("距離", ""))
        p_track = str(p.get("トラック", ""))
        p_is_dirt = "ダ" in p_track or "ダート" in p_track

        if p_is_dirt == is_dirt:
            if p_dist > 0 and curr_dist_num > 0 and abs(p_dist - curr_dist_num) <= 300:
                filtered_races.append(p)

    target_races = filtered_races if filtered_races else past_list

    high_pace_good = []
    slow_pace_good = []

    for p in target_races:
        try:
            pci_val = float(p.get("PCI", 50.0))
        except Exception:
            pci_val = 50.0

        try:
            rpci_val = float(p.get("RPCI", pci_val))
        except Exception:
            rpci_val = pci_val

        try:
            rank_val = int(re.search(r"\d+", str(p.get("着順", "99"))).group())
        except Exception:
            rank_val = 99

        try:
            agari_rank = int(re.search(r"\d+", str(p.get("上り3F順位", "99"))).group())
        except Exception:
            agari_rank = 99

        if (rpci_val <= 48.0 or pci_val <= 48.0) and rank_val <= 3:
            high_pace_good.append((rpci_val, pci_val, rank_val))

        if (rpci_val >= 52.0 or pci_val >= 52.0) and (rank_val <= 3 or agari_rank <= 2):
            slow_pace_good.append((rpci_val, pci_val, rank_val, agari_rank))

    score_adj = 0.0
    comment = ""
    tags = []

    if expected_pace == "ハイ":
        if high_pace_good:
            best_rpci = min([x[0] for x in high_pace_good])
            score_adj += 5.0
            tags.append("⏱️ RPCIハイ戦強者")
            comment = f"同トラック・類似距離のハイペース（前傾ラップRPCI {best_rpci:.1f}）で好走実績あり。激しい流れでもバテずに伸びるタフな適性が合致！（+5.0pt）"
        else:
            score_adj -= 2.0
            comment = "過去のハイペース・前傾消耗戦実績は手薄。ペース激化時の粘りにやや懸念。"
    elif expected_pace == "スロー":
        if slow_pace_good:
            best_rpci = max([x[0] for x in slow_pace_good])
            score_adj += 5.0
            tags.append("⚡ RPCIキレ特化")
            comment = f"スローペース・後傾瞬発力戦（RPCI {best_rpci:.1f}）で最速級の上りを繰り出した実績あり。上がりの速いキレ勝負で一気に浮上！（+5.0pt）"
        else:
            score_adj -= 2.0
            comment = "スローペース・後傾キレ勝負での最高速勝負にやや懸念。"
    else:  # ミドルペース
        score_adj += 3.0
        tags.append("⏱️ RPCI万能型")
        comment = "平均ペース（ミドルテンポ）で崩れず走れるバランスの良いPCI/RPCI持続力特性。（+3.0pt）"

    return score_adj, comment, tags


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
    stats_index=None,
    sire="",
    dam_sire="",
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

    # 2. 馬場適性詳細評価
    bad_score_adj = 0.0
    bad_flag = "標準"
    bad_comment = ""

    wet_past_races = [
        p for p in past_list
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

    # 3. 枠番・配置基礎評価 ＆ 過去5年コース統計連動
    waku_score_adj = 0.0
    waku_comment = ""
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)

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

    stats_adj = 0.0
    stats_comment = ""
    curr_dist_num = parse_distance_num(current_race_dist_str)
    if stats_index:
        track_name = re.sub(r"\d+.*", "", current_race_cond).strip() if current_race_cond else ""
        tt_short = "ダ" if is_dirt else "芝"
        course_key = f"{track_name}・{tt_short}{curr_dist_num}m" if track_name and curr_dist_num else ""

        match_stats = stats_index.get(course_key)
        if not match_stats:
            for k, v in stats_index.items():
                if tt_short in k and str(curr_dist_num) in k:
                    match_stats = v
                    course_key = k
                    break

        if match_stats:
            w_rate = match_stats["waku"].get(waku, 12.5)
            k_rate = match_stats["kyakushitsu"].get(real_style, 25.0)

            stats_adj += (w_rate - 12.5) * 0.4
            stats_adj += (k_rate - 25.0) * 0.2

            stats_comment = f" ➔ 【過去5年コース統計】{course_key}の実測複勝率：{waku}枠({w_rate:.1f}%)・脚質[{real_style}]({k_rate:.1f}%)(補正:{stats_adj:+.1f}pt)。"

    # 4. 全10バイアス完全連動
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

    waku_full_comment = waku_comment + stats_comment + tb_comment

    # 5. 血統・コース適性評価エンジン
    blood_adj = 0.0
    blood_comment = ""

    dirt_sires = ["ヘニーヒューズ", "マジェスティックウォリアー", "シニスターミニスター", "ドレフォン", "パイロ", "ホッコータルマエ", "エスポワールシチー", "カリフォルニアクローム", "ヴァンゴッホ", "ロードカナロア"]
    turf_sires = ["ディープインパクト", "ロードカナロア", "ハーツクライ", "エピファネイア", "キズナ", "モーリス", "ドゥラメンテ", "ルーラーシップ", "サートゥルナーリア", "レイデオロ"]
    power_sires = ["キズナ", "ドレフォン", "パイロ", "オルフェーヴル", "ハービンジャー", "ゴールドシップ", "マジェスティックウォリアー"]

    if is_dirt:
        if any(s in sire for s in dirt_sires) or any(s in dam_sire for s in dirt_sires):
            blood_adj += 5.0
            blood_comment = f"父{sire}×母父{dam_sire}。ダート適性の非常に高い血統構成でコース条件にベストマッチ。"
        else:
            blood_comment = f"父{sire}×母父{dam_sire}の標準的ダート適性血統。"
    else:
        if any(s in sire for s in turf_sires) or any(s in dam_sire for s in turf_sires):
            blood_adj += 5.0
            blood_comment = f"父{sire}×母父{dam_sire}。芝コースでの瞬発力・スピード持続力に長けた好血統。"
        else:
            blood_comment = f"父{sire}×母父{dam_sire}のバランス型血統構成。コース条件への適応力は十分。"

    if is_wet_track and (any(s in sire for s in power_sires) or any(s in dam_sire for s in power_sires)):
        blood_adj += 3.0
        blood_comment += f" さらに{current_track_condition}馬場で急浮上するパワー血統要素を完備。（+3.0pt）"

    # 6. 精密PCI/RPCI適性評価
    pci_score_adj, pci_comment, pci_tags = evaluate_pci_rpci_precision(
        past_list, current_track_type, curr_dist_num, expected_pace
    )

    # 7. 距離適性・分析
    dist_flag = "適性距離"
    dist_comment = "前走と同等の距離設定推移。"

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

    total_score = round(70.0 + bad_score_adj + waku_score_adj + stats_adj + tb_adj + blood_adj + pci_score_adj, 1)

    return {
        "real_style": real_style,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
        "waku_comment": waku_full_comment,
        "blood_comment": blood_comment,
        "pci_comment": pci_comment,
        "pci_tags": pci_tags,
        "dist_flag": dist_flag,
        "dist_comment": dist_comment,
        "total_score": total_score,
    }


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

    phase_label = f"<- {phase} GOAL" if phase == "最終直線" else f"<- {phase} 方向"
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

    style_x_offsets = {
        "逃げ": (0.6, 2.4),
        "先行": (3.3, 5.4),
        "差し": (6.3, 8.4),
        "追込": (9.3, 11.4),
    }

    style_horses = {"逃げ": [], "先行": [], "差し": [], "追込": []}
    for h in processed_horses:
        style_horses.get(h["real_style"], style_horses["先行"]).append(h)

    for style, hlist in style_horses.items():
        n = len(hlist)
        if n == 0:
            continue
        xmin, xmax = style_x_offsets.get(style, (3.3, 5.4))
        width = xmax - xmin

        cols = math.ceil(math.sqrt(n)) if n > 4 else min(n, 2)
        rows = math.ceil(n / cols)

        dx = width / (cols + 1) if cols > 0 else width / 2
        dy = 2.4 / (rows + 1) if rows > 0 else 1.0

        for idx, horse in enumerate(hlist):
            c_idx = idx % cols
            r_idx = idx // cols

            x_pos = xmin + (c_idx + 1) * dx
            y_pos = 1.0 - (r_idx + 1) * dy

            if phase == "3・4コーナー":
                if style in ["差し", "追込"]:
                    x_pos -= 0.8
                if horse["waku"] in [7, 8]:
                    y_pos -= 0.4
            elif phase == "最終直線":
                score_rank = horse.get("rank", 5)
                if score_rank <= 3:
                    x_pos -= 1.2
                if "外" in track_bias and horse["waku"] >= 5:
                    y_pos -= 0.5

            bg_col, text_col = WAKU_COLOR_MAP.get(horse["waku"], ("#ffffff", "#000000"))

            circle = patches.Circle(
                (x_pos, y_pos), 0.35,
                facecolor=bg_col, edgecolor='#f8fafc', linewidth=1.8, zorder=4
            )
            ax.add_patch(circle)

            ax.text(
                x_pos, y_pos, str(horse["num"]),
                color=text_col, fontsize=11, fontweight='bold',
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
    stats_index = load_course_stats_index()

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

st.markdown(
    f"""
<div class="race-banner">
    <div class="race-banner-title">
        🔍 選択レース: {selected_date_str} 【 {clean_race_title} 】
    </div>
    <div class="race-banner-sub">
        出走頭数: <b>{len(current_race_horses)}頭 AI精密PCI/RPCI完全解析</b>
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

if track_bias == "🤖 AI自動判定（馬場・コース連動）":
    if track_condition in ["重", "不良"]:
        track_bias = "タフ・スタミナ消耗馬場"
    elif track_condition == "稍重" and "ダ" in current_track_type:
        track_bias = "超前残り・逃げ天国"
    else:
        track_bias = "内伸び・内前有利"

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
        stats_index=stats_index,
        sire=sire,
        dam_sire=dam_sire,
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
        "pci_comment": eval_res["pci_comment"],
        "pci_tags": eval_res["pci_tags"],
        "dist_flag": eval_res["dist_flag"],
        "dist_comment": eval_res["dist_comment"],
    })

ranked_horses = sorted(
    processed_horses, key=lambda x: x["total_score"], reverse=True
)

for rank_idx, h in enumerate(ranked_horses, start=1):
    h["rank"] = rank_idx

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
        for tag_str in horse.get("pci_tags", []):
            tags_html += f'<span style="background-color:#7c3aed; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{tag_str}</span>'

        if "距離短縮" in horse["dist_flag"]:
            tags_html += '<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離短縮</span>'

        if "道悪◎" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◎(好実績)</span>'
        elif "道悪◯" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#10b981; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◯</span>'

        sire_info = f"父: {horse['sire']} ｜ 母父: {horse['dam_sire']}" if horse['sire'] else ""

        card_code = f"""
        <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div style="flex: 1 1 200px; min-width: 180px;">
                <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 2px;">
                    枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}
                </div>
                <div style="font-size: 11px; color: #475569; margin-bottom: 4px; font-weight: 600;">
                    🧬 {sire_info}
                </div>
                <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                    想定脚質: <b>{horse['real_style']}</b>
                </div>
                <div>{tags_html}</div>
            </div>
            <div style="flex: 2 1 300px; min-width: 250px;">
                <div class="analysis-label">🚩 枠順・コース統計・展開配置評価</div>
                <div class="analysis-text">{horse["waku_comment"]}</div>
                <div class="analysis-label">⏱️ PCI/RPCI・展開適性評価</div>
                <div class="analysis-text">{horse["pci_comment"]}</div>
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
        fig1 = render_pace_map_graphic_phase(processed_horses, clean_race_title, current_track_type, track_bias, phase="向こう正面")
        st.pyplot(fig1, use_container_width=True)
        plt.close(fig1)

    with phase_tab2:
        fig2 = render_pace_map_graphic_phase(processed_horses, clean_race_title, current_track_type, track_bias, phase="3・4コーナー")
        st.pyplot(fig2, use_container_width=True)
        plt.close(fig2)

    with phase_tab3:
        fig3 = render_pace_map_graphic_phase(processed_horses, clean_race_title, current_track_type, track_bias, phase="最終直線")
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
        a_num = str(tanana['num']) if tanana else ""
        r_nums = [str(h['num']) for h in renka]

        a_and_r = ([a_num] if a_num else []) + r_nums
        a_and_r_str = ", ".join(a_and_r)

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title"><span>🥇 馬連 (本命軸)</span><span style="color:#059669;">本線</span></div>
                    <div class="ticket-combo">軸: {h_num} ➔ 相手: {t_num}{', ' + a_and_r_str if a_and_r_str else ''}</div>
                </div>
                <div class="ticket-card">
                    <div class="ticket-title"><span>🎯 3連複 (1頭軸流し)</span><span style="color:#2563eb;">主力</span></div>
                    <div class="ticket-combo">軸: {h_num} ➔ 相手: {t_num}, {a_and_r_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_t2:
            st.markdown(
                f"""
                <div class="ticket-card">
                    <div class="ticket-title"><span>🔥 馬単 (1着固定)</span><span style="color:#dc2626;">高配当</span></div>
                    <div class="ticket-combo">1着: {h_num} ➔ 2着: {t_num}, {a_and_r_str}</div>
                </div>
                <div class="ticket-card">
                    <div class="ticket-title"><span>🚀 3連単 (フォーメーション)</span><span style="color:#7c3aed;">一撃</span></div>
                    <div class="ticket-combo">1着: {h_num}, {t_num} ➔ 2着: {h_num}, {t_num}, {a_num} ➔ 3着: {h_num}, {t_num}, {a_and_r_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
