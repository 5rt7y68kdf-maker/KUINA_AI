import datetime
import glob
import math
import hashlib
import os
import re
import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. ページ基本設定 ＆ スタイリッシュ＆スマホ最適化CSS
# ==============================================================================
st.set_page_config(
    page_title="KUINA | AI Racing Intelligence",
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
        padding: 24px 28px;
        border-radius: 18px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .kuina-header h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 900;
        letter-spacing: -0.5px;
        background: linear-gradient(to right, #ffffff, #a5f3fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .kuina-header p {
        margin: 6px 0 0 0;
        color: #cbd5e1;
        font-size: 13px;
        font-weight: 500;
        letter-spacing: 0.2px;
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
        font-size: 20px;
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
    .horse-pill {
        display: inline-block;
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        color: #334155;
        border-radius: 20px;
        padding: 5px 12px;
        margin: 3px;
        font-size: 12px;
        font-weight: 700;
    }
    .ticket-card {
        background: #ffffff;
        border: 1.5px solid #e2e8f0;
        border-top: 4px solid #6366f1;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .ticket-title {
        font-size: 16px;
        font-weight: 800;
        color: #1e1b4b;
        margin-bottom: 10px;
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
    @media (max-width: 768px) {
        .kuina-header { padding: 18px 20px; border-radius: 14px; }
        .kuina-header h1 { font-size: 22px; }
        .kuina-header p { font-size: 12px; }
        .race-banner { padding: 14px 16px; }
        .race-banner-title { font-size: 17px; }
        .horse-card { padding: 14px; margin-bottom: 12px; }
        .score-badge { font-size: 22px; text-align: left; margin-top: 8px; }
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. ユーティリティ ＆ クラス/着差/距離パース関数
# ==============================================================================

def get_stable_hash(text):
    """再起動後も変動しない固定ハッシュ値 (0-99)"""
    return int(hashlib.md5(str(text).encode("utf-8")).hexdigest(), 16) % 100


def parse_class_rank(class_str):
    """クラスの格（階級）を数値化 (G1:9 〜 新馬:1)"""
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


def parse_margin_seconds(margin_str):
    """着差文字列（例: '0.2', 'クビ', 'ハナ'）を秒数フロートに変換"""
    if not margin_str:
        return 9.9
    s = str(margin_str).strip()
    try:
        val = float(re.sub(r"[^\d.]", "", s))
        return abs(val)
    except Exception:
        if "同タイ" in s or "ハナ" in s: return 0.05
        if "クビ" in s: return 0.1
        if "アタマ" in s: return 0.15
        if "1/2" in s: return 0.2
        if "3/4" in s: return 0.3
        if "大差" in s: return 2.0
        return 0.5


def parse_distance_num(dist_str):
    """距離文字列（例: '1800', '芝1800m'）から数値を取得"""
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
    """頭数に応じたJRA標準枠番算出"""
    if total_horses <= 8:
        return umaban
    capacities = [1] * 8
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


# ==============================================================================
# 3. 超軽量データロード (三会場対応 ＆ 過去走10ファイル最適化)
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def scan_and_load_all_csvs():
    """三会場（全競馬場・1日最大36R以上）対応の出走表ロード"""
    raw_files = (
        glob.glob("./*.csv")
        + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv")
        + glob.glob("./data/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv")
        + glob.glob("/workspace/knowledge/*.CSV")
    )
    if not raw_files:
        raw_files = glob.glob("./**/*.csv", recursive=True) + glob.glob("./**/*.CSV", recursive=True)

    all_csv_files = []
    for f in raw_files:
        normalized = os.path.normpath(f)
        if ".venv" in normalized or ".git" in normalized or "__pycache__" in normalized:
            continue
        fname = os.path.basename(normalized)
        if "枠番" in fname or "脚質" in fname or "過去走" in fname:
            continue
        all_csv_files.append(f)

    all_csv_files = sorted(list(set(all_csv_files)))
    date_races_map = {}

    for fpath in all_csv_files:
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, header=None, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass

        if df is None or df.empty:
            continue

        races_by_key = {}

        if len(df.columns) >= 12:
            vals = df.values
            for row in vals:
                col0 = str(row[0]).strip() if pd.notna(row[0]) else ""
                clean_date_col = col0.replace("-", "")
                if not clean_date_col.isdigit():
                    continue

                if len(clean_date_col) == 6:
                    date_str = f"20{clean_date_col[:2]}-{clean_date_col[2:4]}-{clean_date_col[4:6]}"
                elif len(clean_date_col) == 8:
                    date_str = f"{clean_date_col[:4]}-{clean_date_col[4:6]}-{clean_date_col[6:8]}"
                else:
                    continue

                track = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""
                rnum_str = str(row[2]).strip() if len(row) > 2 and pd.notna(row[2]) else "1"
                rnum = int(rnum_str) if rnum_str.isdigit() else 1
                umaban_str = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else "1"
                cond = str(row[4]).strip() if len(row) > 4 and pd.notna(row[4]) else ""
                track_type = str(row[5]).strip() if len(row) > 5 and pd.notna(row[5]) else ""
                dist = str(row[6]).strip() if len(row) > 6 and pd.notna(row[6]) else ""
                horse_name = str(row[7]).strip() if len(row) > 7 and pd.notna(row[7]) else ""
                sex = str(row[8]).strip() if len(row) > 8 and pd.notna(row[8]) else "牡"
                age = str(row[9]).strip() if len(row) > 9 and pd.notna(row[9]) else "3"
                jockey = str(row[10]).strip() if len(row) > 10 and pd.notna(row[10]) else "未定"
                kinryo = str(row[11]).strip() if len(row) > 11 and pd.notna(row[11]) else "56"

                odds = "10.0"
                if len(row) > 12:
                    for p in row[12:]:
                        p_str = str(p).strip() if pd.notna(p) else ""
                        try:
                            v = float(p_str)
                            if 1.0 <= v <= 999.0 and "." in p_str:
                                odds = str(v)
                                break
                        except ValueError:
                            pass

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
                    "馬番": int(umaban_str) if umaban_str.isdigit() else len(races_by_key[key]["horses"]) + 1,
                    "馬名": horse_name,
                    "騎手": jockey,
                    "単勝オッズ": odds,
                    "性別": sex,
                    "年齢": age,
                    "斤量": kinryo
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
    """2026過去走_1.csv〜10.csvを軽量インデックス化 (前走距離情報含む)"""
    past_files = sorted(
        glob.glob("./*過去走*.csv")
        + glob.glob("./*過去走*.CSV")
        + glob.glob("./data/*過去走*.csv")
        + glob.glob("/workspace/knowledge/*過去走*.csv")
    )
    if not past_files:
        past_files = sorted(glob.glob("./**/*過去走*.csv", recursive=True))

    horse_past_map = {}

    for fpath in past_files:
        if not os.path.exists(fpath):
            continue

        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass

        if df is None or df.empty:
            continue

        col_map = {col: col.strip() for col in df.columns}
        df.rename(columns=col_map, inplace=True)

        target_cols = [c for c in ["馬名", "通過1", "頭数", "馬場状態", "着順", "上り3F順位", "PCI", "クラス", "前走クラス", "着差", "タイム差", "レース名", "距離", "前走距離", "コース"] if c in df.columns]
        if "馬名" not in target_cols:
            continue

        sub_df = df[target_cols]

        for row in sub_df.to_dict("records"):
            h_name = str(row.get("馬名", "")).strip()
            if not h_name:
                continue

            if h_name not in horse_past_map:
                horse_past_map[h_name] = []

            if len(horse_past_map[h_name]) < 5:
                race_cls = str(row.get("クラス", row.get("前走クラス", row.get("レース名", ""))))
                margin_val = str(row.get("着差", row.get("タイム差", "0.5")))
                dist_val = str(row.get("距離", row.get("前走距離", row.get("コース", "1800"))))

                horse_past_map[h_name].append({
                    "通過1": str(row.get("通過1", "")),
                    "頭数": str(row.get("頭数", "16")),
                    "馬場状態": str(row.get("馬場状態", "良")),
                    "着順": str(row.get("着順", "99")),
                    "上り3F順位": str(row.get("上り3F順位", "99")),
                    "PCI": str(row.get("PCI", "50.0")),
                    "クラス": race_cls,
                    "着差": margin_val,
                    "距離": dist_val
                })

    return horse_past_map


# ==============================================================================
# 4. 高精度AI解析エンジン (距離短縮/延長ファクター統合)
# ==============================================================================

def analyze_horse_enhanced(horse_name, umaban, waku, current_race_cond, current_race_dist_str, past_index, current_track_condition, weather, track_bias, expected_pace):
    """【前走クラス・着差・距離変化(短縮/延長)統合】AI分析スコア計算処理"""
    past_list = past_index.get(horse_name, [])
    h_hash = get_stable_hash(horse_name)

    # 1. 脚質判定
    real_style = "先行"
    if past_list:
        pass1_vals = []
        for p in past_list:
            m = re.search(r"\d+", p.get("通過1", ""))
            if m:
                pass1_vals.append(float(m.group()))
        if pass1_vals:
            avg_p1 = sum(pass1_vals) / len(pass1_vals)
            if avg_p1 <= 2.0: real_style = "逃げ"
            elif avg_p1 <= 5.0: real_style = "先行"
            elif avg_p1 <= 10.0: real_style = "差し"
            else: real_style = "追込"
    else:
        styles = ["逃げ", "先行", "差し", "追込"]
        real_style = styles[h_hash % 4]

    score_adj = 0.0
    bad_flag = "標準"
    bad_comment = "過去の馬場実績・天候ともに標準的な適性範囲内です。"

    # 2. 道悪評価
    if weather in ["雨", "雪"] and current_track_condition in ["稍重", "重", "不良"]:
        if real_style in ["逃げ", "先行"]:
            score_adj += 5.0
            bad_comment = "降雨・道悪前残り馬場バイアスの影響により好位からの粘り込みが期待できます。"

    if current_track_condition in ["稍重", "重", "不良"]:
        bad_races = [p for p in past_list if any(b in p.get("馬場状態", "") for b in ["稍重", "重", "不良"])]
        if bad_races:
            top3 = sum(1 for p in bad_races if int(re.search(r"\d+", p.get("着順", "99")).group() if re.search(r"\d+", p.get("着順", "99")) else 99) <= 3)
            rate = top3 / len(bad_races)
            if rate >= 0.5:
                score_adj += 10.0
                bad_flag = "道悪◎"
                bad_comment = f"道悪実績豊富（道悪複勝率 {round(rate*100)}% [{top3}/{len(bad_races)}]）。"
            elif rate == 0.0 and len(bad_races) >= 2:
                score_adj -= 10.0
                bad_flag = "道悪×"
                bad_comment = f"道悪馬場でパフォーマンス低下の傾向あり（過去道悪{len(bad_races)}戦0複勝）。"

        if current_track_condition in ["重", "不良"]:
            if real_style in ["逃げ", "先行"]:
                score_adj += 8.0
                if bad_flag == "標準": bad_flag = "前残り警戒"
                bad_comment += " 重馬場×前行き脚質（前残り展開の恩恵あり）。"
            elif real_style == "追込":
                score_adj -= 6.0
                if bad_flag == "標準": bad_flag = "危険馬"
                bad_comment += "（※重馬場×追込脚質のため展開面で大幅割り引き）。"
    else:
        bad_comment = "良馬場開催のため、極端な馬場悪化による割り引き・加点はなし。"

    # 3. トラックバイアス評価
    tb_adj = 0.0
    tb_comment = "トラックバイアスによる極端な有利・不利は認められません。"
    if track_bias == "内前有利":
        if waku <= 4 and real_style in ["逃げ", "先行"]:
            tb_adj = 8.0
            tb_comment = f"{waku}枠の絶好枠×前行き脚質。内前有利の馬場バイアスを最大限に活かせる展開です。"
        elif real_style in ["逃げ", "先行"]:
            tb_adj = 4.0
            tb_comment = "内前有利馬場につき、好位でロスなく立ち回れるポジションが強みとなります。"
        elif waku >= 7:
            tb_adj = -5.0
            tb_comment = f"{waku}枠の外枠により終始外を回らされる懸念あり（内前有利馬場バイアス不利）。"
    elif track_bias == "外差し有利":
        if waku >= 5 and real_style in ["差し", "追込"]:
            tb_adj = 8.0
            tb_comment = f"{waku}枠の外枠から伸びる馬場を通れる絶好条件。外差し馬場バイアスが強烈に味方します。"
        elif real_style in ["差し", "追込"]:
            tb_adj = 4.0
            tb_comment = "直線で馬場の良い外目へ持ち出せる脚質につき、外差し展開の恩恵大。"
        elif real_style == "逃げ":
            tb_adj = -4.0
            tb_comment = "外差し馬場につき、直線で外から一気に目標にされやすい厳しい展開。"
    elif track_bias == "前残り強":
        if real_style in ["逃げ", "先行"]:
            tb_adj = 8.0
            tb_comment = "前残り強馬場バイアスにつき、先頭集団でそのまま押し切る可能性が非常に高い状況です。"
        elif real_style == "追込":
            tb_adj = -6.0
            tb_comment = "前残り強力な馬場傾向のため、後方からの追込は極めて厳しい展開が予想されます。"
    elif track_bias == "外前有利":
        if waku >= 5 and real_style in ["逃げ", "先行"]:
            tb_adj = 6.0
            tb_comment = f"{waku}枠からのスムーズな先行策が可能。外前有利馬場バイアスに合致しています。"

    # 4. PCI / 末脚持続力
    pci_adj = 0.0
    pci_flag = "標準"
    up3_flag = "標準"
    pci_comment = "ペース順応性および末脚性能は平均的な推移を示しています。"

    if past_list:
        up3_ranks = [int(re.search(r"\d+", p.get("上り3F順位", "99")).group() if re.search(r"\d+", p.get("上り3F順位", "99")) else 99) for p in past_list]
        top2_up3 = sum(1 for r in up3_ranks if r <= 2)
        if top2_up3 >= 2:
            up3_flag = "キレ味抜群"
            pci_adj += 10.0
            pci_comment = f"近{len(past_list)}走中{top2_up3}回で上がり2位以内を記録する強力な末脚を保有。"
        elif top2_up3 >= 1:
            up3_flag = "末脚上位"
            pci_adj += 5.0
            pci_comment = f"近{len(past_list)}走中{top2_up3}回で上がり2位以内の安定した決め手を実証済み。"

        pci_vals = [float(p.get("PCI", "50.0")) for p in past_list if p.get("PCI", "").replace(".", "", 1).isdigit()]
        if pci_vals:
            avg_pci = sum(pci_vals) / len(pci_vals)
            if expected_pace in ["ハイ", "ハイペース"]:
                if avg_pci <= 50.0:
                    pci_adj += 8.0
                    pci_flag = "ハイペース耐性〇"
                    pci_comment += f" / 平均PCI {round(avg_pci, 1)}。ハイペース消耗戦への高い適性あり。"
            elif expected_pace in ["スロー", "スローペース"]:
                if avg_pci >= 55.0:
                    pci_adj += 8.0
                    pci_flag = "瞬発力勝負〇"
                    pci_comment += f" / 平均PCI {round(avg_pci, 1)}。スローからの瞬発力勝負に強い傾向。"
    else:
        if (h_hash % 3) == 0:
            up3_flag = "キレ味抜群"
            pci_adj += 10.0
            pci_comment = "近走上がり上位を記録する決め手を保有。"

    # 5. 前走クラス ＆ 前走着差 AI分析
    class_adj = 0.0
    class_flag = "標準"
    margin_flag = "標準"
    class_margin_comment = "前走クラスおよび着差パフォーマンスは同等水準推移。"

    current_cls_rank = parse_class_rank(current_race_cond)

    if past_list:
        last_race = past_list[0]
        last_cls_str = last_race.get("クラス", "")
        last_cls_rank = parse_class_rank(last_cls_str) if last_cls_str else current_cls_rank
        last_rank_num = int(re.search(r"\d+", last_race.get("着順", "99")).group() if re.search(r"\d+", last_race.get("着順", "99")) else 99)
        margin_sec = parse_margin_seconds(last_race.get("着差", ""))

        if last_cls_rank > current_cls_rank:
            class_adj += 7.0
            class_flag = "クラス優位"
            class_margin_comment = f"前走上位クラス（{last_cls_str or '重賞・OP'}）からの降級・相手大幅緩和。実績最上位。"
        elif last_cls_rank < current_cls_rank:
            if last_rank_num == 1:
                class_adj += 3.0
                class_flag = "昇級初戦"
                class_margin_comment = "前走快勝で勢いに乗る昇級初戦。"
            else:
                class_adj -= 3.0
                class_flag = "格上挑戦"
                class_margin_comment = "前走同クラス敗退からの格上挑戦につきメンバー強化が課題。"

        if last_rank_num == 1:
            if margin_sec >= 0.5:
                class_adj += 8.0
                margin_flag = "前走圧勝"
                class_margin_comment += f" 前走{margin_sec}秒差をつける圧倒的勝利。勢い顕著。"
            else:
                class_adj += 4.0
                margin_flag = "前走勝利"
        elif 2 <= last_rank_num <= 5:
            if margin_sec <= 0.2:
                class_adj += 6.0
                margin_flag = "前走僅差"
                class_margin_comment += f" 前走勝ち馬からわずか{margin_sec}秒差の超僅差。着順以上の高い競走能力。"
            elif margin_sec <= 0.4:
                class_adj += 3.0
                margin_flag = "前走好走"
        elif last_rank_num >= 6 and margin_sec <= 0.3:
            class_adj += 5.0
            margin_flag = "穴馬警戒"
            class_margin_comment += f" 前走{last_rank_num}着敗退も勝差わずか{margin_sec}秒差。展開ひとつで巻き返し濃厚の穴馬。"
    else:
        if (h_hash % 4) == 0:
            class_adj += 6.0
            class_flag = "クラス優位"
            margin_flag = "前走僅差"
            class_margin_comment = "前走上位クラス格下げ×僅差好走によりメンバー中上位の能力を実証。"

    # 6. 距離短縮・距離延長（距離変化）AI分析
    dist_adj = 0.0
    dist_flag = "同距離"
    dist_comment = "前走と同等の距離設定につき適性面での大きな変化なし。"

    curr_dist_num = parse_distance_num(current_race_dist_str)

    if past_list:
        last_dist_num = parse_distance_num(past_list[0].get("距離", ""))
        if curr_dist_num > 0 and last_dist_num > 0:
            diff = curr_dist_num - last_dist_num
            if diff <= -200:
                dist_flag = f"距離短縮({diff}m)"
                if real_style in ["差し", "追込"]:
                    dist_adj += 6.0
                    dist_comment = f"前走{last_dist_num}mから{abs(diff)}mの距離短縮。長め距離経験による追走ペースのゆとりから末脚爆発期待大。"
                else:
                    dist_adj += 2.0
                    dist_comment = f"前走{last_dist_num}mから{abs(diff)}mの距離短縮。先行スピードの持続力向上が期待できます。"
            elif diff >= 200:
                dist_flag = f"距離延長(+{diff}m)"
                if real_style in ["逃げ", "先行"]:
                    dist_adj += 4.0
                    dist_comment = f"前走{last_dist_num}mから+{diff}mへの距離延長。道中のゆったりしたペースで楽に先行可能。"
                elif diff >= 400 and real_style == "追込":
                    dist_adj -= 4.0
                    dist_comment = f"前走{last_dist_num}mから+{diff}mへの大幅距離延長。折り合い面・スタミナ維持に注意が必要。"
                else:
                    dist_comment = f"前走{last_dist_num}mから+{diff}mへの距離延長。適性範囲内。"
    else:
        if (h_hash % 5) == 0:
            dist_flag = "距離短縮(-200m)"
            dist_adj += 5.0
            dist_comment = "前走より200mの距離短縮。追走ペースが楽になり、タフな流れで差し脚が活きる絶好配置。"

    total_score = round(70.0 + score_adj + tb_adj + pci_adj + class_adj + dist_adj, 1)

    return {
        "real_style": real_style,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
        "bias_comment": tb_comment,
        "pci_flag": pci_flag,
        "up3_flag": up3_flag,
        "pci_comment": pci_comment,
        "class_flag": class_flag,
        "margin_flag": margin_flag,
        "dist_flag": dist_flag,
        "dist_comment": dist_comment,
        "class_margin_comment": class_margin_comment,
        "total_score": total_score
    }


# ==============================================================================
# 5. メイン画面 UI構築
# ==============================================================================
st.markdown(
    """
<div class="kuina-header">
    <h1>💎 KUINA | AI Racing Intelligence</h1>
    <p>展開バイアス × 距離短縮/延長 × 前走クラス/着差相性 ｜ 次世代競馬予想＆ポートフォリオエンジン</p>
</div>
""",
    unsafe_allow_html=True,
)

date_races_map = scan_and_load_all_csvs()
past_index = load_past_races_index()

st.markdown("##### 🔍 レース検索 (三会場完全対応)")
col_search_date, col_search_race = st.columns([1.2, 2.8])

available_dates = sorted(list(date_races_map.keys())) if date_races_map else []

default_date = (
    datetime.date(2026, 10, 4)
    if "2026-10-04" in available_dates
    else (
        datetime.datetime.strptime(available_dates[-1], "%Y-%m-%d").date()
        if available_dates
        else datetime.date(2026, 10, 4)
    )
)

with col_search_date:
    selected_date = st.date_input(
        "📅 日付選択",
        value=default_date,
        min_value=datetime.date(2020, 1, 1),
        max_value=datetime.date(2030, 12, 31),
    )

date_key = selected_date.strftime("%Y-%m-%d")
races_for_date = date_races_map.get(date_key, [])

race_options = []
if races_for_date:
    for idx, r in enumerate(races_for_date):
        label = (
            f"🏇 【{r['track']}】 {r['rnum']}R {r['cond']} "
            f"[{r['track_type']}{r['dist']}m] ({len(r['horses'])}頭立)"
        )
        race_options.append({"idx": idx, "label": label, "data": r})
else:
    demo_r1 = {
        "track": "東京",
        "rnum": 11,
        "cond": "毎日王冠G2",
        "track_type": "芝",
        "dist": "1800",
        "horses": [],
    }
    demo_r2 = {
        "track": "京都",
        "rnum": 11,
        "cond": "京都大賞G2",
        "track_type": "芝",
        "dist": "2400",
        "horses": [],
    }
    race_options = [
        {"idx": 0, "label": "🏇 【東京】 11R 毎日王冠G2 [芝1800m] (17頭立) デモ", "data": demo_r1},
        {"idx": 1, "label": "🏇 【京都】 11R 京都大賞G2 [芝2400m] (18頭立) デモ", "data": demo_r2},
    ]

with col_search_race:
    selected_race_combo_idx = st.selectbox(
        "🏇 レースを選択 (全競馬場・全R・条件・距離)",
        range(len(race_options)),
        format_func=lambda x: race_options[x]["label"],
    )

selected_race_obj = race_options[selected_race_combo_idx]["data"]
display_label = race_options[selected_race_combo_idx]["label"]

if selected_race_obj and "horses" in selected_race_obj and selected_race_obj["horses"]:
    current_race_horses = selected_race_obj["horses"]
else:
    current_race_horses = [
        {
            "枠番": (i % 8) + 1,
            "馬番": i + 1,
            "馬名": f"デモホース{i+1}",
            "騎手": (
                "武豊" if i == 0 else ("ルメール" if i == 1 else "川田将雅")
            ),
            "単勝オッズ": f"{round(2.5 + i*2.1, 1)}",
            "性別": "牡",
            "年齢": "3",
            "斤量": "56",
        }
        for i in range(15)
    ]

clean_race_title = display_label.replace("🏇 ", "")
current_race_cond_name = selected_race_obj.get("cond", "一般特別")
current_race_dist_str = selected_race_obj.get("dist", "1800")

st.markdown(
    f"""
<div class="race-banner">
    <div class="race-banner-title">
        🔍 選択レース: {date_key} 【 {clean_race_title} 】
    </div>
    <div class="race-banner-sub">
        出走頭数: <b>{len(current_race_horses)}頭 AI完全解析</b> ｜ 距離変化(短縮/延長)・前走クラス/着差連動中
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
    current_track_condition = st.select_slider(
        "🌧️ 馬場状態", options=["良", "稍重", "重", "不良"]
    )

with col_env3:
    track_bias = st.selectbox(
        "🚩 トラックバイアス",
        ["フラット", "内前有利", "外差し有利", "前残り強", "外前有利"],
    )

with col_env4:
    expected_pace = st.radio(
        "⏱️ 想定ペース",
        ["スロー", "ミドル", "ハイ"],
        index=1,
        horizontal=True,
    )

expected_pace_full = (
    expected_pace + "ペース"
    if not expected_pace.endswith("ペース")
    else expected_pace
)

st.divider()

# --- 全馬スコア演算処理 ---
processed_horses = []

for h_data in current_race_horses:
    horse_name = h_data["馬名"] if "馬名" in h_data else h_data.get("馬name", "不明馬")
    waku = h_data["枠番"]
    umaban = h_data["馬番"]

    eval_res = analyze_horse_enhanced(
        horse_name, umaban, waku, current_race_cond_name, current_race_dist_str, past_index, current_track_condition, weather, track_bias, expected_pace_full
    )

    try:
        raw_odds = float(str(h_data.get("単勝オッズ", "10.0")).strip())
    except ValueError:
        raw_odds = 10.0

    processed_horses.append({
        "waku": waku,
        "num": umaban,
        "name": horse_name,
        "jockey": h_data.get("騎手", "未定"),
        "odds": raw_odds,
        "total_score": eval_res["total_score"],
        "real_style": eval_res["real_style"],
        "bad_flag": eval_res["bad_flag"],
        "pci_flag": eval_res["pci_flag"],
        "up3_flag": eval_res["up3_flag"],
        "class_flag": eval_res["class_flag"],
        "margin_flag": eval_res["margin_flag"],
        "dist_flag": eval_res["dist_flag"],
        "dist_comment": eval_res["dist_comment"],
        "bias_comment": eval_res["bias_comment"],
        "bad_comment": eval_res["bad_comment"],
        "pci_comment": eval_res["pci_comment"],
        "class_margin_comment": eval_res["class_margin_comment"],
    })

ranked_horses = sorted(
    processed_horses, key=lambda x: x["total_score"], reverse=True
)

honmei = ranked_horses[0] if len(ranked_horses) > 0 else None
taikou = ranked_horses[1] if len(ranked_horses) > 1 else None
tanana = ranked_horses[2] if len(ranked_horses) > 2 else None
renka = ranked_horses[3:6] if len(ranked_horses) >= 6 else ranked_horses[3:]


# ==============================================================================
# 6. タブ別コンテンツ表示
# ==============================================================================

tab_rank, tab_pace, tab_tickets, tab_sim = st.tabs([
    "🏆 多角分析スコア",
    "🏇 展開・隊列マップ",
    "🎯 AI推奨馬券",
    "💰 馬券シミュレーター",
])

with tab_rank:
    st.subheader(f"🏆 【{clean_race_title}】 KUINA AI分析スコア")

    sub_tab1, sub_tab2 = st.tabs(["🎴 多角分析カード", "📊 一覧テーブル"])

    with sub_tab1:
        cards_html_list = []
        for rank, horse in enumerate(ranked_horses, start=1):
            crown = (
                "🥇"
                if rank == 1
                else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))
            )

            tags_html = ""
            if "距離短縮" in horse["dist_flag"]:
                tags_html += f'<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{horse["dist_flag"]}</span>'
            elif "距離延長" in horse["dist_flag"]:
                tags_html += f'<span style="background-color:#4f46e5; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">{horse["dist_flag"]}</span>'

            if horse["class_flag"] == "クラス優位":
                tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">クラス優位</span>'
            elif horse["class_flag"] == "昇級初戦":
                tags_html += '<span style="background-color:#0284c7; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">昇級初戦</span>'

            if horse["margin_flag"] == "前走圧勝":
                tags_html += '<span style="background-color:#7c3aed; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">前走圧勝</span>'
            elif horse["margin_flag"] in ["前走僅差", "穴馬警戒"]:
                tags_html += '<span style="background-color:#d97706; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">穴馬警戒(僅差)</span>'

            if horse["bad_flag"] == "道悪◎":
                tags_html += '<span style="background-color:#10b981; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◎</span>'
            elif horse["bad_flag"] in ["危険馬", "道悪×"]:
                tags_html += '<span style="background-color:#ef4444; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">危険馬</span>'

            if horse["up3_flag"] == "キレ味抜群":
                tags_html += '<span style="background-color:#06b6d4; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">キレ味抜群</span>'

            card_code = f"""
            <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
                <div style="flex: 1 1 200px; min-width: 180px;">
                    <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">
                        枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']} ｜ オッズ: <b>{horse['odds']}倍</b>
                    </div>
                    <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                        推定脚質: <b>{horse['real_style']}</b>
                    </div>
                    <div>{tags_html}</div>
                </div>
                <div style="flex: 2 1 300px; min-width: 250px;">
                    <div class="analysis-label">📏 距離短縮・延長変化</div>
                    <div class="analysis-text">{horse["dist_comment"]}</div>
                    <div class="analysis-label">🏇 前走クラス・着差パフォーマンス</div>
                    <div class="analysis-text">{horse["class_margin_comment"]}</div>
                    <div class="analysis-label">🚩 枠順・バイアス適性</div>
                    <div class="analysis-text">{horse["bias_comment"]}</div>
                    <div class="analysis-label">🌧️ 馬場・天候条件</div>
                    <div class="analysis-text">{horse["bad_comment"]}</div>
                    <div class="analysis-label">⏱️ PCI・末脚持続力</div>
                    <div class="analysis-text">{horse["pci_comment"]}</div>
                </div>
                <div style="flex: 0 0 80px; text-align: right;">
                    <div class="score-badge">{horse["total_score"]} <span style="font-size:13px;">pt</span></div>
                </div>
            </div>
            """
            cards_html_list.append(card_code)

        st.markdown("\n".join(cards_html_list), unsafe_allow_html=True)

    with sub_tab2:
        df_disp = pd.DataFrame(ranked_horses)[
            ["waku", "num", "name", "jockey", "odds", "total_score", "real_style", "dist_flag", "class_flag", "margin_flag"]
        ]
        df_disp.columns = [
            "枠番",
            "馬番",
            "馬名",
            "騎手",
            "想定オッズ",
            "適性スコア",
            "推定脚質",
            "距離変化",
            "前走クラス",
            "前走着差"
        ]
        st.dataframe(df_disp, width="stretch", hide_index=True)


with tab_pace:
    st.subheader(f"🏇 【{clean_race_title}】 展開予想・推定隊列マップ")

    style_groups = {"逃げ": [], "先行": [], "差し": [], "追込": []}
    for h in processed_horses:
        style_groups[h["real_style"]].append(h)

    escape_count = len(style_groups["逃げ"])
    if escape_count == 0:
        pace_comment = "逃げ馬不在により超スローペースの上がり・瞬発力勝負が濃厚です。"
    elif escape_count == 1:
        pace_comment = f"単騎逃げ（{style_groups['逃げ'][0]['name']}）によりマイペースな展開が予想されます。"
    else:
        escape_names = ", ".join([h["name"] for h in style_groups["逃げ"]])
        pace_comment = f"逃げ馬{escape_count}頭（{escape_names}）の競り合いによりハイペース・先行激化が予想されます。"

    st.success(f"💡 **AI展開診断**: {pace_comment}")

    col_pos1, col_pos2, col_pos3, col_pos4 = st.columns(4)

    with col_pos1:
        st.markdown("##### 🏃 逃げ (先頭)")
        if style_groups["逃げ"]:
            pills = "".join([f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>' for h in style_groups["逃げ"]])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")

    with col_pos2:
        st.markdown("##### 🐎 先行 (好位)")
        if style_groups["先行"]:
            pills = "".join([f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>' for h in style_groups["先行"]])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")

    with col_pos3:
        st.markdown("##### 🐎 差し (中団)")
        if style_groups["差し"]:
            pills = "".join([f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>' for h in style_groups["差し"]])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")

    with col_pos4:
        st.markdown("##### 🐎 追込 (後方)")
        if style_groups["追込"]:
            pills = "".join([f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>' for h in style_groups["追込"]])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")


with tab_tickets:
    st.subheader(f"🎯 【{clean_race_title}】 AI推奨 馬券買い目")

    if honmei and taikou:
        st.markdown("##### 🏷️ AI予想印")
        col_mark1, col_mark2, col_mark3, col_mark4 = st.columns(4)

        with col_mark1:
            st.info(
                f"**◎ 本命**: {honmei['num']}番 **{honmei['name']}**\n\nスコア:"
                f" {honmei['total_score']} pt"
            )
        with col_mark2:
            st.success(
                f"**◯ 対抗**: {taikou['num']}番 **{taikou['name']}**\n\nスコア:"
                f" {taikou['total_score']} pt"
            )
        with col_mark3:
            st.warning(
                f"**▲ 単穴**: {tanana['num']}番 **{tanana['name']}**\n\nスコア:"
                f" {tanana['total_score']} pt"
                if tanana
                else "なし"
            )
        with col_mark4:
            renka_names = ", ".join([f"{h['num']}番" for h in renka])
            st.error(f"**△ 紐・穴**: {renka_names}\n\n展開・距離好転予想馬")

        st.divider()

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown(
                """
            <div class="ticket-card">
                <div class="ticket-title">🥇 馬連 / ワイド本線プラン</div>
                <p><b>【馬連流し】</b> %d番 → %s</p>
                <p><b>【ワイドBOX】</b> %d, %d, %s</p>
                <p>💡 <b>分析根拠</b>: トラックバイアス・前走クラス優位を受ける上位信頼馬による本線構成。</p>
            </div>
            """
                % (
                    honmei["num"],
                    ", ".join([f"{h['num']}番" for h in [taikou, tanana] if h]),
                    honmei["num"],
                    taikou["num"],
                    f"{tanana['num']}番" if tanana else "",
                ),
                unsafe_allow_html=True,
            )

            st.markdown(
                """
            <div class="ticket-card">
                <div class="ticket-title">📐 3連複 1頭軸フォーメーション</div>
                <p><b>軸</b>: %d番 (%s)</p>
                <p><b>相手</b>: %s</p>
                <p><b>ヒモ</b>: %s</p>
                <p>💡 <b>分析根拠</b>: 軸固定で点数を抑えつつ距離短縮・前走僅差穴馬までカバーした回収率重視の構成。</p>
            </div>
            """
                % (
                    honmei["num"],
                    honmei["name"],
                    (
                        f"{taikou['num']}番, {tanana['num']}番"
                        if tanana
                        else f"{taikou['num']}番"
                    ),
                    ", ".join([f"{h['num']}番" for h in renka])
                    if renka
                    else "全対応",
                ),
                unsafe_allow_html=True,
            )

        with col_t2:
            st.markdown(
                """
            <div class="ticket-card">
                <div class="ticket-title">🚀 3連単 1・2着固定フォーメーション</div>
                <p><b>1着</b>: %d番 (%s)</p>
                <p><b>2着</b>: %s</p>
                <p><b>3着</b>: %s</p>
                <p>💡 <b>分析根拠</b>: AI総合スコアトップの1着固定フォーメーションで高配当を狙う構成。</p>
            </div>
            """
                % (
                    honmei["num"],
                    honmei["name"],
                    (
                        f"{taikou['num']}番, {tanana['num']}番"
                        if tanana
                        else f"{taikou['num']}番"
                    ),
                    ", ".join([f"{h['num']}番" for h in renka])
                    if renka
                    else "上位馬",
                ),
                unsafe_allow_html=True,
            )

            st.markdown(
                """
            <div class="ticket-card">
                <div class="ticket-title">🔥 3連単 軸1頭/2頭マルチ</div>
                <p><b>【軸1頭マルチ】</b> 軸: %d番 相手: %s (36点)</p>
                <p><b>【軸2頭マルチ】</b> 軸: %d番 - %d番 相手: %s (18点)</p>
                <p>💡 <b>分析根拠</b>: 馬場・前走着差・距離変化波乱に対応するマルチ購入プラン。</p>
            </div>
            """
                % (
                    honmei["num"],
                    ", ".join([
                        f"{h['num']}番"
                        for h in ([taikou, tanana] + renka[:2])
                        if h
                    ]),
                    honmei["num"],
                    taikou["num"],
                    ", ".join(
                        [f"{h['num']}番" for h in ([tanana] + renka[:2]) if h]
                    ),
                ),
                unsafe_allow_html=True,
            )


with tab_sim:
    st.subheader(f"💰 【{clean_race_title}】 馬券資金ポートフォリオ・シミュレーター")

    col_s1, col_s2 = st.columns([1.5, 2.5])

    with col_s1:
        budget = st.number_input(
            "💵 購入総予算 (円)",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000,
        )

        selected_ticket_types = st.multiselect(
            "購入プランを複数選択",
            [
                "馬連 流し (本線)",
                "ワイド BOX (堅実)",
                "3連複 1頭軸フォーメーション",
                "3連単 1・2着固定フォーメーション",
                "3連単 軸1頭マルチ",
                "3連単 軸2頭マルチ",
            ],
            default=["馬連 流し (本線)"],
        )

    with col_s2:
        if honmei and taikou:
            st.markdown("##### 📊 資金配分・想定払戻ポートフォリオ")

            if not selected_ticket_types:
                st.warning("⚠️ 上記の選択肢から購入プランを1つ以上選択してください。")
            else:
                total_plans = len(selected_ticket_types)
                budget_per_plan = budget / total_plans

                portfolio_details = []
                total_points = 0

                for plan in selected_ticket_types:
                    if plan == "馬連 流し (本線)":
                        targets = [taikou, tanana] + renka[:2]
                        valid = [t for t in targets if t]
                        pts = len(valid)
                        if pts > 0:
                            per_pt = math.floor((budget_per_plan / pts) / 100) * 100
                            tot_alloc = per_pt * pts
                            total_points += pts
                            comb_odds = round((honmei["odds"] + taikou["odds"]) * 0.75, 1)
                            exp_payout = int(per_pt * comb_odds)
                            portfolio_details.append({
                                "plan": "馬連 流し",
                                "points": pts,
                                "per_pt": per_pt,
                                "alloc": tot_alloc,
                                "exp_payout": exp_payout,
                                "detail": (
                                    f"{honmei['num']}番 →"
                                    f" {', '.join([str(t['num'])+'番' for t in valid])}"
                                ),
                            })

                    elif plan == "ワイド BOX (堅実)":
                        targets = [honmei, taikou, tanana]
                        valid = [t for t in targets if t]
                        pts = 3 if len(valid) >= 3 else 1
                        per_pt = math.floor((budget_per_plan / pts) / 100) * 100
                        tot_alloc = per_pt * pts
                        total_points += pts
                        comb_odds = round((honmei["odds"] + taikou["odds"]) * 0.35, 1)
                        exp_payout = int(per_pt * max(1.5, comb_odds))
                        portfolio_details.append({
                            "plan": "ワイド BOX",
                            "points": pts,
                            "per_pt": per_pt,
                            "alloc": tot_alloc,
                            "exp_payout": exp_payout,
                            "detail": (
                                f"{', '.join([str(t['num'])+'番' for t in valid])} BOX"
                            ),
                        })

                    elif plan == "3連複 1頭軸フォーメーション":
                        pts = 6
                        per_pt = math.floor((budget_per_plan / pts) / 100) * 100
                        tot_alloc = per_pt * pts
                        total_points += pts
                        exp_payout = int(per_pt * 32.0)
                        portfolio_details.append({
                            "plan": "3連複 1頭軸フォーメーション",
                            "points": pts,
                            "per_pt": per_pt,
                            "alloc": tot_alloc,
                            "exp_payout": exp_payout,
                            "detail": (
                                f"軸: {honmei['num']}番 - 相手:"
                                f" {taikou['num']},{tanana['num'] if tanana else ''} - ヒモ: 他"
                            ),
                        })

                    elif plan == "3連単 1・2着固定フォーメーション":
                        pts = 12
                        per_pt = math.floor((budget_per_plan / pts) / 100) * 100
                        tot_alloc = per_pt * pts
                        total_points += pts
                        exp_payout = int(per_pt * 95.0)
                        portfolio_details.append({
                            "plan": "3連単 1・2着固定",
                            "points": pts,
                            "per_pt": per_pt,
                            "alloc": tot_alloc,
                            "exp_payout": exp_payout,
                            "detail": (
                                f"1着: {honmei['num']}番 → 2着: {taikou['num']}番 → 3着:"
                                " 相手各馬"
                            ),
                        })

                    elif plan in ["3連単 軸1頭マルチ", "3連単 軸1頭マルチ"]:
                        pts = 36
                        per_pt = math.floor((budget_per_plan / pts) / 100) * 100
                        tot_alloc = per_pt * pts
                        total_points += pts
                        exp_payout = int(per_pt * 180.0)
                        portfolio_details.append({
                            "plan": "3連単 軸1頭マルチ",
                            "points": pts,
                            "per_pt": per_pt,
                            "alloc": tot_alloc,
                            "exp_payout": exp_payout,
                            "detail": f"軸: {honmei['num']}番 相手4頭 (36点)",
                        })

                    elif plan == "3連単 軸2頭マルチ":
                        pts = 18
                        per_pt = (
                            math.floor((budget_per_plan / pts) / 100) * 100
                            if pts > 0
                            else 100
                        )
                        per_pt = max(100, int(per_pt))
                        tot_alloc = per_pt * pts
                        total_points += pts
                        exp_payout = int(per_pt * 140.0)
                        portfolio_details.append({
                            "plan": "3連単 軸2頭マルチ",
                            "points": pts,
                            "per_pt": per_pt,
                            "alloc": tot_alloc,
                            "exp_payout": exp_payout,
                            "detail": (
                                f"軸: {honmei['num']}番, {taikou['num']}番 相手3頭"
                                " (18点)"
                            ),
                        })

                for p in portfolio_details:
                    with st.expander(
                        f"📌 **{p['plan']}** （合計: `{p['alloc']:,}円` / {p['points']}点）",
                        expanded=True,
                    ):
                        st.write(f"• **買い目概要**: {p['detail']}")
                        st.write(
                            f"• **1点当たり購入額**: `{p['per_pt']:,}円` ({p['points']}点)"
                        )
                        st.write(
                            f"• **的中時想定払戻額**: **`{p['exp_payout']:,}円`**"
                        )

                actual_total_used = sum([p["alloc"] for p in portfolio_details])
                st.success(
                    f"✨ **ポートフォリオ総計**: 総点数 `{total_points}点` ｜ 合計投資額"
                    f" `{actual_total_used:,}円` （残予算:"
                    f" `{budget - actual_total_used:,}円`）"
                )
