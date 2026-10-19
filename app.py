import os
import glob
import re
import json
import math
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import textwrap

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
    .legal-box {
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 30px;
        font-size: 12px;
        color: #475569;
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
# 3. 高速インデックスロード ＆ 枠順・脚質過去統計
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_waku_and_style_stats():
    waku_files = glob.glob("./*枠番*.csv") + glob.glob("./data/*枠番*.csv") + glob.glob("/workspace/knowledge/*枠番*.csv")
    waku_map = {}
    for fpath in set(waku_files):
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass
        if df is not None and not df.empty and "場所･距離" in df.columns:
            for row in df.to_dict("records"):
                key = str(row.get("場所･距離", "")).strip()
                if not key:
                    continue
                if key not in waku_map:
                    waku_map[key] = {}
                for w in range(1, 9):
                    col_name = f"{['１','２','３','４','５','６','７','８'][w-1]}枠"
                    val_str = str(row.get(col_name, "0")).strip()
                    try:
                        val = float(val_str)
                    except Exception:
                        val = 0.0
                    waku_map[key][w] = waku_map[key].get(w, 0.0) + val
    return waku_map


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
    horse_all_history = {}

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

            waku_num = int(str(row[19]).strip()) if len(row) > 19 and str(row[19]).strip().isdigit() else 1
            rank_str = str(row[22]).strip() if len(row) > 22 and pd.notna(row[22]) else "99"
            rank = int(rank_str) if rank_str.isdigit() or (rank_str.startswith('-') and rank_str[1:].isdigit()) else 99
            
            diff_str = str(row[23]).strip() if len(row) > 23 and pd.notna(row[23]) else "0.5"
            try:
                diff = float(diff_str)
            except Exception:
                diff = 0.5

            pass1 = str(row[24]).strip() if len(row) > 24 and pd.notna(row[24]) else "0"
            agari_rank_str = str(row[31]).strip() if len(row) > 31 and pd.notna(row[31]) else "99"
            agari_rank = int(agari_rank_str) if agari_rank_str.isdigit() else 99

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
                "枠番": waku_num,
                "馬名": horse_name,
                "騎手": jockey,
                "Sire": sire,
                "DamSire": damsire,
                "prize_money": prize_money,
            })

            # 馬ごとの全履歴インデックスを生成
            if horse_name not in horse_all_history:
                horse_all_history[horse_name] = []
            
            horse_all_history[horse_name].append({
                "date": date_str,
                "track": track,
                "rnum": rnum,
                "cond": cond,
                "track_type": track_type,
                "dist": dist,
                "waku": waku_num,
                "umaban": umaban_num,
                "rank": rank,
                "diff": diff,
                "pass1": pass1,
                "agari_rank": agari_rank,
                "sire": sire,
                "damsire": damsire,
            })

        for key, rdata in races_by_key.items():
            tot = len(rdata["horses"])
            for h in rdata["horses"]:
                if h["枠番"] <= 0 or h["枠番"] > 8:
                    h["枠番"] = get_jra_waku(h["馬番"], tot)

            d_str = rdata["date"]
            if d_str not in date_races_map:
                date_races_map[d_str] = []
            date_races_map[d_str].append(rdata)

    for d_str in date_races_map:
        date_races_map[d_str] = sorted(
            date_races_map[d_str], key=lambda x: (x["track"], x["rnum"])
        )

    # 各馬の履歴を日付・レース番号で確実に降順ソート
    for h_name in horse_all_history:
        horse_all_history[h_name] = sorted(
            horse_all_history[h_name],
            key=lambda x: (x["date"], x["rnum"]),
            reverse=True
        )

    return date_races_map, horse_all_history


# ==============================================================================
# 4. 全12バイアス・ファクター完全連動 AI解析エンジン
# ==============================================================================

def analyze_horse_with_index(
    horse_name,
    umaban,
    waku,
    total_horses,
    current_race_cond,
    current_race_dist_str,
    current_track_type,
    horse_history,
    waku_stats_map,
    current_track_condition,
    weather,
    track_bias,
    expected_pace,
    current_date,
    current_rnum,
    current_track_name,
    sire="",
    damsire="",
):
    all_past = horse_history.get(horse_name, [])
    
    # 対象レースより【確実に過去のレース（日付・レース番号厳密フィルタ）】のみ抽出
    past_list = [
        r for r in all_past
        if (r["date"] < current_date) or (r["date"] == current_date and r["rnum"] < current_rnum)
    ]

    # 1. 脚質判定
    real_style = "先行"
    if past_list:
        pass1_vals = [
            float(re.search(r"\d+", str(p["pass1"])).group())
            for p in past_list if p.get("pass1") and re.search(r"\d+", str(p["pass1"]))
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

    # 2. 直近前走（1走前）パフォーマンス & 傾向評価
    last_race_adj = 0.0
    last_race_flag = ""
    last_race_comment = "前走データなし（昇級・新馬・休養明け）。"

    if past_list and len(past_list) > 0:
        last = past_list[0] # 厳密に直近1走前
        l_rank = last.get("rank", 99)
        l_diff = last.get("diff", 0.5)
        l_track = last.get("track_type", "")
        l_waku = last.get("waku", 4)
        l_pass1 = str(last.get("pass1", ""))

        if l_rank == 1:
            last_race_adj += 8.0
            last_race_flag = "前走1着(勝利)"
            last_race_comment = f"前走{last.get('track','')}【{l_track}{last.get('dist','')}m】で見事な1着勝利！絶好の勝負強さと勢いを維持。"
        elif l_rank in [2, 3] or (l_diff <= 0.3 and l_rank <= 5):
            last_race_adj += 5.0
            last_race_flag = "前走僅差好走"
            last_race_comment = f"前走{last.get('track','')}で{l_rank}着（勝ち馬と僅差{l_diff}s）の好内容。好調キープで上位争い必至。"
        else:
            last_race_comment = f"前走{last.get('track','')}で{l_rank}着からの巻き返しを狙う一戦。"

        # 直近（前走）の芝➔ダート替わり
        if ("芝" in l_track) and ("ダ" in str(current_track_type) or "ダート" in str(current_track_type)):
            last_race_adj += 5.0
            last_race_flag += " 直近芝➔ダート"
            last_race_comment += " ➔ 直近の前走芝から今回ダート替わり！砂適性発揮による一変激走に警戒。"

        # 前走ダート内枠好走
        if ("ダ" in l_track or "ダート" in l_track) and l_waku <= 2 and l_rank <= 3:
            last_race_adj += 5.0
            last_race_comment += " ➔ 前走ダート最内枠（1・2枠）から3着以内に好走。砂被り（キックバック）にも動じない勝負根性。"

        # 前走出遅れ
        if "出遅" in l_pass1 or (l_pass1.isdigit() and int(l_pass1) >= 14 and real_style in ["逃げ", "先行"]):
            last_race_adj -= 4.0
            last_race_comment += " ➔ 前走出遅れ（後手踏み）のリスクあり。スタートで後手に回らないかが鍵。"

    # 3. ⚡ 上がり3F末脚 & PCI分析
    agari_adj = 0.0
    agari_flag = ""
    agari_comment = ""
    
    agari_ranks = [r.get("agari_rank", 99) for r in past_list if r.get("agari_rank", 99) < 90]
    if agari_ranks:
        min_agari = min(agari_ranks)
        if min_agari == 1:
            agari_adj += 7.0
            agari_flag = "上がり最速◎"
            agari_comment = f"過去走でメンバー最速（上がり1位）の末脚を記録！直線での一括引き寄せ能力を保有。"
        elif min_agari <= 3:
            agari_adj += 4.0
            agari_flag = "上がり上位◯"
            agari_comment = f"過去走で上がり{min_agari}位の上位末脚を発揮。安定した追い込み脚を確保。"
        else:
            agari_comment = "上がり3F時計は平均的。早めのスパートや展開の助けが必要。"
    else:
        agari_comment = "上がり3Fデータ十分蓄積なし。先行力や立ち回りで補填期待。"

    # 展開（ハイペース・差しバイアス）とのシナジー
    if expected_pace == "ハイ" or track_bias in ["前崩れ・差し必至", "外伸び・外差し有利", "大外一気・外全振り"]:
        if (agari_ranks and min(agari_ranks) <= 3) or real_style in ["差し", "追込"]:
            agari_adj += 4.0
            agari_comment += " ➔ ハイペース/差し有利展開と末脚が合致！一気の捲り差しに好条件。"

    # 4. 🧬 血統背景・コース適性評価
    blood_adj = 0.0
    blood_flag = ""
    blood_comment = ""
    
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)
    curr_dist_num = parse_distance_num(current_race_dist_str)

    dirt_sires = ["オメガパフューム", "ヘニーヒューズ", "シニスターミニスター", "ゴールドアリュール", "マジェスティックウォリアー", "ドレフォン", "エスポワールシチー", "スマートボーイ", "カリフォルニアクローム", "パイロ", "マテラスカイ", "ルヴァンスレーヴ", "クリソベリル", "ダノンレジェンド", "ホッコータルマエ", "マインドユアビスケッツ"]
    turf_sires = ["ディープインパクト", "キズナ", "エピファネイア", "ロードカナロア", "ハーツクライ", "ルーラーシップ", "サートゥルナーリア", "モーリス", "ドゥラメンテ", "キタサンブラック", "コントレイル", "ダイワメジャー", "リアルスティール", "スワーヴリチャード", "ハービンジャー", "レイデオロ", "ブリックスアンドモルタル", "シルバーステート"]
    sprint_sires = ["サクラバクシンオー", "ビッグアーサー", "ロードカナロア", "ダノンプレシャス", "ミッキーアイル", "ファインニードル", "レッドファルクス"]

    full_blood_str = f"{sire} {damsire}"
    if is_dirt and any(k in full_blood_str for k in dirt_sires):
        blood_adj += 5.0
        blood_flag = "ダート血統◎"
        blood_comment = f"父: {sire if sire else '不明'} × 母父: {damsire if damsire else '不明'}。ダート特化のパワー＆砂被り耐久型血統。ダート戦で本領発揮。"
    elif not is_dirt and any(k in full_blood_str for k in turf_sires):
        blood_adj += 5.0
        blood_flag = "芝血統◎"
        blood_comment = f"父: {sire if sire else '不明'} × 母父: {damsire if damsire else '不明'}。芝での切れ味と高速適性に長けた王道芝血統。"
    elif curr_dist_num > 0 and curr_dist_num <= 1400 and any(k in full_blood_str for k in sprint_sires):
        blood_adj += 5.0
        blood_flag = "短距離血統◎"
        blood_comment = f"父: {sire if sire else '不明'} × 母父: {damsire if damsire else '不明'}。短距離スピードに特化した電撃スプリント血統。"
    else:
        blood_comment = f"父: {sire if sire else '標準'} / 母父: {damsire if damsire else '標準'}。標準的な血統バランスでコース不問の立ち回り。"

    # 5. 🌧️ 馬場適性評価
    bad_score_adj = 0.0
    bad_flag = "標準"
    bad_comment = ""

    wet_past_races = [p for p in past_list if p.get("cond") in ["稍重", "重", "不良"]]
    is_wet_track = current_track_condition in ["稍重", "重", "不良"]

    if is_wet_track:
        if wet_past_races:
            best_wet_finish = min([r.get("rank", 99) for r in wet_past_races] or [99])
            if best_wet_finish <= 3:
                bad_score_adj += 8.0
                bad_flag = "道悪◎(好実績)"
                bad_comment = f"過去の道悪馬場で最高{best_wet_finish}着の好実績あり！タフな{current_track_condition}馬場は絶好の勝機。"
            elif best_wet_finish <= 5:
                bad_score_adj += 4.0
                bad_flag = "道悪◯"
                bad_comment = f"過去の道悪馬場で掲示板（{best_wet_finish}着）獲得実績あり。崩れにくい重馬場適性を保有。"
            else:
                bad_score_adj -= 5.0
                bad_flag = "道悪割り引き"
                bad_comment = f"過去の道悪馬場では凡走傾向（最高{best_wet_finish}着）。馬場悪化による割引が必要。"
        else:
            if real_style in ["逃げ", "先行"]:
                bad_score_adj += 4.0
                bad_flag = "道悪注意(前行き)"
                bad_comment = f"道悪過去走は少ないですが、{current_track_condition}馬場×前行き脚質（{real_style}）により前残り有利の恩恵享受。"
            elif real_style == "追込":
                bad_score_adj -= 5.0
                bad_flag = "道悪割り引き"
                bad_comment = f"{current_track_condition}馬場で後方追込。水含み馬場で前との差が縮まりにくく苦戦懸念。"
            else:
                bad_comment = f"{current_track_condition}馬場での走破実績はなく未知数。"
    else:
        bad_comment = "良馬場開催につき、スピード・瞬発力をフルに発揮できる好条件です。"

    # 6. 🏟️ 競馬場・コース・距離別 枠順勝率評価
    waku_score_adj = 0.0
    waku_comment = ""
    
    # 新潟芝1000m直線の特記事項
    if "新潟" in current_track_name and "芝" in str(current_track_type) and curr_dist_num == 1000:
        if waku in [7, 8]:
            waku_score_adj += 8.0
            waku_comment = f"【新潟芝1000m特記】過去5年データで外枠（7・8枠）複勝率29.9%と圧倒的有利！最高の枠順配置です。"
        elif waku in [1, 2]:
            waku_score_adj -= 8.0
            waku_comment = f"【新潟芝1000m特記】過去5年データで最内（1・2枠）複勝率3.0%と大苦戦。内ラチ沿いの馬場傷みに泣く厳しい枠順。"
        else:
            waku_comment = f"新潟芝1000m中枠{waku}枠。スムーズに外目へ出せるかが好走の分岐点。"
    else:
        track_dist_key = f"{current_track_name}・{current_track_type}{curr_dist_num}m"
        stats_for_course = waku_stats_map.get(track_dist_key, {})
        if stats_for_course and waku in stats_for_course:
            w_val = stats_for_course[waku]
            avg_val = sum(stats_for_course.values()) / max(len(stats_for_course), 1)
            if w_val >= avg_val * 1.3:
                waku_score_adj += 4.0
                waku_comment = f"【{track_dist_key}枠データ】過去データで{waku}枠は好走率が高く、立ち回りやすい絶好ポジション。"
            elif w_val <= avg_val * 0.7:
                waku_score_adj -= 3.0
                waku_comment = f"【{track_dist_key}枠データ】過去データで{waku}枠は包まれやすく距離ロス等の割引傾向あり。"
            else:
                waku_comment = f"{waku}枠（{waku}枠配置）。展開に応じたポジション取りが期待できる標準枠順。"
        else:
            if waku in [1, 2]:
                if is_dirt:
                    waku_score_adj -= 2.0
                    waku_comment = f"最内{waku}枠。ダート戦のため被せられた際の砂被りリスクに注意が必要。"
                else:
                    waku_score_adj += 3.0
                    waku_comment = f"絶好の{waku}枠（内枠）。最短距離をロスなく立ち回れる経済コースの恩恵大。"
            elif waku in [3, 4, 5, 6]:
                waku_score_adj += 2.0
                waku_comment = f"自在性の高い{waku}枠（中枠）。包まれるリスクも低い好配置。"
            else:
                if is_dirt:
                    waku_score_adj += 4.0
                    waku_comment = f"ダート好走の黄金パターンである外{waku}枠。砂被りを回避しスムーズに外から進出可能。"
                else:
                    waku_comment = f"外枠の{waku}枠。外スムーズの反面、コーナーでの距離ロスには注意。"

    # 7. 🤖 トラックバイアス連動エンジン（全10パターン）
    tb_adj = 0.0
    tb_comment = "【バイアス適合】標準的なコースバイアス状態。"

    if track_bias == "超イン伸び・最内ラチ有利":
        if waku in [1, 2] and real_style in ["逃げ", "先行"]:
            tb_adj = 12.0
            tb_comment = f" ➔ 【バイアス絶好】{waku}枠の最内ラチ沿い×前行き脚質。最内を通れる最高の展開です。"
        elif waku in [1, 2]:
            tb_adj = 6.0
            tb_comment = f" ➔ 【バイアス良好】{waku}枠の最内枠。内目のグリーンベルトを通れる好位置。"
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
    elif track_bias in ["外伸び・外差し有利", "外差し有利"]:
        if waku >= 5 and real_style in ["差し", "追込"]:
            tb_adj = 10.0
            tb_comment = f" ➔ 【バイアス絶好】{waku}枠×外差し脚質。荒れた内を避けて一気に突き抜ける絶好機会。"
        elif waku <= 2 and real_style in ["逃げ", "先行"]:
            tb_adj = -6.0
            tb_comment = f" ➔ 【バイアス逆風】最内枠×逃げ・先行。痛んだ内目を通らされる懸念。"
    elif track_bias in ["超前残り・逃げ天国", "前残り強"]:
        if real_style == "逃げ":
            tb_adj = 12.0
            tb_comment = " ➔ 【バイアス絶好】逃げ天国馬場につき、マイペース逃げからの押し切り濃厚。"
        elif real_style == "追込":
            tb_adj = -10.0
            tb_comment = " ➔ 【バイアス大逆風】後方追込には絶望的な超前残りバイアス。"
    elif track_bias in ["前崩れ・差し必至"]:
        if real_style == "追込":
            tb_adj = 12.0
            tb_comment = " ➔ 【バイアス絶好】前崩れ確実の展開につき、直線大外一気での末脚爆発期待。"
        elif real_style == "逃げ":
            tb_adj = -10.0
            tb_comment = " ➔ 【バイアス大逆風】ハイペース巻き込まれで直線完全失速のリスク。"

    # 8. 📏 距離推移分析
    dist_flag = "適性距離"
    dist_comment = "前走と同等の距離設定推移。"

    if past_list and len(past_list) > 0:
        last_race = past_list[0]
        last_dist_num = parse_distance_num(last_race.get("dist", ""))
        if curr_dist_num > 0 and last_dist_num > 0:
            diff = curr_dist_num - last_dist_num
            if diff <= -200:
                dist_flag = f"距離短縮({diff}m)"
                dist_comment = f"前走{last_dist_num}mから{abs(diff)}mの距離短縮。追走ペースが楽になり末脚爆発の期待大。"
            elif diff >= 200:
                dist_flag = f"距離延長(+{diff}m)"
                dist_comment = f"前走{last_dist_num}mから+{diff}mへの距離延長。道中のゆったりした追走が可能。"

    total_score = round(70.0 + last_race_adj + bad_score_adj + waku_score_adj + tb_adj + agari_adj + blood_adj, 1)

    return {
        "real_style": real_style,
        "last_race_flag": last_race_flag,
        "last_race_comment": last_race_comment,
        "tb_comment": tb_comment,
        "agari_flag": agari_flag,
        "agari_comment": agari_comment,
        "blood_flag": blood_flag,
        "blood_comment": blood_comment,
        "bad_flag": bad_flag,
        "bad_comment": bad_comment,
        "waku_comment": waku_comment,
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

    # トラックバイアスのハイライトゾーン
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
    date_races_map, horse_history = scan_and_load_all_csvs()
    waku_stats_map = load_waku_and_style_stats()

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
current_rnum = selected_race_obj.get("rnum", 1)

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

st.markdown("##### 🤖 当日AIトラックバイアス解析ステータス")
st.info(f"選択中のトラックバイアス: **【{track_bias}】** ➔ 各出走馬の「枠順 × 脚質」に基づき、最大+12.0pt〜-10.0ptのリアルタイム加減点調整を自動適用しています。")

st.divider()

# --- インデックス参照型 全馬スコア演算 ---
processed_horses = []
tot_horses_count = len(current_race_horses)

for h_data in current_race_horses:
    horse_name = h_data.get("馬名", "不明馬")
    waku = h_data["枠番"]
    umaban = h_data["馬番"]
    sire = h_data.get("Sire", "")
    damsire = h_data.get("DamSire", "")

    eval_res = analyze_horse_with_index(
        horse_name=horse_name,
        umaban=umaban,
        waku=waku,
        total_horses=tot_horses_count,
        current_race_cond=current_race_cond_name,
        current_race_dist_str=current_race_dist_str,
        current_track_type=current_track_type,
        horse_history=horse_history,
        waku_stats_map=waku_stats_map,
        current_track_condition=track_condition,
        weather=weather,
        track_bias=track_bias,
        expected_pace=expected_pace,
        current_date=selected_date_str,
        current_rnum=current_rnum,
        current_track_name=current_track_name,
        sire=sire,
        damsire=damsire,
    )

    processed_horses.append({
        "waku": waku,
        "num": umaban,
        "name": horse_name,
        "jockey": h_data.get("騎手", "未定"),
        "sire": sire,
        "damsire": damsire,
        "total_score": eval_res["total_score"],
        "real_style": eval_res["real_style"],
        "last_race_flag": eval_res["last_race_flag"],
        "last_race_comment": eval_res["last_race_comment"],
        "tb_comment": eval_res["tb_comment"],
        "agari_flag": eval_res["agari_flag"],
        "agari_comment": eval_res["agari_comment"],
        "blood_flag": eval_res["blood_flag"],
        "blood_comment": eval_res["blood_comment"],
        "bad_flag": eval_res["bad_flag"],
        "bad_comment": eval_res["bad_comment"],
        "waku_comment": eval_res["waku_comment"],
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
        if "距離短縮" in horse["dist_flag"]:
            tags_html += '<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離短縮</span>'

        if "前走1着" in horse["last_race_flag"]:
            tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">前走1着(勝利)</span>'
        elif "僅差" in horse["last_race_flag"]:
            tags_html += '<span style="background-color:#0284c7; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">前走僅差好走</span>'

        if "芝➔ダート" in horse["last_race_flag"]:
            tags_html += '<span style="background-color:#d97706; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">直近芝➔ダート</span>'

        if "上がり最速" in horse["agari_flag"]:
            tags_html += '<span style="background-color:#7c3aed; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">上がり最速◎</span>'

        if "血統適性" in horse["blood_flag"] or "ダート血統" in horse["blood_flag"] or "芝血統" in horse["blood_flag"]:
            tags_html += '<span style="background-color:#4f46e5; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">血統適性◎</span>'

        if "道悪◎" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◎(好実績)</span>'
        elif "道悪割り引き" in horse["bad_flag"]:
            tags_html += '<span style="background-color:#dc2626; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪割り引き</span>'

        card_code = textwrap.dedent(f"""
        <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div style="flex: 1 1 220px; min-width: 180px;">
                <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">
                    枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}
                </div>
                <div style="font-size: 12px; color: #475569; margin-bottom: 6px;">
                    父: <b>{horse['sire'] if horse['sire'] else '不明'}</b> ｜ 母父: <b>{horse['damsire'] if horse['damsire'] else '不明'}</b>
                </div>
                <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                    想定脚質: <b>{horse['real_style']}</b>
                </div>
                <div style="margin-top: 6px;">{tags_html}</div>
            </div>
            <div style="flex: 2 1 300px; min-width: 250px;">
                <div class="analysis-label">🏁 直近前走パフォーマンス・傾向評価</div>
                <div class="analysis-text">{horse['last_race_comment']}</div>
                
                <div class="analysis-label">🤖 AIトラックバイアス適合判定</div>
                <div class="analysis-text">{horse['tb_comment']}</div>
                
                <div class="analysis-label">🚩 枠順・コース勝率配置評価</div>
                <div class="analysis-text">{horse['waku_comment']}</div>
                
                <div class="analysis-label">⚡ 上がり3F末脚・PCIペース分析</div>
                <div class="analysis-text">{horse['agari_comment']}</div>
                
                <div class="analysis-label">🧬 血統背景・コース適性評価</div>
                <div class="analysis-text">{horse['blood_comment']}</div>
                
                <div class="analysis-label">🌧️ 馬場適性・過去実績評価</div>
                <div class="analysis-text">{horse['bad_comment']}</div>
                
                <div class="analysis-label">📏 距離推移・展開分析</div>
                <div class="analysis-text">{horse['dist_comment']}</div>
            </div>
            <div style="flex: 0 0 80px; text-align: right;">
                <div class="score-badge">{horse['total_score']} <span style="font-size:13px;">pt</span></div>
            </div>
        </div>
        """)
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
        honmei_num = str(honmei['num'])
        honmei_name = str(honmei['name'])
        honmei_score = str(honmei['total_score'])
        
        taikou_num = str(taikou['num'])
        taikou_name = str(taikou['name'])
        taikou_score = str(taikou['total_score'])

        tanana_num = str(tanana['num']) if tanana else ""
        tanana_name = str(tanana['name']) if tanana else ""
        tanana_score = str(tanana['total_score']) if tanana else ""

        col_mark1, col_mark2, col_mark3, col_mark4 = st.columns(4)
        with col_mark1:
            st.info(f"**◎ 本命**: {honmei_num}番 **{honmei_name}**\n\nスコア: {honmei_score} pt")
        with col_mark2:
            st.success(f"**◯ 対抗**: {taikou_num}番 **{taikou_name}**\n\nスコア: {taikou_score} pt")
        with col_mark3:
            if tanana:
                st.warning(f"**▲ 単穴**: {tanana_num}番 **{tanana_name}**\n\nスコア: {tanana_score} pt")
            else:
                st.warning("**▲ 単穴**: なし")
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
                """),
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
                """),
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
                """),
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
                """),
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
                """),
                unsafe_allow_html=True
            )

# ==============================================================================
# 7. フッター（免責事項 ＆ お問い合わせ・プライバシーポリシー）
# ==============================================================================

st.markdown(
    textwrap.dedent("""
    <div class="legal-box">
        <h5 style="margin-top:0; font-weight:800; color:#1e1b4b;">🛡️ KUINA AI 免責事項・ご利用上の注意</h5>
        <p>1. 本サービス（KUINA AI）が提供する予想、分析スコア、隊列図および推奨馬券情報は、過去データおよび統計モデルに基づく機械学習AIによる自動シミュレーション結果であり、将来のレース結果や的中・収益を保証するものではありません。</p>
        <p>2. 馬券の購入および勝馬投票の最終決定は、利用者ご自身の判断と責任において行なってください。本サービスの利用により生じた直接的・間接的な損害や損失について、運営者は一切の責任を負いかねます。</p>
        <p>3. 競馬法により、20歳未満の者の勝馬投票券の購入および譲り受けは固く禁止されています。</p>
        <hr style="border:0; border-top:1px solid #cbd5e1; margin:12px 0;">
        <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <div><b>📩 お問い合わせ:</b> kuina.ai.keiba@gmail.com</div>
            <div><b>🔒 プライバシーポリシー:</b> 当サイトではGoogle AdSense等の第三者配信広告サービスおよびCookieを利用してコンテンツ表示の最適化を行なっています。</div>
        </div>
    </div>
    """),
    unsafe_allow_html=True
)
