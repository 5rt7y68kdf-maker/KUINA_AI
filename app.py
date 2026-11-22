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
        font-size: 24px;
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
        margin-bottom: 16px;
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
# 3. CSVデータ一括パースエンジン（Fallback用）
# ==============================================================================

def build_races_from_csvs():
    raw_files = (
        glob.glob("./*.csv") + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv") + glob.glob("./data/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv") + glob.glob("/workspace/knowledge/*.CSV")
    )
    raw_files = sorted(list(set(raw_files)))
    
    race_files = []
    pedigree_map = {}
    past_files = []

    for f in raw_files:
        bn = os.path.basename(f)
        if any(k in bn for k in ["枠番", "脚質"]):
            continue
        if "過去走" in bn:
            past_files.append(f)
        elif "血統" in bn:
            key = bn.replace("血統", "").replace(".csv", "").replace(".CSV", "")
            pedigree_map[key] = f
        else:
            race_files.append(f)

    date_races_map = {}

    for fpath in race_files:
        bn = os.path.basename(fpath)
        base_key = bn.replace(".csv", "").replace(".CSV", "")
        ped_fpath = pedigree_map.get(base_key)

        fn_date = ""
        m_date = re.search(r"(\d{8}|\d{6})", bn)
        if m_date:
            ds = m_date.group(1)
            if len(ds) == 6:
                fn_date = f"20{ds[:2]}-{ds[2:4]}-{ds[4:6]}"
            elif len(ds) == 8:
                fn_date = f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}"

        df_main = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df_main = pd.read_csv(fpath, encoding=enc, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass

        if df_main is None or df_main.empty:
            continue

        df_ped = None
        if ped_fpath:
            for enc in ["cp932", "shift_jis", "utf-8"]:
                try:
                    df_ped = pd.read_csv(ped_fpath, encoding=enc, dtype=str, on_bad_lines="skip")
                    break
                except Exception:
                    pass

        # Case A: Named columns
        if "馬名S" in df_main.columns or "馬名" in df_main.columns:
            if df_ped is not None and ("馬名S" in df_ped.columns or "馬名" in df_ped.columns):
                h_col = "馬名S" if "馬名S" in df_main.columns else "馬名"
                ped_h_col = "馬名S" if "馬名S" in df_ped.columns else "馬名"
                df_merged = pd.merge(df_main, df_ped, left_on=h_col, right_on=ped_h_col, suffixes=("", "_ped"), how="left")
            else:
                df_merged = df_main

            races_by_key = {}
            for row in df_merged.to_dict("records"):
                ba_r = str(row.get("場 R", "")).strip()
                h_name = str(row.get("馬名S", row.get("馬名", ""))).strip()
                if not h_name:
                    continue

                track = ba_r[:1] if ba_r else "東京"
                rnum_str = re.sub(r"\D", "", ba_r) or "1"
                rnum = int(rnum_str)

                date_str = fn_date or "2026-11-23"
                key = (date_str, track, rnum)

                if key not in races_by_key:
                    races_by_key[key] = {
                        "date": date_str,
                        "track": track,
                        "rnum": rnum,
                        "cond": str(row.get("クラス", "未勝利")).strip(),
                        "track_type": str(row.get("今芝ダ", "芝")).strip() or "芝",
                        "dist": str(row.get("距離", "1800")).strip(),
                        "horses": []
                    }

                umaban_raw = re.sub(r"\D", "", str(row.get("馬番", "1")))
                umaban = int(umaban_raw) if umaban_raw else 1

                horse_dict = {
                    "馬番": umaban,
                    "馬名": h_name,
                    "騎手": str(row.get("騎手", "未定")).strip(),
                    "斤量": str(row.get("斤量", "56")).strip(),
                    "性別": str(row.get("性", "牡")).strip(),
                    "年齢": str(row.get("齢", "3")).strip(),
                    "種牡馬": str(row.get("種牡馬", "")).strip(),
                    "母名": str(row.get("母名", "")).strip(),
                    "母父名": str(row.get("母父名", "")).strip(),
                    "父タイプ名": str(row.get("父タイプ名", "")).strip(),
                    "母父タイプ名": str(row.get("母父タイプ名", "")).strip(),
                    "前着順": str(row.get("前着順", "")).strip(),
                    "前着差": str(row.get("前着差", "0.5")).strip(),
                    "前クラス": str(row.get("前ｸﾗｽ", "")).strip(),
                    "前人気": str(row.get("前人気", "")).strip(),
                    "前脚質": str(row.get("前脚質", "")).strip(),
                    "前距離": str(row.get("前距離", "")).strip(),
                    "距離差": str(row.get("距離差", "0")).strip(),
                    "間隔": str(row.get("間隔", "4")).strip(),
                }
                races_by_key[key]["horses"].append(horse_dict)

            for key, rdata in races_by_key.items():
                tot = len(rdata["horses"])
                for h in rdata["horses"]:
                    if "枠番" not in h:
                        h["枠番"] = get_jra_waku(h["馬番"], tot)
                d_str = rdata["date"]
                if d_str not in date_races_map:
                    date_races_map[d_str] = []
                date_races_map[d_str].append(rdata)

        # Case B: Headerless CSV
        else:
            races_by_key = {}
            for row in df_main.values:
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

                if not horse_name:
                    continue

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
                        "horses": []
                    }

                races_by_key[key]["horses"].append({
                    "馬番": umaban_num,
                    "馬名": horse_name,
                    "騎手": jockey,
                    "性別": str(row[8]).strip() if len(row) > 8 and pd.notna(row[8]) else "牡",
                    "年齢": str(row[9]).strip() if len(row) > 9 and pd.notna(row[9]) else "3",
                    "斤量": "56",
                    "種牡馬": "",
                    "母名": "",
                    "母父名": "",
                    "父タイプ名": "",
                    "母父タイプ名": "",
                    "前着順": "",
                    "前着差": "0.5",
                    "前クラス": "",
                    "前人気": "",
                    "前脚質": "",
                    "前距離": "",
                    "距離差": "0",
                    "間隔": "4",
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
def scan_and_load_all_csvs():
    json_candidates = ["races_data.json", "./data/races_data.json", "/workspace/knowledge/races_data.json", "/workspace/scratch/races_data.json"]
    for jpath in json_candidates:
        if os.path.exists(jpath):
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                pass

    date_races_map = build_races_from_csvs()

    for out_path in ["races_data.json", "/workspace/scratch/races_data.json"]:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(date_races_map, f, ensure_ascii=False, indent=2)
            break
        except Exception:
            pass

    return date_races_map


@st.cache_data(ttl=3600, show_spinner=False)
def load_past_races_index():
    json_candidates = ["past_index.json", "./data/past_index.json", "/workspace/knowledge/past_index.json", "/workspace/scratch/past_index.json"]
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
                    "クラス": str(row.get("クラス", row.get("前走クラス", ""))),
                    "着差": str(row.get("着差", "0.5")),
                    "距離": str(row.get("距離", "1800")),
                })

    return horse_past_map


# ==============================================================================
# 4. 全7大ファクター完全統合 AI解析エンジン
# ==============================================================================

def analyze_horse_full(
    h_data,
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
):
    horse_name = h_data.get("馬名", "不明馬")
    umaban = h_data.get("馬番", 1)

    past_list = past_index.get(horse_name, [])

    # 1. 脚質判定
    real_style = "先行"
    prev_style = h_data.get("前脚質", "")
    if prev_style:
        if "逃" in prev_style: real_style = "逃げ"
        elif "先" in prev_style: real_style = "先行"
        elif "差" in prev_style or "中" in prev_style: real_style = "差し"
        elif "追" in prev_style or "後" in prev_style: real_style = "追込"
    elif past_list:
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

    # --- Factor 1: 血統構成・系統相性 ---
    sire = h_data.get("種牡馬", "")
    damsire = h_data.get("母父名", "")
    sire_type = h_data.get("父タイプ名", "")
    damsire_type = h_data.get("母父タイプ名", "")

    ped_score = 0.0
    is_wet_track = current_track_condition in ["稍重", "重", "不良"]

    if is_wet_track:
        if any(k in (sire + damsire) for k in ["ドゥラメンテ", "エピファネイア", "ハービンジャー", "キズナ", "モーリス", "ルーラーシップ", "ゴールドシップ", "シニスターミニスター"]) or "ロベルト" in (sire_type + damsire_type):
            ped_score += 6.0
            ped_comment = f"父:{sire or '未登録'} × 母父:{damsire or '未登録'}。道悪・タフ馬場パワー血統により、今回の{current_track_condition}馬場で強烈な血統恩恵あり。"
        else:
            ped_comment = f"父:{sire or '未登録'} × 母父:{damsire or '未登録'}。タフな馬場状態でのパワー適性に要注視。"
    else:
        if any(k in (sire + damsire) for k in ["キタサンブラック", "ディープインパクト", "スワーヴリチャード", "ロードカナロア", "ワールドエース", "アルアイン", "シルバーステート"]):
            ped_score += 5.0
            ped_comment = f"父:{sire or '未登録'} × 母父:{damsire or '未登録'}。良馬場で圧倒的な瞬発力・キレ味を発揮する高速馬場ベスト血統。"
        else:
            ped_comment = f"父:{sire or '未登録'} × 母父:{damsire or '未登録'}。持続力を活かせるバランス型の血統構成。"

    # --- Factor 2: 前走成績・競走能力 ---
    perf_score = 0.0
    last_rank = h_data.get("前着順", "")
    last_margin_raw = h_data.get("前着差", "0.5")

    try:
        last_margin = float(re.search(r"[-+]?\d*\.\d+|\d+", str(last_margin_raw)).group())
    except Exception:
        last_margin = 0.5

    if "1着" in last_rank or "１" in last_rank:
        perf_score += 8.0
        perf_comment = "前走1着と勝利を挙げて勢いに乗る好調評価。着順通りの能力を発揮。"
    elif any(k in last_rank for k in ["2着", "3着", "２着", "３着"]):
        perf_score += 5.0
        perf_comment = f"前走{last_rank}と掲示板・券内を確保。安定した好走能力を評価。"
    else:
        if last_margin <= 0.3:
            perf_score += 4.0
            perf_comment = f"前走{last_rank}（タイム差{last_margin}秒）と勝ち馬から僅差。着順以上の高い競走能力。"
        elif last_margin >= 1.5:
            perf_score -= 4.0
            perf_comment = f"前走{last_rank}（タイム差{last_margin}秒）と大敗。一変への状態引き上げと展開の助けが必要。"
        else:
            perf_comment = f"前走{last_rank}。展開ひとつで上位争いに加われるポテンシャル。"

    # --- Factor 3: 枠番・展開配置評価 ---
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
            waku_comment = f"ダート好走の黄金パターンである外{waku}枠。砂被りを回避しスムーズに進出可能。"
        else:
            if total_horses >= 15:
                waku_score_adj -= 3.0
                waku_comment = f"多頭数（{total_horses}頭立）の外{waku}枠。終始外を回らされる距離ロスの懸念あり。"
            else:
                waku_comment = f"外枠の{waku}枠。スムーズに包まれず運べる反面、コーナーでの距離ロスには注意。"

    # トラックバイアス連動
    tb_adj = 0.0
    tb_comment = ""
    if track_bias == "超イン伸び・最内ラチ有利":
        if waku in [1, 2] and real_style in ["逃げ", "先行"]:
            tb_adj = 10.0
            tb_comment = " ➔ 【バイアス絶好】最内ラチ沿い×前行きでインのグリーンベルト通過可能。"
        elif waku in [7, 8]:
            tb_adj = -6.0
            tb_comment = " ➔ 【バイアス逆風】外枠につきインコースに入れず不利。"
    elif track_bias in ["内伸び・内前有利", "内前有利"]:
        if waku <= 4 and real_style in ["逃げ", "先行"]:
            tb_adj = 8.0
            tb_comment = " ➔ 【バイアス絶好】内枠×内前有利。ロスなく先手を奪える強みあり。"
    elif track_bias in ["外伸び・外差し有利", "外差し有利"]:
        if waku >= 5 and real_style in ["差し", "追込"]:
            tb_adj = 8.0
            tb_comment = " ➔ 【バイアス絶好】外枠×外差し脚質。痛んだ内を避けて一気に突き抜ける展解。"
    elif track_bias in ["超前残り・逃げ天国", "前残り強"]:
        if real_style == "逃げ":
            tb_adj = 10.0
            tb_comment = " ➔ 【バイアス絶好】マイペース逃げからの押し切り濃厚。"
    elif track_bias in ["前崩れ・差し必至"]:
        if real_style in ["差し", "追込"]:
            tb_adj = 10.0
            tb_comment = " ➔ 【バイアス絶好】前崩れのハイペース巻き込みで末脚爆発の期待大。"

    waku_full_comment = waku_comment + tb_comment

    # --- Factor 4: 馬場適性・過去実績 ---
    bad_score_adj = 0.0
    bad_flag = "標準"
    bad_comment = ""

    wet_past_races = [
        p for p in past_list
        if p.get("馬場状態") in ["稍重", "重", "不良"]
    ]

    if is_wet_track:
        if wet_past_races:
            best_wet_finish = min([
                int(re.search(r"\d+", p.get("着順", "99")).group())
                for p in wet_past_races if re.search(r"\d+", p.get("着順", "99"))
            ] or [99])

            if best_wet_finish <= 3:
                bad_score_adj += 8.0
                bad_flag = "道悪◎(好実績)"
                bad_comment = f"過去の道悪馬場で最高{best_wet_finish}着の好実績あり！タフな馬場適性は非常に高い。"
            elif best_wet_finish <= 5:
                bad_score_adj += 4.0
                bad_flag = "道悪◯"
                bad_comment = f"過去の道悪馬場で掲示板（{best_wet_finish}着）獲得。重馬場でも崩れにくいパワーを装備。"
            else:
                bad_score_adj -= 5.0
                bad_flag = "道悪不安"
                bad_comment = f"過去の道悪馬場では凡走傾向（最高{best_wet_finish}着）。馬場悪化による割引が必要。"
        else:
            if real_style in ["逃げ", "先行"]:
                bad_score_adj += 4.0
                bad_flag = "道悪注意(前行き)"
                bad_comment = f"過去の道悪実績は少ないですが、前行き脚質（{real_style}）による前残り恩恵を期待。"
            else:
                bad_comment = f"{current_track_condition}馬場での走破実績はなく未知数。パワー適性の高まりに対応できるかが鍵。"
    else:
        bad_comment = "良馬場開催につき、スピード・瞬発力をフルに発揮できる好条件です。"

    # --- Factor 5: 距離推移・ペース適合 ---
    dist_flag = "適性距離"
    dist_comment = ""
    curr_dist_num = parse_distance_num(current_race_dist_str)
    dist_diff_str = h_data.get("距離差", "0")

    try:
        dist_diff = float(re.search(r"[-+]?\d+", str(dist_diff_str)).group())
    except Exception:
        dist_diff = 0.0

    if dist_diff <= -150:
        dist_flag = f"距離短縮({int(dist_diff)}m)"
        dist_comment = f"前走から{abs(int(dist_diff))}mの距離短縮。追走ペースが楽になり追込・末脚爆発の期待大。"
    elif dist_diff >= 150:
        dist_flag = f"距離延長(+{int(dist_diff)}m)"
        dist_comment = f"前走から+{int(dist_diff)}mの距離延長。道中のゆったりした折り合いとスタミナが問われる一戦。"
    else:
        dist_comment = "同等距離設定での出走。ベストのペースで立ち回れる安定した距離推移。"

    if expected_pace == "ハイ" and real_style in ["差し", "追込"]:
        dist_comment += " 想定ハイペースにより直線での差し脚展開が絶好にハマる好材料。"
    elif expected_pace == "スロー" and real_style in ["逃げ", "先行"]:
        dist_comment += " 想定スローペースにより楽な前目マイペース粘り込みが可能。"

    # --- Factor 6: 斤量・騎手評価 ---
    jockey = h_data.get("騎手", "未定")
    kinryo = h_data.get("斤量", "56")
    jockey_score = 0.0
    if any(k in jockey for k in ["ルメール", "川田", "武豊", "横山武", "戸崎", "モレイラ", "レーン", "松山", "坂井"]):
        jockey_score += 4.0

    kinryo_comment = f"鞍上: {jockey} 騎手 ｜ 斤量: {kinryo}kg。"
    if "▲" in kinryo or "△" in kinryo or "★" in kinryo or "☆" in kinryo:
        kinryo_comment += " 減量騎手起用により軽い斤量を活かした立ち回りアドバンテージあり。"
    else:
        kinryo_comment += " 実力派鞍上とのタッグで能力を存分に発揮できる勝負気配。"

    # --- Factor 7: 総合勝負気配・オッズ期待値 ---
    value_score = 0.0
    last_pop_raw = h_data.get("前人気", "")
    try:
        last_pop = float(re.search(r"\d+", str(last_pop_raw)).group())
    except Exception:
        last_pop = 5.0

    if last_pop <= 3.0 and "1着" not in last_rank:
        value_score += 5.0
        value_comment = "🔥 【巻き返し注目馬】前走上位人気に支持された素質馬。敗戦によるオッズ妙味と巻き返し期待値が絶大！"
    elif perf_score >= 5.0:
        value_comment = "👑 【信頼度抜群】安定した好好走パフォーマンスを維持しており、確実な好勝負を期待できる安定株。"
    else:
        value_comment = "🎯 展開や馬場状態の噛み合いひとつで穴を開ける好配当ターゲット。"

    # 総合スコア集計
    total_score = round(70.0 + ped_score + perf_score + waku_score_adj + tb_adj + bad_score_adj + jockey_score + value_score, 1)

    return {
        "real_style": real_style,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
        "waku_comment": waku_full_comment,
        "dist_flag": dist_flag,
        "dist_comment": dist_comment,
        "ped_comment": ped_comment,
        "perf_comment": perf_comment,
        "kinryo_comment": kinryo_comment,
        "value_comment": value_comment,
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
    st.error("⚠️ 読み込めるレースデータ（races_data.json または 出走表CSV）が見つかりません。")
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
        出走頭数: <b>{len(current_race_horses)}頭 AI完全解析（全7大ファクター照合中）</b>
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

# --- 全7ファクター完全統合型スコア演算 ---
processed_horses = []
tot_horses_count = len(current_race_horses)

for h_data in current_race_horses:
    waku = h_data.get("枠番", get_jra_waku(h_data.get("馬番", 1), tot_horses_count))
    umaban = h_data.get("馬番", 1)

    eval_res = analyze_horse_full(
        h_data,
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
    )

    processed_horses.append({
        "waku": waku,
        "num": umaban,
        "name": h_data.get("馬名", "不明馬"),
        "jockey": h_data.get("騎手", "未定"),
        "total_score": eval_res["total_score"],
        "real_style": eval_res["real_style"],
        "bad_flag": eval_res["bad_flag"],
        "bad_comment": eval_res["bad_comment"],
        "waku_comment": eval_res["waku_comment"],
        "dist_flag": eval_res["dist_flag"],
        "dist_comment": eval_res["dist_comment"],
        "ped_comment": eval_res["ped_comment"],
        "perf_comment": eval_res["perf_comment"],
        "kinryo_comment": eval_res["kinryo_comment"],
        "value_comment": eval_res["value_comment"],
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
    st.subheader(f"🏆 【{clean_race_title}】 KUINA AI分析スコア (全7ファクター完全表示)")

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

        bg_col, text_col = WAKU_COLOR_MAP.get(horse["waku"], ("#ffffff", "#000000"))

        factors_grid_html = f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 8px; margin-top: 10px;">
            <div style="background:#f1f5f9; padding:8px 10px; border-radius:8px;">
                <div style="font-weight:800; font-size:12px; color:#1e1b4b;">🧬 1. 血統構成・系統相性</div>
                <div style="font-size:11px; color:#334155; line-height:1.4;">{horse['ped_comment']}</div>
            </div>
            <div style="background:#f1f5f9; padding:8px 10px; border-radius:8px;">
                <div style="font-weight:800; font-size:12px; color:#1e1b4b;">🏆 2. 前走成績・競走能力</div>
                <div style="font-size:11px; color:#334155; line-height:1.4;">{horse['perf_comment']}</div>
            </div>
            <div style="background:#f1f5f9; padding:8px 10px; border-radius:8px;">
                <div style="font-weight:800; font-size:12px; color:#1e1b4b;">🏁 3. 枠順・展開配置評価</div>
                <div style="font-size:11px; color:#334155; line-height:1.4;">{horse['waku_comment']}</div>
            </div>
            <div style="background:#f1f5f9; padding:8px 10px; border-radius:8px;">
                <div style="font-weight:800; font-size:12px; color:#1e1b4b;">🌧️ 4. 馬場適性・過去実績</div>
                <div style="font-size:11px; color:#334155; line-height:1.4;">{horse['bad_comment']}</div>
            </div>
            <div style="background:#f1f5f9; padding:8px 10px; border-radius:8px;">
                <div style="font-weight:800; font-size:12px; color:#1e1b4b;">📏 5. 距離推移・ペース適合</div>
                <div style="font-size:11px; color:#334155; line-height:1.4;">{horse['dist_comment']}</div>
            </div>
            <div style="background:#f1f5f9; padding:8px 10px; border-radius:8px;">
                <div style="font-weight:800; font-size:12px; color:#1e1b4b;">⚖️ 6. 斤量・騎手評価</div>
                <div style="font-size:11px; color:#334155; line-height:1.4;">{horse['kinryo_comment']}</div>
            </div>
            <div style="background:#eef2ff; padding:8px 10px; border-radius:8px; grid-column: 1 / -1; border: 1px solid #c7d2fe;">
                <div style="font-weight:800; font-size:12px; color:#312e81;">🎯 7. 総合勝負気配・オッズ期待値</div>
                <div style="font-size:11px; color:#1e1b4b; line-height:1.4; font-weight:600;">{horse['value_comment']}</div>
            </div>
        </div>
        """

        card_code = f"""
        <div class="horse-card">
            <div style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px;">
                <div>
                    <h4 style="margin: 0 0 4px 0; font-size: 20px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                    <div style="font-size: 13px; color: #64748b;">
                        <span style="display:inline-block; width:20px; height:20px; border-radius:50%; background-color:{bg_col}; color:{text_col}; text-align:center; line-height:20px; font-weight:bold; font-size:11px; margin-right:4px;">{horse['num']}</span>
                        枠{horse['waku']} {horse['num']}番 ｜ 騎手: <b>{horse['jockey']}</b> ｜ 想定脚質: <b>{horse['real_style']}</b>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div>{tags_html}</div>
                    <div class="score-badge">{horse['total_score']} <span style="font-size:13px;">pt</span></div>
                </div>
            </div>
            {factors_grid_html}
        </div>
        """
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
