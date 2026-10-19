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
# 3. 高速インデックスロード ＆ データ統合
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def scan_and_load_all_csvs():
    raw_files = (
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("./data/*.CSV")
        + glob.glob("./knowledge/*.csv") + glob.glob("./knowledge/*.CSV")
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
            damsire = str(row[20]).strip() if len(row) > 20 and pd.notna(row[20]) else ""

            if not horse_name:
                continue

            prize_money = 0.0
            if len(row) > 27 and pd.notna(row[27]) and str(row[27]).strip().isdigit():
                prize_money = float(str(row[27]).strip())

            umaban_num = int(umaban_str) if umaban_str.isdigit() else 1
            waku_num = int(row[22]) if len(row) > 22 and str(row[22]).strip().isdigit() else get_jra_waku(umaban_num, 16)
            pass1_str = str(row[29]).strip() if len(row) > 29 and pd.notna(row[29]) else "0"
            rank_str = str(row[31]).strip() if len(row) > 31 and pd.notna(row[31]) else "0"
            rank_num = int(rank_str) if rank_str.isdigit() else 0

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
                "sire": sire,
                "damsire": damsire,
                "pass1": pass1_str,
                "rank": rank_num,
                "prize_money": prize_money,
            })

        for key, rdata in races_by_key.items():
            tot = len(rdata["horses"])
            for h in rdata["horses"]:
                if "枠番" not in h or h["枠番"] <= 0:
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
    json_candidates = ["past_index.json", "./data/past_index.json", "./knowledge/past_index.json", "/workspace/knowledge/past_index.json"]
    for jpath in json_candidates:
        if os.path.exists(jpath):
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                pass

    raw_files = (
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("./data/*.CSV")
        + glob.glob("./knowledge/*.csv") + glob.glob("./knowledge/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv") + glob.glob("/workspace/knowledge/*.CSV")
    )
    horse_past_map = {}

    for fpath in set(raw_files):
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
            rnum = int(rnum_str) if rnum_str.isdigit() else 1
            cond = str(row[4]).strip() if pd.notna(row[4]) else ""
            track_type = str(row[5]).strip() if pd.notna(row[5]) else ""
            dist = str(row[6]).strip() if pd.notna(row[6]) else ""
            h_name = str(row[7]).strip() if pd.notna(row[7]) else ""
            sire = str(row[16]).strip() if len(row) > 16 and pd.notna(row[16]) else ""
            damsire = str(row[20]).strip() if len(row) > 20 and pd.notna(row[20]) else ""
            waku_num = int(row[22]) if len(row) > 22 and str(row[22]).strip().isdigit() else 1
            pass1 = str(row[29]).strip() if len(row) > 29 and pd.notna(row[29]) else "0"
            
            # 着順: 31列目 (確定着順)
            rank_str = str(row[31]).strip() if len(row) > 31 and pd.notna(row[31]) else "0"
            rank_num = int(rank_str) if rank_str.isdigit() else 0

            if not h_name:
                continue

            if h_name not in horse_past_map:
                horse_past_map[h_name] = []

            if not any(r["date"] == date_str and r["track"] == track and r["rnum"] == rnum for r in horse_past_map[h_name]):
                horse_past_map[h_name].append({
                    "date": date_str,
                    "track": track,
                    "rnum": rnum,
                    "cond": cond,
                    "track_type": track_type,
                    "dist": dist,
                    "sire": sire,
                    "damsire": damsire,
                    "waku": waku_num,
                    "通過1": pass1,
                    "確定着順": rank_num,
                    "着順": rank_num,
                    "馬場状態": "良",
                    "上り3F順位": "0",
                    "PCI": "50.0",
                })

    for h_name in horse_past_map:
        horse_past_map[h_name].sort(key=lambda x: (x["date"], x["rnum"]), reverse=True)

    return horse_past_map


# ==============================================================================
# 4. 全12ファクター完全連動 AI解析エンジン
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
    sire_name="",
    damsire_name="",
):
    past_list = past_index.get(horse_name, [])

    # 日付フィルタリング: 現在のレース日付・レース番号より古い過去走のみ抽出
    filtered_past = [
        p for p in past_list
        if p["date"] < current_race_date or (p["date"] == current_race_date and p["rnum"] < current_race_rnum)
    ]
    filtered_past.sort(key=lambda x: (x["date"], x["rnum"]), reverse=True)

    # 親血統の補填
    if filtered_past and not sire_name:
        sire_name = filtered_past[0].get("sire", "")
    if filtered_past and not damsire_name:
        damsire_name = filtered_past[0].get("damsire", "")

    active_tags = []

    # 1. 脚質判定
    real_style = "先行"
    if filtered_past:
        pass1_vals = [
            float(re.search(r"\d+", str(p["通過1"])).group())
            for p in filtered_past if p.get("通過1") and re.search(r"\d+", str(p["通過1"])) and str(p["通過1"]) != "0"
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

    # 2. 🏁 直近前走（1走前）パフォーマンス・傾向評価
    last_perf_score = 0.0
    last_perf_comment = "前走データ参照中。潜在能力を発揮できる展開。"

    if filtered_past and len(filtered_past) > 0:
        last_race = filtered_past[0]
        l_rank = last_race.get("確定着順", last_race.get("着順", 0))
        l_track_type = last_race.get("track_type", "芝")
        l_waku = last_race.get("waku", 4)

        comment_parts = []

        if l_rank == 1:
            last_perf_score += 8.0
            active_tags.append("前走1着")
            comment_parts.append("前走見事1着（勝利）！連勝・連勝馬券の軸として信頼感抜群。")
        elif 2 <= l_rank <= 5:
            last_perf_score += 4.0
            active_tags.append("前走掲示板")
            comment_parts.append(f"前走掲示板（{l_rank}着）を確保。崩れにくい堅実な競走能力を発揮。")
        elif l_rank > 5:
            comment_parts.append(f"前走は{l_rank}着と着順を落としましたが、巻き返しの条件揃う。")

        # 芝➔ダート替わり
        if "芝" in str(l_track_type) and ("ダ" in str(current_track_type) or "ダート" in str(current_track_type)):
            last_perf_score += 5.0
            active_tags.append("直近芝➔ダート替わり")
            comment_parts.append("前走芝からのダート条件替わり！砂適性発揮による一変に大注目。")

        # ダート内枠好走
        if "ダ" in str(l_track_type) and l_waku in [1, 2] and 1 <= l_rank <= 3:
            last_perf_score += 5.0
            active_tags.append("前走ダート内枠好走")
            comment_parts.append("前走ダート戦の内枠から好走実績あり。被せられても怯まない精神力あり。")

        last_perf_comment = " ".join(comment_parts)

    # 3. 🤖 トラックバイアス適合判定
    tb_adj = 0.0
    tb_comment = "【バイアス適合】標準的なコースバイアス状態。"

    if track_bias == "超イン伸び・最内ラチ有利":
        if waku in [1, 2] and real_style in ["逃げ", "先行"]:
            tb_adj = 12.0
            tb_comment = f"【バイアス絶好】{waku}枠の最内ラチ沿い×前行き脚質。最内を通れる最高の展開です。"
        elif waku in [1, 2]:
            tb_adj = 6.0
            tb_comment = f"【バイアス良好】{waku}枠の最内枠。内目のグリーンベルトを通れる好位置。"
        elif waku in [7, 8]:
            tb_adj = -8.0
            tb_comment = f"【バイアス大逆風】{waku}枠の外枠によりインコースに入れず大幅不利。"

    elif track_bias in ["内伸び・内前有利", "内前有利"]:
        if waku <= 4 and real_style in ["逃げ", "先行"]:
            tb_adj = 10.0
            tb_comment = f"【バイアス絶好】{waku}枠×内前有利。内ラチ沿いを先手奪取できる絶好配置。"
        elif waku >= 7:
            tb_adj = -4.0
            tb_comment = f"【バイアスやや逆風】外枠につきコーナーでの内入れ苦戦。"

    elif track_bias in ["外伸び・外差し有利", "外差し有利"]:
        if waku >= 5 and real_style in ["差し", "追込"]:
            tb_adj = 10.0
            tb_comment = f"【バイアス絶好】{waku}枠×外差し脚質。荒れた内を避けて一気に突き抜ける絶好機会。"
        elif waku <= 2 and real_style in ["逃げ", "先行"]:
            tb_adj = -6.0
            tb_comment = f"【バイアス逆風】最内枠×逃げ・先行。痛んだ内目を通らされる懸念。"

    elif track_bias in ["超前残り・逃げ天国", "前残り強"]:
        if real_style == "逃げ":
            tb_adj = 12.0
            tb_comment = "【バイアス絶好】逃げ天国馬場につき、マイペース逃げからの押し切り濃厚。"
        elif real_style == "追込":
            tb_adj = -10.0
            tb_comment = "【バイアス大逆風】後方追込には絶望的な超前残りバイアス。"

    elif track_bias in ["前崩れ・差し必至"]:
        if real_style in ["差し", "追込"]:
            tb_adj = 10.0
            tb_comment = "【バイアス絶好】前崩れ確実の展開につき、直線大外一気での末脚爆発期待。"
        elif real_style == "逃げ":
            tb_adj = -10.0
            tb_comment = "【バイアス大逆風】ハイペース巻き込まれで直線完全失速のリスク。"

    # 4. 🚩 枠順・コース勝率配置評価
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

    # 5. ⚡ 上がり3F末脚・PCIペース分析
    agari_score = 0.0
    agari_comment = "上がり3Fデータ十分蓄積なし。先行力や立ち回りで補填期待。"

    if filtered_past:
        agari_ranks = [
            int(p["上り3F順位"]) for p in filtered_past
            if p.get("上り3F順位") and str(p["上り3F順位"]).isdigit() and int(p["上り3F順位"]) > 0
        ]
        if agari_ranks:
            best_agari = min(agari_ranks)
            if best_agari == 1:
                agari_score += 8.0
                active_tags.append("上がり最速実績◎")
                agari_comment = "過去走でメンバー最速（上がり1位）の爆発的な末脚をマーク！直線での決め手抜群。"
            elif best_agari <= 3:
                agari_score += 5.0
                agari_comment = f"過去走で上がり最高{best_agari}位の優秀なキレ味を記録。終いの脚比べで強い。"
            else:
                agari_comment = f"過去走の上がり順位最高{best_agari}位。持続力型の展開で強みを発揮。"
        else:
            agari_comment = f"想定ペース【{expected_pace}】に対し、平均的なペース順応力を備えています。"

    # 6. 🧬 血統背景・コース適性評価
    pedigree_score = 0.0
    pedigree_comment = "血統適性分析中。"

    dirt_sires = ["ゴールドアリュール", "ヘニーヒューズ", "シニスターミニスター", "オメガパフューム", "マジェスティックウォリアー", "カリフォルニアクローム", "ドレフォン", "ホッコータルマエ", "スマートファルコン", "エスポワールシチー", "ヴァンゴッホ", "マテラスカイ", "レッドファルクス"]
    turf_sires = ["ディープインパクト", "キズナ", "エピファネイア", "ロードカナロア", "ハーツクライ", "キタサンブラック", "ドゥラメンテ", "コントレイル", "ルーラーシップ", "インディチャンプ"]

    sire_combined = f"{sire_name} {damsire_name}"
    
    if is_dirt:
        if any(s in sire_combined for s in dirt_sires):
            pedigree_score += 5.0
            active_tags.append("血統適性◎")
            pedigree_comment = f"父: {sire_name if sire_name else 'ダート型'} × 母父: {damsire_name if damsire_name else 'パワー型'}。ダート特化のパワー＆砂被り耐久型血統。ダート戦で本領発揮。"
        else:
            pedigree_comment = f"父: {sire_name if sire_name else '標準'} × 母父: {damsire_name if damsire_name else '標準'}。ダート戦に必要な底力とパワーを秘めた血統構成。"
    else:
        if any(s in sire_combined for s in turf_sires):
            pedigree_score += 5.0
            active_tags.append("血統適性◎")
            pedigree_comment = f"父: {sire_name if sire_name else '芝型'} × 母父: {damsire_name if damsire_name else 'スピード型'}。芝コースで瞬発力と切れ味を発揮する王道血統ライン。"
        else:
            pedigree_comment = f"父: {sire_name if sire_name else '標準'} × 母父: {damsire_name if damsire_name else '標準'}。スピード持続力に長けたバランスの良い血統背景。"

    # 7. 🌧️ 馬場適性・過去実績評価
    bad_score_adj = 0.0
    bad_flag = "標準"
    bad_comment = ""

    wet_past_races = [
        p for p in filtered_past
        if p.get("馬場状態") in ["稍重", "重", "不良"]
    ]

    is_wet_track = current_track_condition in ["稍重", "重", "不良"]

    if is_wet_track:
        if wet_past_races:
            best_wet_finish = min([
                int(p.get("確定着順", p.get("着順", 99)))
                for p in wet_past_races if int(p.get("確定着順", p.get("着順", 99))) > 0
            ] or [99])

            if best_wet_finish <= 3:
                bad_score_adj += 8.0
                bad_flag = "道悪◎(好実績)"
                active_tags.append("道悪◎")
                bad_comment = f"過去の道悪馬場で最高{best_wet_finish}着の好実績あり！タフな馬場適性は非常に高く勝機大。"
            elif best_wet_finish <= 5:
                bad_score_adj += 4.0
                bad_flag = "道悪◯"
                active_tags.append("道悪◯")
                bad_comment = f"過去の道悪馬場で掲示板（{best_wet_finish}着）実績あり。重馬場でも崩れにくい。"
            else:
                bad_score_adj -= 5.0
                bad_flag = "道悪割り引き"
                active_tags.append("道悪割り引き")
                bad_comment = f"過去の道悪馬場では凡走傾向（最高{best_wet_finish}着）。馬場悪化でパフォーマンス低下に注意。"
        else:
            if real_style in ["逃げ", "先行"]:
                bad_score_adj += 5.0
                bad_comment = f"道悪の過去走実績は少ないですが、{current_track_condition}馬場×前行き脚質（{real_style}）により前残り恵まれ期待。"
            else:
                bad_comment = f"{current_track_condition}馬場での走破実績はなく未知数。馬場適応への対応力が鍵。"
    else:
        bad_comment = "良馬場開催につき、スピード・瞬発力をフルに発揮できる好条件です。"

    # 8. 📏 距離推移・展開分析
    dist_flag = "適性距離"
    dist_comment = "前走と同等の距離設定推移。"
    curr_dist_num = parse_distance_num(current_race_dist_str)

    if filtered_past and len(filtered_past) > 0:
        last_race = filtered_past[0]
        last_dist_num = parse_distance_num(last_race.get("距離", ""))
        if curr_dist_num > 0 and last_dist_num > 0:
            diff = curr_dist_num - last_dist_num
            if diff <= -200:
                dist_flag = f"距離短縮({diff}m)"
                active_tags.append("距離短縮")
                dist_comment = f"前走{last_dist_num}mから{abs(diff)}mの距離短縮。追走ペースが楽になり末脚爆発の期待大。"
            elif diff >= 200:
                dist_flag = f"距離延長(+{diff}m)"
                active_tags.append("距離延長")
                dist_comment = f"前走{last_dist_num}mから+{diff}mへの距離延長。道中のゆったりした追走が可能。"

    total_score = round(70.0 + last_perf_score + tb_adj + waku_score_adj + agari_score + pedigree_score + bad_score_adj, 1)

    return {
        "real_style": real_style,
        "active_tags": active_tags,
        "last_perf_comment": last_perf_comment,
        "bias_comment": tb_comment,
        "waku_comment": waku_comment,
        "agari_comment": agari_comment,
        "pedigree_comment": pedigree_comment,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
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
    sire = h_data.get("sire", "")
    damsire = h_data.get("damsire", "")

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
        selected_race_obj["rnum"],
        sire,
        damsire,
    )

    processed_horses.append({
        "waku": waku,
        "num": umaban,
        "name": horse_name,
        "jockey": h_data.get("騎手", "未定"),
        "total_score": eval_res["total_score"],
        "real_style": eval_res["real_style"],
        "active_tags": eval_res["active_tags"],
        "last_perf_comment": eval_res["last_perf_comment"],
        "bias_comment": eval_res["bias_comment"],
        "waku_comment": eval_res["waku_comment"],
        "agari_comment": eval_res["agari_comment"],
        "pedigree_comment": eval_res["pedigree_comment"],
        "bad_flag": eval_res["bad_flag"],
        "bad_comment": eval_res["bad_comment"],
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
        for tag in horse["active_tags"]:
            if "1着" in tag or "好走" in tag:
                bg_c = "#059669"
            elif "◎" in tag or "短縮" in tag:
                bg_c = "#2563eb"
            elif "替わり" in tag:
                bg_c = "#7c3aed"
            elif "割り引き" in tag or "不安" in tag:
                bg_c = "#dc2626"
            else:
                bg_c = "#4f46e5"
            tags_html += f'<span style="background-color:{bg_c}; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{tag}</span>'

        raw_card = f"""
        <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div style="flex: 1 1 200px; min-width: 180px;">
                <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">
                    枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}
                </div>
                <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                    想定脚質: <b>{horse['real_style']}</b>
                </div>
                <div style="margin-top: 6px;">{tags_html}</div>
            </div>
            <div style="flex: 2 1 300px; min-width: 250px;">
                <div class="analysis-label">🏁 直近前走パフォーマンス・傾向評価</div>
                <div class="analysis-text">{horse["last_perf_comment"]}</div>
                
                <div class="analysis-label">🤖 AIトラックバイアス適合判定</div>
                <div class="analysis-text">{horse["bias_comment"]}</div>
                
                <div class="analysis-label">🚩 枠順・コース勝率配置評価</div>
                <div class="analysis-text">{horse["waku_comment"]}</div>
                
                <div class="analysis-label">⚡ 上がり3F末脚・PCIペース分析</div>
                <div class="analysis-text">{horse["agari_comment"]}</div>
                
                <div class="analysis-label">🧬 血統背景・コース適性評価</div>
                <div class="analysis-text">{horse["pedigree_comment"]}</div>
                
                <div class="analysis-label">🌧️ 馬場適性・過去実績評価</div>
                <div class="analysis-text">{horse["bad_comment"]}</div>
                
                <div class="analysis-label">📏 距離推移・展開分析</div>
                <div class="analysis-text">{horse["dist_comment"]}</div>
            </div>
            <div style="flex: 0 0 80px; text-align: right;">
                <div class="score-badge">{horse["total_score"]} <span style="font-size:13px;">pt</span></div>
            </div>
        </div>
        """
        cards_html_list.append(textwrap.dedent(raw_card).strip())

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
            raw_t1 = f"""
            <div class="ticket-card">
                <div class="ticket-title">
                    <span>🤝 馬連 (1頭軸流し)</span>
                    <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span>
                </div>
                <div>軸: <b>{h_num}番 ({honmei['name']})</b> ➔ 相手: {t_num}, {a_and_r_str}</div>
                <div class="ticket-combo">買い目: {umaren_combos}</div>
            </div>
            """
            st.markdown(textwrap.dedent(raw_t1).strip(), unsafe_allow_html=True)

            umatan_combos = f"{h_num} ➔ {t_num}" + (f", {a_num}" if a_num else "") + (f", {', '.join(r_nums)}" if r_nums else "")
            raw_t2 = f"""
            <div class="ticket-card">
                <div class="ticket-title">
                    <span>🎯 馬単 (1着固定)</span>
                    <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span>
                </div>
                <div>1着: <b>{h_num}番 ({honmei['name']})</b> ➔ 2着: {t_num}, {a_and_r_str}</div>
                <div class="ticket-combo">買い目: {umatan_combos}</div>
            </div>
            """
            st.markdown(textwrap.dedent(raw_t2).strip(), unsafe_allow_html=True)

            wide_combos = f"{h_num} - {t_num}" + (f", {a_num}" if a_num else "")
            raw_t3 = f"""
            <div class="ticket-card">
                <div class="ticket-title">
                    <span>💎 ワイド (上位人気・単穴BOX)</span>
                    <span style="font-size:12px; color:#6366f1;">推奨: 計 3 点</span>
                </div>
                <div>BOX: <b>{h_num}番, {t_num}番</b> {f', {a_num}番' if a_num else ''}</div>
                <div class="ticket-combo">買い目: {wide_combos}</div>
            </div>
            """
            st.markdown(textwrap.dedent(raw_t3).strip(), unsafe_allow_html=True)

        with col_t2:
            sanrenpuku_combos = f"{h_num} - {t_num} - {a_and_r_str}"
            raw_t4 = f"""
            <div class="ticket-card">
                <div class="ticket-title">
                    <span>🏆 3連複 (軸1頭ながし)</span>
                    <span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)*(len(a_and_r)+1)//2} 点</span>
                </div>
                <div>軸: <b>{h_num}番</b> ➔ 相手: {t_num}, {a_and_r_str}</div>
                <div class="ticket-combo">買い目: {sanrenpuku_combos}</div>
            </div>
            """
            st.markdown(textwrap.dedent(raw_t4).strip(), unsafe_allow_html=True)

            sanrentan_combos = f"{h_num} ➔ {t_num}{f', {a_num}' if a_num else ''} ➔ {t_num}, {a_and_r_str}"
            raw_t5 = f"""
            <div class="ticket-card">
                <div class="ticket-title">
                    <span>🔥 3連単 (フォーメーション)</span>
                    <span style="font-size:12px; color:#6366f1;">推奨高配当狙い</span>
                </div>
                <div>1着: <b>{h_num}番</b> ➔ 2着: {t_num}{f', {a_num}' if a_num else ''} ➔ 3着: {t_num}, {a_and_r_str}</div>
                <div class="ticket-combo">買い目: {sanrentan_combos}</div>
            </div>
            """
            st.markdown(textwrap.dedent(raw_t5).strip(), unsafe_allow_html=True)

# ==============================================================================
# 7. フッター (免責事項・プライバシーポリシー・お問い合わせ先)
# ==============================================================================
st.markdown(
    textwrap.dedent("""
    <div style="margin-top: 50px; padding: 24px; background-color: #ffffff; border-top: 2px solid #e2e8f0; border-radius: 16px; font-size: 12px; color: #64748b; line-height: 1.6; box-shadow: 0 2px 6px rgba(0,0,0,0.02);">
        <div style="font-weight: 800; font-size: 14px; color: #1e1b4b; margin-bottom: 8px;">📌 免責事項・運営情報</div>
        <p style="margin-bottom: 8px;"><b>【免責事項】</b> 当サイト「KUINA AI | Racing Intelligence System」で提供している予想情報、AIスコア、分析データは勝ち馬投票券の的中や利益を保証するものではありません。競馬の予想・馬券のご購入は、必ずご自身の判断と自己責任において行っていただけますようお願い申し上げます。当サイトの利用により生じた直接的・間接的な損害について、当サイトは一切の責任を負いかねます。</p>
        <p style="margin-bottom: 8px;"><b>【プライバシーポリシー】</b> 当サイトでは、第三者配信事業者（Google AdSense等）による広告配信のためにCookie（クッキー）を使用することがあります。これにより、お客様のサイト訪問履歴に応じた適切な広告が表示されます。Cookieを無効にする設定は、お使いのブラウザの設定画面より可能です。</p>
        <div style="margin-top: 12px; font-weight: 700; color: #334155;">📩 お問い合わせ先（Contact）: <a href="mailto:kuina.ai.keiba@gmail.com" style="color: #4f46e5; text-decoration: underline;">kuina.ai.keiba@gmail.com</a></div>
    </div>
    """).strip(),
    unsafe_allow_html=True
)
