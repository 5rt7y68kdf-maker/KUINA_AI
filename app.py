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
        margin-bottom: 16px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04);
        transition: all 0.2s ease-in-out;
    }
    .horse-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }
    section[data-testid="stSidebar"] {
        display: none;
    }
    .score-badge {
        font-size: 28px;
        font-weight: 900;
        color: #4f46e5;
    }
    .factor-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 10px;
        margin-top: 10px;
        background: #f8fafc;
        padding: 12px;
        border-radius: 12px;
        border: 1px solid #f1f5f9;
    }
    .factor-item {
        background: #ffffff;
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .factor-label {
        font-weight: 800;
        color: #1e293b;
        font-size: 12px;
        margin-bottom: 2px;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .factor-text {
        color: #475569;
        font-size: 12px;
        line-height: 1.45;
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
        .score-badge { font-size: 24px; text-align: left; margin-top: 8px; }
        .factor-grid { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. ユーティリティ ＆ 色判定
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
# 3. 高速JSON/CSVロード
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_races_and_index():
    json_candidates = ["races_data.json", "./scratch/races_data.json", "/workspace/scratch/races_data.json"]
    date_races_map = None
    for jpath in json_candidates:
        if os.path.exists(jpath):
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    date_races_map = json.load(f)
                    if date_races_map:
                        break
            except Exception:
                pass

    if not date_races_map:
        date_races_map = {}

    past_index_candidates = ["past_index.json", "./scratch/past_index.json", "/workspace/scratch/past_index.json"]
    past_index = {}
    for ppath in past_index_candidates:
        if os.path.exists(ppath):
            try:
                with open(ppath, "r", encoding="utf-8") as f:
                    past_index = json.load(f)
                    if past_index:
                        break
            except Exception:
                pass

    return date_races_map, past_index

# ==============================================================================
# 4. 全7大ファクター完全連動 AI解析エンジン
# ==============================================================================

def analyze_horse_7factors(
    h_data,
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
    waku = h_data.get("枠番", get_jra_waku(umaban, total_horses))
    jockey = h_data.get("騎手", "未定")
    kinryo = h_data.get("斤量", "56")

    sire = h_data.get("種牡馬", "")
    dam = h_data.get("母名", "")
    damsire = h_data.get("母父名", "")
    sire_type = h_data.get("父タイプ名", "")
    damsire_type = h_data.get("母父タイプ名", "")

    prev_rank = str(h_data.get("前着順", ""))
    prev_diff = float(h_data.get("前着差", 0.5))
    prev_class = str(h_data.get("前クラス", ""))
    prev_pop = float(h_data.get("前人気", 5.0))
    prev_style = str(h_data.get("前脚質", ""))
    prev_dist = str(h_data.get("前距離", ""))
    dist_diff = float(h_data.get("距離差", 0.0))
    interval = float(h_data.get("間隔", 4.0))
    kinryo_diff = float(h_data.get("斤量差", 0.0))

    past_list = past_index.get(horse_name, [])

    # --- 脚質判定 ---
    real_style = "先行"
    if prev_style:
        if "逃" in prev_style: real_style = "逃げ"
        elif "先" in prev_style: real_style = "先行"
        elif "中" in prev_style or "差" in prev_style: real_style = "差し"
        elif "後" in prev_style or "追" in prev_style: real_style = "追込"
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
    else:
        styles = ["逃げ", "先行", "差し", "追込"]
        real_style = styles[(umaban * 3 + len(horse_name)) % 4]

    # ==========================================
    # 7大ファクターの個別スコア＆コメント演算
    # ==========================================

    # FACTOR 1: 🧬 血統構成・系統相性
    ped_score = 0.0
    ped_comment = ""
    is_wet = current_track_condition in ["稍重", "重", "不良"]
    
    blood_text = f"父:{sire or '不明'} / 母父:{damsire or '不明'}"
    if sire_type or damsire_type:
        blood_text += f" ({sire_type}×{damsire_type})"
        
    roberto_sires = ["エピファネイア", "モーリス", "シンボリクリスエス", "スクリーンヒーロー", "グラスワンダー", "ロベルト"]
    duramente_sires = ["ドゥラメンテ", "ルーラーシップ", "キングカメハメハ", "ロードカナロア", "キングマンボ"]
    deep_sires = ["ディープインパクト", "キズナ", "コントレイル", "シルバーステート", "リアルスティール", "ハーツクライ", "スワーヴリチャード"]
    kitasan_sires = ["キタサンブラック", "ブラックタイド"]

    any_blood = sire + " " + damsire + " " + sire_type + " " + damsire_type

    if is_wet:
        if any(k in any_blood for k in roberto_sires + duramente_sires + ["ロベルト系", "キングマンボ系"]):
            ped_score += 6.0
            ped_comment = f"{blood_text} ➔ タフな馬場・重馬場に強いパワー血統。{current_track_condition}馬場での適性は極めて高く後押し。"
        elif any(k in any_blood for k in kitasan_sires + deep_sires):
            ped_score += 2.0
            ped_comment = f"{blood_text} ➔ 高いポテンシャルを持つ血統。パワーが必要な道悪馬場への対応が鍵。"
        else:
            ped_comment = f"{blood_text} ➔ 標準的な血統構成。展開・馬場適性の噛み合いに期待。"
    else:
        if any(k in any_blood for k in deep_sires + kitasan_sires + ["サンデーサイレンス系", "ディープインパクト系"]):
            ped_score += 6.0
            ped_comment = f"{blood_text} ➔ 直線の長いコースや良馬場で究極の切れ味（末脚）を発揮する瞬発力特化血統。"
        elif any(k in any_blood for k in duramente_sires):
            ped_score += 4.0
            ped_comment = f"{blood_text} ➔ スピードとパワーのバランスが優れた力強い血統構成。"
        else:
            ped_comment = f"{blood_text} ➔ 持続力と安定性を備えた血統バランス。"

    # FACTOR 2: 🏆 前走パフォーマンス・競走能力
    prev_score = 0.0
    prev_comment = ""
    
    if "1" in prev_rank or "１" in prev_rank:
        prev_score += 8.0
        prev_comment = f"前走1着と素晴らしい勝ち上がり。勢いそのままに好調をキープ。"
    elif any(k in prev_rank for k in ["2", "２", "3", "３"]):
        prev_score += 5.0
        prev_comment = f"前走{prev_rank}（勝ち馬と{prev_diff:.1f}秒差）と勝ち負けを演じた好走実績あり。勝機十分。"
    elif any(k in prev_rank for k in ["4", "４", "5", "５"]):
        prev_score += 2.0
        prev_comment = f"前走{prev_rank}で掲示板を確保。着差{prev_diff:.1f}秒差と展開ひとつで前転の伸び代あり。"
    else:
        if prev_diff <= 0.8:
            prev_score += 1.0
            prev_comment = f"前走は着順こそ{prev_rank}も、着差{prev_diff:.1f}秒差と悲観する内容ではない。"
        else:
            prev_score -= 3.0
            prev_comment = f"前走大敗（{prev_rank}・{prev_diff:.1f}秒差）。一変には展開や馬場の手助けが必要。"

    # FACTOR 3: 🏁 枠番・展開配置評価
    waku_score = 0.0
    waku_comment = ""
    is_dirt = "ダ" in str(current_track_type) or "ダート" in str(current_track_type)

    if waku in [1, 2]:
        if is_dirt:
            waku_score -= 2.0
            waku_comment = f"最内{waku}枠({umaban}番)。ダート戦のため揉まれた際の砂被りリスクに注意。"
        else:
            waku_score += 4.0
            waku_comment = f"絶好の{waku}枠({umaban}番)。インコースをロスなく立ち回れる経済コースの恩恵大。"
    elif waku in [3, 4, 5, 6]:
        waku_score += 2.0
        waku_comment = f"自在性の高い{waku}枠({umaban}番)。包まれるリスクが低くスムーズに運べる好配置。"
    else:
        if is_dirt:
            waku_score += 4.0
            waku_comment = f"ダート好走の黄金パターンである外{waku}枠({umaban}番)。砂被りを回避し外からスムーズ進出可能。"
        else:
            if total_horses >= 15:
                waku_score -= 3.0
                waku_comment = f"多頭数の外{waku}枠({umaban}番)。終始外を回らされる距離ロスのリスクあり。"
            else:
                waku_comment = f"外枠の{waku}枠({umaban}番)。被せられず運べる反面、コース取りに工夫が必要。"

    tb_adj = 0.0
    tb_text = ""
    if "イン伸び" in track_bias or "内前" in track_bias:
        if waku <= 4 and real_style in ["逃げ", "先行"]:
            tb_adj = 8.0
            tb_text = " 【バイアス絶好】内枠×前行きでインラチ独占展開。"
        elif waku >= 7:
            tb_adj = -6.0
            tb_text = " 【バイアス逆風】外枠につき内に入れず不利。"
    elif "外差し" in track_bias or "外伸び" in track_bias:
        if waku >= 5 and real_style in ["差し", "追込"]:
            tb_adj = 8.0
            tb_text = " 【バイアス絶好】外枠×外差し脚質で馬場良い大外進出。"
        elif waku <= 2:
            tb_adj = -5.0
            tb_text = " 【バイアス逆風】痛んだ内目通過の懸念。"
    elif "前残り" in track_bias or "逃げ天国" in track_bias:
        if real_style == "逃げ":
            tb_adj = 8.0
            tb_text = " 【バイアス絶好】前が止まらない逃げ天国。"
        elif real_style == "追込":
            tb_adj = -8.0
            tb_text = " 【バイアス大逆風】後方追込には厳しい前残り展開。"

    waku_full_comment = waku_comment + tb_text
    waku_score += tb_adj

    # FACTOR 4: 🌧️ 馬場適性・パワー評価
    bad_score = 0.0
    bad_flag = "標準"
    bad_comment = ""
    wet_past = [p for p in past_list if p.get("馬場状態") in ["稍重", "重", "不良"]]

    if is_wet:
        if wet_past:
            best_w = min([int(re.search(r"\d+", p.get("着順", "99")).group()) for p in wet_past if re.search(r"\d+", p.get("着順", "99"))] or [99])
            if best_w <= 3:
                bad_score += 8.0
                bad_flag = "道悪◎(好実績)"
                bad_comment = f"過去の道悪馬場で最高{best_w}着の好実績あり！{current_track_condition}馬場での適性は極めて高く大チャンス。"
            elif best_w <= 5:
                bad_score += 4.0
                bad_flag = "道悪◯"
                bad_comment = f"過去の道悪馬場で掲示板（{best_w}着）実績あり。パワー勝負に対応可能な底力。"
            else:
                bad_score -= 4.0
                bad_flag = "道悪不安"
                bad_comment = f"過去の道悪馬場で凡走傾向（最高{best_w}着）。馬場悪化による脚力削がれに懸念。"
        else:
            if real_style in ["逃げ", "先行"]:
                bad_score += 4.0
                bad_flag = "道悪注意(前行き)"
                bad_comment = f"道悪の実績は未知数も、前行き脚質（{real_style}）につき前残り展開の恩恵あり。"
            elif real_style == "追込":
                bad_score -= 4.0
                bad_flag = "道悪懸念(後方)"
                bad_comment = f"タフな{current_track_condition}馬場×後方追込。前との差が縮まりにくく割引き。"
            else:
                bad_comment = f"{current_track_condition}馬場での走破実績はなく未知数。血統・パワーでの対応力に注目。"
    else:
        bad_comment = "良馬場開催。持ち味のスピードとキレ味（上り性能）をフルに発揮できる好条件。"

    # FACTOR 5: 📏 距離推移・ペース適合
    dist_score = 0.0
    dist_flag = "適性距離"
    dist_comment = ""
    
    if dist_diff <= -150:
        dist_score += 4.0
        dist_flag = f"距離短縮({dist_diff:.0f}m)"
        dist_comment = f"前走から{abs(dist_diff):.0f}mの距離短縮。道中の追走ペースが楽になり終盤の末脚爆発期待。"
    elif dist_diff >= 150:
        dist_flag = f"距離延長(+{dist_diff:.0f}m)"
        dist_comment = f"前走から+{dist_diff:.0f}mの距離延長。道中で力まずゆったり折り合えるかがポイント。"
    else:
        dist_comment = f"前走（{prev_dist or current_race_dist_str}m）と同等の距離推移。行き脚・リズムを保ちやすい適性設定。"

    if expected_pace == "ハイ" and real_style in ["差し", "追込"]:
        dist_score += 4.0
        dist_comment += " ハイペース想定につき前崩れからの強襲に絶好の展開。"
    elif expected_pace == "スロー" and real_style in ["逃げ", "先行"]:
        dist_score += 4.0
        dist_comment += " スローペース想定につき前々のマイペース逃げ切り・粘り込み濃厚。"

    # FACTOR 6: ⚖️ 斤量・騎手相性
    jockey_score = 0.0
    jockey_comment = f"鞍上: {jockey}騎手 / 斤量: {kinryo}kg。"
    if kinryo_diff <= -1.0:
        jockey_score += 3.0
        jockey_comment += f" 前走比{kinryo_diff:.1f}kgの斤量減！軽量を活かした素早い反応・加速が魅力。"
    elif kinryo_diff >= 1.0:
        jockey_score -= 2.0
        jockey_comment += f" 前走比+{kinryo_diff:.1f}kgの斤量増。背負い慣れた重量かどうかが鍵。"
    else:
        jockey_comment += " 前走と同等の斤量設定で力配分・走量に変化なし。"

    # FACTOR 7: 🎯 総合勝負気配・オッズ期待値
    value_score = 0.0
    value_comment = ""
    if prev_pop <= 3.0 and not any(k in prev_rank for k in ["1", "１", "2", "２", "3", "３"]):
        value_score += 5.0
        value_comment = f"前走は上位人気（{prev_pop:.0f}番人気）に支持されながら大敗。能力は高くオッズが甘くなる今回は巻き返しの期待値（妙味）特大！"
    elif any(k in prev_rank for k in ["1", "１", "2", "２"]):
        value_score += 3.0
        value_comment = "近走充実度が非常に高く、連勝・連続連対の勢いそのままに首位争い有力。"
    else:
        value_comment = "展開やバイアスの助けがあれば一発上位浮上を狙える穴馬ポジション。"

    # トータルAIスコア計算
    total_score = round(65.0 + ped_score + prev_score + waku_score + bad_score + dist_score + jockey_score + value_score, 1)

    return {
        "real_style": real_style,
        "bad_flag": bad_flag,
        "dist_flag": dist_flag,
        "total_score": total_score,
        "factors": [
            {"icon": "🧬", "title": "血統構成・系統相性", "text": ped_comment},
            {"icon": "🏆", "title": "前走成績・競走能力", "text": prev_comment},
            {"icon": "🏁", "title": "枠順・展開配置", "text": waku_full_comment},
            {"icon": "🌧️", "title": "馬場適性・過去実績", "text": bad_comment},
            {"icon": "📏", "title": "距離推移・ペース適合", "text": dist_comment},
            {"icon": "⚖️", "title": "斤量・騎手相性", "text": jockey_comment},
            {"icon": "🎯", "title": "総合勝負気配・期待値", "text": value_comment},
        ]
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
        fontsize=11, fontweight='bold', color='#fef08a', ha='left'
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

with st.spinner("データを高速読み込み中..."):
    date_races_map, past_index = load_all_races_and_index()

available_dates = sorted(list(date_races_map.keys()))

st.markdown("##### レース選択")

if not available_dates:
    st.error("⚠️ 読み込めるレースデータ（races_data.json）が見つかりません。")
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
        出走頭数: <b>{len(current_race_horses)}頭 全7大AIファクター完全解析完了</b>
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

# --- 全7大ファクター AIスコア演算 ---
processed_horses = []
tot_horses_count = len(current_race_horses)

for h_data in current_race_horses:
    eval_res = analyze_horse_7factors(
        h_data,
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
        "waku": h_data.get("枠番", 1),
        "num": h_data.get("馬番", 1),
        "name": h_data.get("馬名", "不明"),
        "jockey": h_data.get("騎手", "未定"),
        "total_score": eval_res["total_score"],
        "real_style": eval_res["real_style"],
        "bad_flag": eval_res["bad_flag"],
        "dist_flag": eval_res["dist_flag"],
        "factors": eval_res["factors"],
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
    "🏆 全7大ファクター AI分析スコア",
    "🏇 展開・隊列グラフィック",
    "🎯 AI推奨馬券",
])

with tab_rank:
    st.subheader(f"🏆 【{clean_race_title}】 KUINA AI 全7大ファクター解析")

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

        factors_html_items = []
        for fitem in horse["factors"]:
            f_code = f"""
            <div class="factor-item">
                <div class="factor-label"><span>{fitem['icon']}</span> <span>{fitem['title']}</span></div>
                <div class="factor-text">{fitem['text']}</div>
            </div>
            """
            factors_html_items.append(f_code)

        factors_grid_html = f'<div class="factor-grid">{"".join(factors_html_items)}</div>'

        card_code = f"""
        <div class="horse-card">
            <div style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px;">
                <div>
                    <h4 style="margin: 0 0 4px 0; font-size: 20px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                    <div style="font-size: 13px; color: #64748b;">
                        枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']} ｜ 想定脚質: <b>{horse['real_style']}</b>
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
            st.info(f"**◎ 本命**: {honmei['num']}番 **{honmei['name']}** (スコア: {honmei['total_score']} pt)")
        with col_mark2:
            st.success(f"**◯ 対抗**: {taikou['num']}番 **{taikou['name']}** (スコア: {taikou['total_score']} pt)")
        with col_mark3:
            st.warning(f"**▲ 単穴**: {tanana['num']}番 **{tanana['name']}** (スコア: {tanana['total_score']} pt)" if tanana else "なし")
        with col_mark4:
            renka_nums = [str(h['num']) for h in renka]
            st.error(f"**△ 紐・穴**: {', '.join([f'{n}番' for n in renka_nums])}")

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
