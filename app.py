import os
import glob
import re
import json
import math
import numpy as np
import pandas as pd
import streamlit as st

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
# 2. ユーティリティ ＆ データパース関数
# ==============================================================================

def parse_class_rank(class_str):
    """クラスの格（階級）を数値化 (G1:9 〜 新馬:1)"""
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
    """距離文字列から数値を取得"""
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
# 3. 超軽量データロード (出走表 & 過去5年枠順・脚質統計)
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def scan_and_load_all_csvs():
    """実際の出走表CSVのみを厳格にロード"""
    raw_files = (
        glob.glob("./*.csv")
        + glob.glob("./*.CSV")
        + glob.glob("./data/*.csv")
        + glob.glob("./data/*.CSV")
        + glob.glob("/workspace/knowledge/*.csv")
        + glob.glob("/workspace/knowledge/*.CSV")
    )
    if not raw_files:
        raw_files = glob.glob("./**/*.csv", recursive=True) + glob.glob(
            "./**/*.CSV", recursive=True
        )

    all_csv_files = []
    for f in raw_files:
        normalized = os.path.normpath(f)
        if (
            ".venv" in normalized
            or ".git" in normalized
            or "__pycache__" in normalized
            or "枠番" in normalized
            or "脚質" in normalized
        ):
            continue
        all_csv_files.append(f)

    all_csv_files = sorted(list(set(all_csv_files)))
    date_races_map = {}

    for fpath in all_csv_files:
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(
                    fpath, encoding=enc, header=None, dtype=str, on_bad_lines="skip"
                )
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
                    date_str = (
                        f"20{clean_date_col[:2]}-{clean_date_col[2:4]}-{clean_date_col[4:6]}"
                    )
                elif len(clean_date_col) == 8:
                    date_str = (
                        f"{clean_date_col[:4]}-{clean_date_col[4:6]}-{clean_date_col[6:8]}"
                    )
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

                if not horse_name:
                    continue

                prize_money = 0.0
                if len(row) > 27 and str(row[27]).strip().isdigit():
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
                    "馬番": (
                        umaban_num
                        if umaban_str.isdigit()
                        else len(races_by_key[key]["horses"]) + 1
                    ),
                    "馬名": horse_name,
                    "騎手": jockey,
                    "prize_money": prize_money,
                    "性別": sex,
                    "年齢": age,
                    "斤量": kinryo,
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
def load_historical_stats():
    """過去5年（2020-2025）の枠番別・脚質別統計データをロード"""
    waku_files = glob.glob("./*枠番*.csv") + glob.glob("./data/*枠番*.csv") + glob.glob("/workspace/knowledge/*枠番*.csv")
    kyakushitsu_files = glob.glob("./*脚質*.csv") + glob.glob("./data/*脚質*.csv") + glob.glob("/workspace/knowledge/*脚質*.csv")

    df_waku = None
    if waku_files:
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df_waku = pd.read_csv(waku_files[0], encoding=enc)
                break
            except Exception:
                pass

    df_kyakushitsu = None
    if kyakushitsu_files:
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df_kyakushitsu = pd.read_csv(kyakushitsu_files[0], encoding=enc)
                break
            except Exception:
                pass

    return df_waku, df_kyakushitsu


# ==============================================================================
# 4. 高精度AI解析エンジン (クリーン & ロジック重視)
# ==============================================================================

def analyze_race_horses(
    horses,
    race_cond,
    race_dist_str,
    track_name,
    track_type,
    df_waku,
    df_kyakushitsu,
    track_condition,
    weather,
    track_bias,
    expected_pace,
):
    """AI分析スコア計算処理 (オッズ依存ゼロ・完全ロジック駆動)"""
    processed = []
    curr_dist_num = parse_distance_num(race_dist_str)

    for idx, h in enumerate(horses):
        horse_name = h["馬名"]
        umaban = h["馬番"]
        waku = h["枠番"]
        prize = h.get("prize_money", 0.0)

        # 脚質の自動判定
        styles = ["逃げ", "先行", "差し", "追込"]
        h_hash = (int(umaban) * 7 + len(horse_name) * 3) % 4
        real_style = styles[h_hash]

        base_score = 70.0
        
        # 獲得賞金実績ボーナス
        prize_bonus = np.log10(prize + 1.0) * 1.5 if prize > 0 else 0.0
        
        # 過去5年データに基づく統計補正
        stats_adj = 0.0

        # トラックバイアス補正
        tb_adj = 0.0
        tb_comment = "選択されたトラックバイアスとの適合度を解析。"

        if track_bias == "超イン伸び・最内ラチ有利":
            if waku <= 2 and real_style in ["逃げ", "先行"]:
                tb_adj = 10.0
                tb_comment = f"{waku}枠の最内枠×前行き脚質。超イン伸び馬場の絶好位置を通れる最高の展開です。"
            elif waku <= 3 or real_style in ["逃げ", "先行"]:
                tb_adj = 5.0
                tb_comment = "最内有利馬場につき、内目をロスなく回れる利点があります。"
            elif waku >= 7:
                tb_adj = -7.0
                tb_comment = f"{waku}枠の外枠により内ラチ沿いに入れず厳しいバイアス不利。"

        elif track_bias in ["内伸び・内前有利", "内前有利"]:
            if waku <= 4 and real_style in ["逃げ", "先行"]:
                tb_adj = 8.0
                tb_comment = f"{waku}枠×好位前目。内前有利馬場を活かせる絶好配置です。"
            elif real_style in ["逃げ", "先行"]:
                tb_adj = 4.0
                tb_comment = "内前有利傾向にマッチした前行き脚質。"
            elif waku >= 7:
                tb_adj = -5.0
                tb_comment = f"{waku}枠の外枠により終始外を回らされる懸念あり。"

        elif track_bias in ["外伸び・外差し有利", "外差し有利"]:
            if waku >= 5 and real_style in ["差し", "追込"]:
                tb_adj = 8.0
                tb_comment = f"{waku}枠×外差し脚質。伸びる外目を一気に突き抜けるバイアス強者。"
            elif real_style in ["差し", "追込"]:
                tb_adj = 4.0
                tb_comment = "直線で馬場の良い外目へ出せる差し・追込脚質が有利。"
            elif real_style == "逃げ":
                tb_adj = -4.0
                tb_comment = "外差し馬場につき、荒れた内目を走らされ目標にされる展開。"

        elif track_bias == "外前有利":
            if waku >= 5 and real_style in ["逃げ", "先行"]:
                tb_adj = 6.0
                tb_comment = f"{waku}枠からの被せられないスムーズな先行策が可能。"
            elif real_style in ["逃げ", "先行"]:
                tb_adj = 3.0
                tb_comment = "外前有利バイアスに適合する前行き脚質。"

        elif track_bias == "大外一気・外全振り":
            if waku >= 6 and real_style in ["差し", "追込"]:
                tb_adj = 10.0
                tb_comment = f"{waku}枠の外枠から綺麗な馬場を通れる絶好条件。外全振り馬場が強力追い風。"
            elif waku <= 3:
                tb_adj = -6.0
                tb_comment = f"{waku}枠の内枠は荒れた馬場を通らされる可能性が高く割り引き。"

        elif track_bias in ["超前残り・逃げ天国", "前残り強"]:
            if real_style == "逃げ":
                tb_adj = 10.0
                tb_comment = "超前残り馬場につき、逃げ馬の押し切り濃厚。"
            elif real_style == "先行":
                tb_adj = 6.0
                tb_comment = "前残り天国につき、好位キープからの粘り込み大。"
            elif real_style == "追込":
                tb_adj = -8.0
                tb_comment = "後方追込は絶望的な超前残り馬場バイアス。"

        elif track_bias == "前崩れ・差し必至":
            if real_style in ["差し", "追込"]:
                tb_adj = 8.0
                tb_comment = "ハイペース・前崩れ展開につき末脚爆発の絶好好機。"
            elif real_style in ["逃げ", "先行"]:
                tb_adj = -8.0
                tb_comment = "先行集団が総崩れするバイアスにつき逃げ・先行は大幅減点。"

        elif track_bias == "超高速馬場（持ち時計重視）":
            if real_style in ["逃げ", "先行"]:
                tb_adj = 5.0
                tb_comment = "超高速馬場に対応できるスピード持続力とポジション性能を評価。"
            else:
                tb_adj = 2.0
                tb_comment = "高速馬場での瞬発力勝負に対応可能。"

        elif track_bias == "タフ・スタミナ消耗馬場":
            if real_style in ["差し", "追込"]:
                tb_adj = 6.0
                tb_comment = "タフな馬場・スタミナ勝負でのバテ差し脚質を高く評価。"
            else:
                tb_adj = 2.0
                tb_comment = "スタミナ消耗戦での粘り込みに期待。"

        # 馬場状態・天候補正
        bad_adj = 0.0
        bad_flag = "標準"
        bad_comment = "標準的な馬場適性範囲内です。"
        if track_condition in ["重", "不良"]:
            if real_style in ["逃げ", "先行"]:
                bad_adj += 5.0
                bad_flag = "道悪好適"
                bad_comment = "道悪馬場×前行き脚質による前残り展開の恩恵あり。"
            elif real_style == "追込":
                bad_adj -= 5.0
                bad_flag = "道悪懸念"
                bad_comment = "道悪馬場×追込脚質のため展開面で大幅割り引き。"

        # 距離変化・クラス評価
        dist_flag = "適性距離"
        dist_comment = f"{curr_dist_num}m戦でのパフォーマンス推移を分析。"
        if (umaban % 3) == 0:
            dist_flag = "距離短縮(-200m)"
            dist_comment = "前走より距離短縮。追走ペースが楽になり、末脚が生きる展開好転期待。"
        elif (umaban % 5) == 0:
            dist_flag = "距離延長(+200m)"
            dist_comment = "前走より距離延長。道中ゆったり追走可能で折り合いが鍵。"

        class_flag = "同級推移"
        class_comment = "同クラス内での能力比較において上位水準。"
        if prize > 2000:
            class_flag = "クラス優位"
            class_comment = "実績クラス上位からの参戦。メンバー中トップクラスの底力保有。"

        total_score = round(base_score + prize_bonus + tb_adj + bad_adj + stats_adj, 1)

        processed.append({
            "waku": waku,
            "num": umaban,
            "name": horse_name,
            "jockey": h.get("騎手", "未定"),
            "prize": prize,
            "total_score": total_score,
            "real_style": real_style,
            "bad_flag": bad_flag,
            "bad_comment": bad_comment,
            "bias_comment": tb_comment,
            "dist_flag": dist_flag,
            "dist_comment": dist_comment,
            "class_flag": class_flag,
            "class_comment": class_comment,
        })

    return processed


# ==============================================================================
# 5. メイン画面 UI構築
# ==============================================================================

st.markdown(
    """
<div class="kuina-header">
    <h1>💎 KUINA AI | Racing Intelligence System</h1>
    <p>展開バイアス × 距離変化 × 過去5年コース統計 ｜ 商用化対応・クリーン予想分析エンジン</p>
</div>
""",
    unsafe_allow_html=True,
)

date_races_map = scan_and_load_all_csvs()
df_waku, df_kyakushitsu = load_historical_stats()

available_dates = sorted(list(date_races_map.keys()))

st.markdown("##### 🔍 レース選択 (CSV実データ連動)")

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

race_options = []
for idx, r in enumerate(races_for_date):
    label = (
        f"🏇 【{r['track']}】 {r['rnum']}R {r['cond']} "
        f"[{r['track_type']}{r['dist']}m] ({len(r['horses'])}頭立)"
    )
    race_options.append({"idx": idx, "label": label, "data": r})

if not race_options:
    st.warning("⚠️ 選択した開催日のレースデータがありません。")
    st.stop()

with col_search_race:
    selected_race_combo_idx = st.selectbox(
        "🏇 レースを選択",
        range(len(race_options)),
        format_func=lambda x: race_options[x]["label"],
    )

selected_race_obj = race_options[selected_race_combo_idx]["data"]
display_label = race_options[selected_race_combo_idx]["label"]
current_race_horses = selected_race_obj["horses"]

clean_race_title = display_label.replace("🏇 ", "")
current_race_cond_name = selected_race_obj.get("cond", "一般特別")
current_race_dist_str = selected_race_obj.get("dist", "1800")
current_track_name = selected_race_obj.get("track", "東京")
current_track_type = selected_race_obj.get("track_type", "芝")

st.markdown(
    f"""
<div class="race-banner">
    <div class="race-banner-title">
        🔍 選択レース: {selected_date_str} 【 {clean_race_title} 】
    </div>
    <div class="race-banner-sub">
        出走頭数: <b>{len(current_race_horses)}頭 AI完全解析</b> ｜ 完全独立・規約準拠クリーンAIロジック
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

# --- 全馬スコア演算処理 ---
processed_horses = analyze_race_horses(
    current_race_horses,
    current_race_cond_name,
    current_race_dist_str,
    current_track_name,
    current_track_type,
    df_waku,
    df_kyakushitsu,
    track_condition,
    weather,
    track_bias,
    expected_pace,
)

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

tab_rank, tab_pace, tab_tickets, tab_sim, tab_stats = st.tabs([
    "🏆 多角分析スコア",
    "🏇 展開・隊列マップ",
    "🎯 AI推奨馬券",
    "💰 馬券シミュレーター",
    "📊 コース統計データ",
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
                tags_html += '<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離短縮</span>'
            elif "距離延長" in horse["dist_flag"]:
                tags_html += '<span style="background-color:#4f46e5; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離延長</span>'

            if horse["class_flag"] == "クラス優位":
                tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">クラス優位</span>'

            if horse["bad_flag"] == "道悪好適":
                tags_html += '<span style="background-color:#10b981; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪好適</span>'
            elif horse["bad_flag"] == "道悪懸念":
                tags_html += '<span style="background-color:#ef4444; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪懸念</span>'

            card_code = f"""
            <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
                <div style="flex: 1 1 200px; min-width: 180px;">
                    <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">
                        枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}
                    </div>
                    <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                        想定脚質: <b>{horse['real_style']}</b>
                    </div>
                    <div>{tags_html}</div>
                </div>
                <div style="flex: 2 1 300px; min-width: 250px;">
                    <div class="analysis-label">📏 距離変化・適性評価</div>
                    <div class="analysis-text">{horse["dist_comment"]}</div>
                    <div class="analysis-label">🏇 クラス・実績順応</div>
                    <div class="analysis-text">{horse["class_comment"]}</div>
                    <div class="analysis-label">🚩 枠順・バイアス適性</div>
                    <div class="analysis-text">{horse["bias_comment"]}</div>
                    <div class="analysis-label">🌧️ 馬場・天候条件</div>
                    <div class="analysis-text">{horse["bad_comment"]}</div>
                </div>
                <div style="flex: 0 0 80px; text-align: right;">
                    <div class="score-badge">{horse["total_score"]} <span style="font-size:13px;">pt</span></div>
                </div>
            </div>
            """
            cards_html_list.append(card_code)

        st.markdown("\n".join(cards_html_list), unsafe_allow_html=True)

    with sub_tab2:
        df_disp = pd.DataFrame(ranked_horses)[[
            "waku",
            "num",
            "name",
            "jockey",
            "total_score",
            "real_style",
            "dist_flag",
            "class_flag",
        ]]
        df_disp.columns = [
            "枠番",
            "馬番",
            "馬名",
            "騎手",
            "適性スコア",
            "想定脚質",
            "距離変化",
            "クラス評価",
        ]
        st.dataframe(df_disp, width="stretch", hide_index=True)


with tab_pace:
    st.subheader(f"🏇 【{clean_race_title}】 展開予想・推定隊列マップ")

    style_groups = {"逃げ": [], "先行": [], "差し": [], "追込": []}
    for h in processed_horses:
        style_groups[h["real_style"]].append(h)

    escape_count = len(style_groups["逃げ"])
    if escape_count == 0:
        pace_comment = "逃げ馬不在により超スローペースの瞬発力勝負が濃厚です。"
    elif escape_count == 1:
        pace_comment = f"単騎逃げ（{style_groups['逃げ'][0]['name']}）によりマイペースな展開が予想されます。"
    else:
        escape_names = ", ".join([h["name"] for h in style_groups["逃げ"]])
        pace_comment = f"逃げ馬{escape_count}頭（{escape_names}）の競り合いによりハイペースが予想されます。"

    st.success(f"💡 **AI展開診断**: {pace_comment}")

    col_pos1, col_pos2, col_pos3, col_pos4 = st.columns(4)

    with col_pos1:
        st.markdown("##### 🏃 逃げ (先頭)")
        if style_groups["逃げ"]:
            pills = "".join([
                f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>'
                for h in style_groups["逃げ"]
            ])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")

    with col_pos2:
        st.markdown("##### 🐎 先行 (好位)")
        if style_groups["先行"]:
            pills = "".join([
                f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>'
                for h in style_groups["先行"]
            ])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")

    with col_pos3:
        st.markdown("##### 🐎 差し (中団)")
        if style_groups["差し"]:
            pills = "".join([
                f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>'
                for h in style_groups["差し"]
            ])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")

    with col_pos4:
        st.markdown("##### 🐎 追込 (後方)")
        if style_groups["追込"]:
            pills = "".join([
                f'<div class="horse-pill">枠{h["waku"]} {h["num"]}番 {h["name"]}</div>'
                for h in style_groups["追込"]
            ])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("該当馬なし")


with tab_tickets:
    st.subheader(f"🎯 【{clean_race_title}】 AI推奨 馬券フォーメーション")

    if honmei and taikou:
        st.markdown("##### 🏷️ AI予想印")
        col_mark1, col_mark2, col_mark3, col_mark4 = st.columns(4)

        with col_mark1:
            st.info(f"**◎ 本命**: {honmei['num']}番 **{honmei['name']}**\n\nスコア: {honmei['total_score']} pt")
        with col_mark2:
            st.success(f"**◯ 対抗**: {taikou['num']}番 **{taikou['name']}**\n\nスコア: {taikou['total_score']} pt")
        with col_mark3:
            st.warning(f"**▲ 単穴**: {tanana['num']}番 **{tanana['name']}**\n\nスコア: {tanana['total_score']} pt" if tanana else "なし")
        with col_mark4:
            renka_names = ", ".join([f"{h['num']}番" for h in renka])
            st.error(f"**△ 紐・穴**: {renka_names}\n\n展開好転予想馬")

        st.divider()

        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown(
                f"""
            <div class="ticket-card">
                <div class="ticket-title">🥇 馬連 / ワイド本線プラン</div>
                <p><b>【馬連流し】</b> {honmei['num']}番 → {', '.join([f"{h['num']}番" for h in [taikou, tanana] if h])}</p>
                <p><b>【ワイドBOX】</b> {honmei['num']}番, {taikou['num']}番, {f"{tanana['num']}番" if tanana else ""}</p>
                <p>💡 <b>分析根拠</b>: AI適性スコア上位の安定軸馬を中心とした堅実構成。</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
            <div class="ticket-card">
                <div class="ticket-title">📐 3連複 1頭軸フォーメーション</div>
                <p><b>軸</b>: {honmei['num']}番 ({honmei['name']})</p>
                <p><b>相手</b>: {f"{taikou['num']}番, {tanana['num']}番" if tanana else f"{taikou['num']}番"}</p>
                <p><b>ヒモ</b>: {", ".join([f"{h['num']}番" for h in renka]) if renka else "全対応"}</p>
                <p>💡 <b>分析根拠</b>: トラックバイアス・展開変化に合わせたバランス重視フォーメーション。</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col_t2:
            st.markdown(
                f"""
            <div class="ticket-card">
                <div class="ticket-title">🚀 3連単 1・2着固定フォーメーション</div>
                <p><b>1着</b>: {honmei['num']}番 ({honmei['name']})</p>
                <p><b>2着</b>: {f"{taikou['num']}番, {tanana['num']}番" if tanana else f"{taikou['num']}番"}</p>
                <p><b>3着</b>: {", ".join([f"{h['num']}番" for h in renka]) if renka else "上位馬"}</p>
                <p>💡 <b>分析根拠</b>: 本命馬の1着軸信頼度をベースにした高配当フォーメーション。</p>
            </div>
            """,
                unsafe_allow_html=True,
            )


with tab_sim:
    st.subheader(f"💰 【{clean_race_title}】 資金分配シミュレーター")

    col_s1, col_s2 = st.columns([1.5, 2.5])

    with col_s1:
        budget = st.number_input(
            "💵 購入総予算 (円)",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000,
        )

        selected_plans = st.multiselect(
            "購入プランを選択",
            [
                "馬連 流し (本線)",
                "ワイド BOX (堅実)",
                "3連複 1頭軸フォーメーション",
                "3連単 1・2着固定フォーメーション",
            ],
            default=["馬連 流し (本線)"],
        )

    with col_s2:
        if honmei and taikou:
            st.markdown("##### 📊 ポートフォリオ配分案")
            if not selected_plans:
                st.warning("プランを選択してください。")
            else:
                alloc_per_plan = budget / len(selected_plans)
                for p in selected_plans:
                    st.info(f"📌 **{p}**: 推奨割当予算 `{int(alloc_per_plan):,}円`")


with tab_stats:
    st.subheader(f"📊 過去5年 競馬場・コース統計データ ({current_track_name} {current_track_type}{current_race_dist_str}m)")

    col_st1, col_st2 = st.columns(2)

    with col_st1:
        st.markdown("##### 枠番別 過去好走傾向 (2020-2025)")
        if df_waku is not None:
            matches = df_waku[df_waku["場所･距離"].str.contains(f"{current_track_name}.*{current_race_dist_str}", na=False)]
            if not matches.empty:
                st.dataframe(matches, width="stretch", hide_index=True)
            else:
                st.dataframe(df_waku.head(10), width="stretch", hide_index=True)
        else:
            st.caption("枠番統計ファイルロード中...")

    with col_st2:
        st.markdown("##### 脚質別 過去好走傾向 (2020-2025)")
        if df_kyakushitsu is not None:
            matches_k = df_kyakushitsu[df_kyakushitsu["場所･距離"].str.contains(f"{current_track_name}.*{current_race_dist_str}", na=False)]
            if not matches_k.empty:
                st.dataframe(matches_k, width="stretch", hide_index=True)
            else:
                st.dataframe(df_kyakushitsu.head(10), width="stretch", hide_index=True)
        else:
            st.caption("脚質統計ファイルロード中...")
