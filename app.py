import os, glob, re, json, numpy as np, pandas as pd, streamlit as st
import matplotlib.pyplot as plt, matplotlib.patches as patches

st.set_page_config(page_title="KUINA AI | Racing Intelligence", page_icon="💎", layout="wide")

st.markdown("""<style>
.stApp { background: #f8fafc; font-family: -apple-system, sans-serif; }
.kuina-header { background: linear-gradient(135deg, #0f172a, #312e81); color: #fff; padding: 18px 20px; border-radius: 14px; margin-bottom: 16px; }
.kuina-header h1 { margin: 0; font-size: 24px; font-weight: 900; background: linear-gradient(to right, #fff, #a5f3fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.race-banner { background: #fff; border: 1px solid #e2e8f0; border-left: 6px solid #6366f1; padding: 14px 18px; border-radius: 12px; margin-bottom: 16px; }
.horse-card { background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; padding: 16px; margin-bottom: 12px; }
section[data-testid="stSidebar"] { display: none; }
.score-badge { font-size: 24px; font-weight: 900; color: #4f46e5; }
.analysis-label { font-weight: 800; color: #0f172a; font-size: 13px; margin-top: 6px; }
.analysis-text { color: #475569; font-size: 12px; margin-bottom: 4px; line-height: 1.4; }
.ticket-card { background: #fff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }
.ticket-title { font-size: 14px; font-weight: 800; color: #1e1b4b; display: flex; justify-content: space-between; }
.ticket-combo { font-size: 13px; font-weight: 700; color: #4338ca; background: #eef2ff; padding: 4px 8px; border-radius: 6px; margin-top: 4px; display: inline-block; }
</style>""", unsafe_allow_html=True)

def parse_distance_num(s):
    m = re.search(r"\d{3,4}", str(s or ""))
    return int(m.group()) if m else 0

def get_jra_waku(u, tot):
    if tot <= 8: return u
    caps, ext = [1] * 8, tot - 8
    for i in range(7, -1, -1):
        if ext > 0: caps[i] += 1; ext -= 1
    curr = 0
    for idx, c in enumerate(caps, start=1):
        if curr < u <= curr + c: return idx
        curr += c
    return 8

WAKU_COLOR_MAP = {
    1: ("#ffffff", "#000000"), 2: ("#1e293b", "#ffffff"), 3: ("#ef4444", "#ffffff"), 4: ("#3b82f6", "#ffffff"),
    5: ("#eab308", "#000000"), 6: ("#22c55e", "#ffffff"), 7: ("#f97316", "#ffffff"), 8: ("#ec4899", "#ffffff")
}

@st.cache_data(ttl=3600, show_spinner=False)
def scan_and_load_all_csvs():
    raw_files = sorted(list(set(glob.glob("./*.csv") + glob.glob("./*.CSV") + glob.glob("./data/*.csv") + glob.glob("/workspace/knowledge/*.csv"))))
    files = [f for f in raw_files if not any(k in os.path.basename(f) for k in ["枠番", "脚質", "過去走"])]
    date_races_map = {}
    for fpath in files:
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try: df = pd.read_csv(fpath, encoding=enc, header=None, dtype=str, on_bad_lines="skip"); break
            except Exception: pass
        if df is None or df.empty or len(df.columns) < 11: continue
        races = {}
        for row in df.values:
            if len(row) < 11: continue
            col0 = str(row[0]).strip().replace("-", "") if pd.notna(row[0]) else ""
            if not col0.isdigit(): continue
            d = f"20{col0[:2]}-{col0[2:4]}-{col0[4:6]}" if len(col0) == 6 else (f"{col0[:4]}-{col0[4:6]}-{col0[6:8]}" if len(col0) == 8 else "")
            if not d: continue
            tr, rn, u = str(row[1]).strip(), int(str(row[2]).strip()) if str(row[2]).strip().isdigit() else 1, int(str(row[3]).strip()) if str(row[3]).strip().isdigit() else 1
            cond, tt, dist = str(row[4]).strip(), str(row[5]).strip(), str(row[6]).strip()
            name, jock = str(row[7]).strip(), str(row[10]).strip() if len(row) > 10 and pd.notna(row[10]) else "未定"
            if not name: continue
            key = (d, tr, rn)
            if key not in races: races[key] = {"date": d, "track": tr, "rnum": rn, "cond": cond, "track_type": tt, "dist": dist, "horses": []}
            races[key]["horses"].append({"馬番": u, "馬名": name, "騎手": jock})
        for key, rdata in races.items():
            tot = len(rdata["horses"])
            for h in rdata["horses"]:
                if "枠番" not in h: h["枠番"] = get_jra_waku(h["馬番"], tot)
            d_str = rdata["date"]
            if d_str not in date_races_map: date_races_map[d_str] = []
            date_races_map[d_str].append(rdata)
    for d_str in date_races_map: date_races_map[d_str].sort(key=lambda x: (x["track"], x["rnum"]))
    return date_races_map

@st.cache_data(ttl=3600, show_spinner=False)
def load_past_races_index():
    past_files = glob.glob("./*過去走*.csv") + glob.glob("./data/*過去走*.csv") + glob.glob("/workspace/knowledge/*過去走*.csv")
    horse_past_map = {}
    for fpath in set(past_files):
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try: df = pd.read_csv(fpath, encoding=enc, dtype=str, on_bad_lines="skip"); break
            except Exception: pass
        if df is None or df.empty or "馬名" not in df.columns: continue
        for row in df.to_dict("records"):
            h = str(row.get("馬名", "")).strip()
            if not h: continue
            if h not in horse_past_map: horse_past_map[h] = []
            if len(horse_past_map[h]) < 5:
                horse_past_map[h].append({"通過1": str(row.get("通過1", "")), "馬場状態": str(row.get("馬場状態", "良")), "着順": str(row.get("着順", "99")), "距離": str(row.get("距離", "1800"))})
    return horse_past_map

BIAS_RULES = {
    "超イン伸び・最内ラチ有利": lambda w, s: (12.0, f" ➔ 【バイアス絶好】{w}枠最内×前行き。インベタで最高。") if w <= 2 and s in ["逃げ", "先行"] else ((6.0, f" ➔ 【バイアス良好】{w}枠最内コース通れる配置。") if w <= 2 else ((-8.0, f" ➔ 【バイアス大逆風】{w}枠外枠でインに入れず不利。") if w >= 7 else (0.0, ""))),
    "内伸び・内前有利": lambda w, s: (10.0, f" ➔ 【バイアス絶好】{w}枠×内前有利。先手奪取絶好。") if w <= 4 and s in ["逃げ", "先行"] else ((4.0, f" ➔ 【バイアス良好】内枠からロスなく追走。") if w <= 4 else ((-7.0, f" ➔ 【バイアス逆風】外枠×追込。内前有利に泣く。") if w >= 5 and s == "追込" else (0.0, ""))),
    "内前有利": lambda w, s: (10.0, f" ➔ 【バイアス絶好】{w}枠×内前有利。先手奪取絶好。") if w <= 4 and s in ["逃げ", "先行"] else ((4.0, f" ➔ 【バイアス良好】内枠からロスなく追走。") if w <= 4 else ((-7.0, f" ➔ 【バイアス逆風】外枠×追込。内前有利に泣く。") if w >= 5 and s == "追込" else (0.0, ""))),
    "外伸び・外差し有利": lambda w, s: (10.0, f" ➔ 【バイアス絶好】{w}枠×外差し。伸びる外目から一気。") if w >= 5 and s in ["差し", "追込"] else ((-6.0, f" ➔ 【バイアス逆風】最内枠×前行き。痛んだ内を通らされる。") if w <= 2 and s in ["逃げ", "先行"] else (0.0, "")),
    "外差し有利": lambda w, s: (10.0, f" ➔ 【バイアス絶好】{w}枠×外差し。伸びる外目から一気。") if w >= 5 and s in ["差し", "追込"] else ((-6.0, f" ➔ 【バイアス逆風】最内枠×前行き。痛んだ内を通らされる。") if w <= 2 and s in ["逃げ", "先行"] else (0.0, "")),
    "外前有利": lambda w, s: (10.0, f" ➔ 【バイアス絶好】{w}枠×外前展開。綺麗な外目から先行。") if w >= 5 and s in ["逃げ", "先行"] else ((-6.0, f" ➔ 【バイアス逆風】綺麗な外目を通った前目が止まらない。") if s in ["差し", "追込"] else (0.0, "")),
    "大外一気・外全振り": lambda w, s: (12.0, f" ➔ 【バイアス絶好】{w}枠×大外一気。最高の適合。") if w in [7, 8] and s in ["差し", "追込"] else ((-10.0, f" ➔ 【バイアス大逆風】最内×前行き。目標にされる展開。") if w <= 2 and s in ["逃げ", "先行"] else (0.0, "")),
    "超前残り・逃げ天国": lambda w, s: (12.0, " ➔ 【バイアス絶好】逃げ天国。そのまま押し切り濃厚。") if s == "逃げ" else ((7.0, " ➔ 【バイアス良好】好位前目で粘り込める。") if s == "先行" else ((-10.0, " ➔ 【バイアス大逆風】後方追込には絶望的。") if s == "追込" else (0.0, ""))),
    "前残り強": lambda w, s: (12.0, " ➔ 【バイアス絶好】逃げ天国。そのまま押し切り濃厚。") if s == "逃げ" else ((7.0, " ➔ 【バイアス良好】好位前目で粘り込める。") if s == "先行" else ((-10.0, " ➔ 【バイアス大逆風】後方追込には絶望的。") if s == "追込" else (0.0, ""))),
    "前崩れ・差し必至": lambda w, s: (12.0, " ➔ 【バイアス絶好】前崩れ展開で大外一気爆発。") if s == "追込" else ((8.0, " ➔ 【バイアス良好】バテた先行馬を一網打尽。") if s == "差し" else ((-10.0, " ➔ 【バイアス大逆風】ハイペース巻き込まれ直線失速。") if s == "逃げ" else (0.0, ""))),
    "超高速馬場（持ち時計重視）": lambda w, s: (8.0, " ➔ 【バイアス良好】超高速馬場×スピード持続力。") if s in ["逃げ", "先行"] else ((-5.0, " ➔ 【バイアス逆風】高速決着で追い出し遅れ懸念。") if s == "追込" else (0.0, "")),
    "タフ・スタミナ消耗馬場": lambda w, s: (8.0, " ➔ 【バイアス良好】スタミナ消耗戦。底力と末脚を発揮。") if s in ["差し", "追込"] else ((-6.0, " ➔ 【バイアス逆風】逃げ馬が最後バテるリスク。") if s == "逃げ" else (0.0, ""))
}

def analyze_horse_with_index(name, u, w, tot, cond, dist, tt, past_index, t_cond, weather, bias, pace):
    past_list = past_index.get(name, [])
    style = "先行"
    if past_list:
        p1 = [float(re.search(r"\d+", p["通過1"]).group()) for p in past_list if p.get("通過1") and re.search(r"\d+", str(p["通過1"]))]
        if p1:
            avg = sum(p1) / len(p1)
            style = "逃げ" if avg <= 2.0 else ("先行" if avg <= 5.0 else ("差し" if avg <= 10.0 else "追込"))
    else: style = ["逃げ", "先行", "差し", "追込"][(u * 3 + len(name)) % 4]

    bad_adj, bad_flag, bad_cmt = 0.0, "標準", ""
    wet_past = [p for p in past_list if p.get("馬場状態") in ["稍重", "重", "不良"]]
    is_wet = t_cond in ["稍重", "重", "不良"]

    if is_wet:
        if wet_past:
            best = min([int(re.search(r"\d+", p.get("着順", "99")).group()) for p in wet_past if re.search(r"\d+", p.get("着順", "99"))] or [99])
            if best <= 3: bad_adj, bad_flag, bad_cmt = 8.0, "道悪◎(好実績)", f"過去の道悪馬場で最高{best}着！タフ馬場適性は高く今回の{t_cond}は絶好。"
            elif best <= 5: bad_adj, bad_flag, bad_cmt = 4.0, "道悪◯", f"過去の道悪で掲示板（{best}着）獲得。崩れにくい重馬場適性を備えています。"
            else: bad_adj, bad_flag, bad_cmt = -5.0, "道悪不安", f"過去の道悪では凡走傾向（最高{best}着）。パフォーマンス低下に注意。"
        else:
            if style in ["逃げ", "先行"]: bad_adj, bad_flag, bad_cmt = 5.0, "道悪注意(前行き)", f"{t_cond}馬場×前行き脚質（{style}）により前残り有利展開に期待。"
            elif style == "追込": bad_adj, bad_flag, bad_cmt = -5.0, "道悪懸念(後方)", f"{t_cond}馬場で後方追込。前との差が縮まりにくく割引。"
            else: bad_cmt = f"{t_cond}馬場での走破実績はなく未知数。"
    else: bad_cmt = "良馬場開催につき、スピード・瞬発力をフルに発揮できる好条件です。"

    is_dirt = "ダ" in str(tt) or "ダート" in str(tt)
    if w in [1, 2]: w_adj, w_cmt = (-2.0, f"最内{w}枠。ダート戦のため砂被りリスクに注意。") if is_dirt else (3.0, f"絶好の{w}枠（内枠）。最短距離をロスなく立ち回れる経済コース。")
    elif w in [3, 4, 5, 6]: w_adj, w_cmt = 2.0, f"自在性の高い{w}枠（中枠）。ポジショニングしやすい好配置。"
    else: w_adj, w_cmt = (4.0, f"ダート好走黄金パターンの外{w}枠。砂被りを回避し進出可能。") if is_dirt else ((-3.0, f"多頭数外{w}枠。距離ロスの懸念あり。") if tot >= 15 else (0.0, f"外枠の{w}枠。スムーズに運べる反面距離ロスに注意。"))

    rule_fn = BIAS_RULES.get(bias)
    tb_adj, tb_cmt = rule_fn(w, style) if rule_fn else (0.0, " ➔ 【バイアス平穏】特定枠・脚質への偏りがないフラット馬場。")
    w_cmt += tb_cmt

    d_flag, d_cmt = "適性距離", "前走と同等の距離設定推移。"
    curr_d = parse_distance_num(dist)
    if past_list and len(past_list) > 0:
        last_d = parse_distance_num(past_list[0].get("距離", ""))
        if curr_d > 0 and last_d > 0:
            diff = curr_d - last_d
            if diff <= -200: d_flag, d_cmt = f"距離短縮({diff}m)", f"前走{last_d}mから{abs(diff)}m短縮。追走ペースが楽になり末脚爆発期待。"
            elif diff >= 200: d_flag, d_cmt = f"距離延長(+{diff}m)", f"前走{last_d}mから+{diff}m延長。ゆったりした追走が可能。"

    tot_score = round(70.0 + bad_adj + w_adj + tb_adj, 1)
    return {"real_style": style, "bad_flag": bad_flag, "bad_comment": bad_cmt, "waku_comment": w_cmt, "dist_flag": d_flag, "dist_comment": d_cmt, "total_score": tot_score}

def render_pace_map_graphic_advanced(processed_horses, race_title, track_type, track_bias):
    fig, ax = plt.subplots(figsize=(12, 4.8), dpi=150)
    is_dirt = "ダ" in str(track_type) or "ダート" in str(track_type)
    bg_dark, track_dark, lane_color = ('#381c0d', '#542d17', '#78350f') if is_dirt else ('#064e3b', '#0f766e', '#14b8a6')

    fig.patch.set_facecolor(bg_dark)
    ax.set_facecolor(track_dark)
    ax.axhline(0, color=lane_color, linewidth=1.5, linestyle='--')
    ax.axhline(1.5, color=lane_color, linewidth=1, linestyle=':')
    ax.axhline(-1.5, color=lane_color, linewidth=1, linestyle=':')

    ax.annotate("<- FINISH / GOAL", xy=(0.5, 2.3), xytext=(3.5, 2.3), arrowprops=dict(facecolor='#fef08a', edgecolor='#fef08a', width=2, headwidth=8), fontsize=11, fontweight='bold', color='#fef08a', ha='left')

    zones = [("NIGE (FRONT)", 0.3, 2.7, '#f87171'), ("SENKO (PACE)", 3.0, 5.7, '#fbbf24'), ("SASHI (MID)", 6.0, 8.7, '#34d399'), ("OIKOMI (BACK)", 9.0, 11.7, '#818cf8')]
    for ztitle, xmin, xmax, zcolor in zones:
        ax.add_patch(patches.Rectangle((xmin, -2.2), xmax - xmin, 4.2, linewidth=0, facecolor=zcolor, alpha=0.1))
        ax.text((xmin + xmax)/2, -2.0, ztitle, color=zcolor, fontsize=10, fontweight='bold', ha='center')

    hot_rects = []
    if any(k in track_bias for k in ["イン伸び", "内前", "超イン伸び"]): hot_rects.append((0.3, 5.7, 0.2, 1.8))
    elif any(k in track_bias for k in ["外差し", "外伸び", "大外一気"]): hot_rects.append((6.0, 11.7, -1.8, 1.8))
    elif any(k in track_bias for k in ["前残り", "逃げ天国", "外前", "超高速"]): hot_rects.append((0.3, 5.7, -1.8, 1.8))
    elif any(k in track_bias for k in ["前崩れ", "差し必至", "タフ"]): hot_rects.append((6.0, 11.7, -1.8, 1.8))

    for xmin, xmax, ymin, ymax in hot_rects:
        ax.add_patch(patches.FancyBboxPatch((xmin, ymin), xmax - xmin, ymax - ymin, boxstyle="round,pad=0.1,rounding_size=0.2", facecolor='#fbbf24', edgecolor='#fef08a', linewidth=2.5, alpha=0.35, zorder=2))

    style_x_offsets = {"逃げ": (0.6, 2.4), "先行": (3.3, 5.4), "差し": (6.3, 8.4), "追込": (9.3, 11.4)}
    style_counts = {"逃げ": 0, "先行": 0, "差し": 0, "追込": 0}

    for horse in processed_horses:
        style, waku, num = horse["real_style"], horse["waku"], horse["num"]
        bg_col, text_col = WAKU_COLOR_MAP.get(waku, ("#ffffff", "#000000"))
        xmin, xmax = style_x_offsets.get(style, (3.3, 5.4))
        cnt = style_counts[style]
        x_pos = xmin + (cnt % 2) * 1.1
        y_pos = 1.2 - (cnt // 2) * 0.9 if cnt < 4 else -1.2 + (cnt % 2) * 0.6
        style_counts[style] += 1
        ax.add_patch(patches.Circle((x_pos, y_pos), 0.38, facecolor=bg_col, edgecolor='#f8fafc', linewidth=1.8, zorder=4))
        ax.text(x_pos, y_pos, str(num), color=text_col, fontsize=12, fontweight='bold', ha='center', va='center', zorder=5)

    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(-2.5, 2.7)
    ax.axis('off')
    plt.tight_layout()
    return fig

# UI構築
st.markdown('<div class="kuina-header"><h1>💎 KUINA AI | Racing Intelligence System</h1></div>', unsafe_allow_html=True)

with st.spinner("データを読み込んでいます..."):
    date_races_map = scan_and_load_all_csvs()
    past_index = load_past_races_index()

available_dates = sorted(list(date_races_map.keys()))
st.markdown("##### レース選択")

if not available_dates:
    st.error("⚠️ 読み込める出走表CSVが見つかりません。")
    st.stop()

col_search_date, col_search_race = st.columns([1.2, 2.8])
with col_search_date:
    selected_date_str = st.selectbox("📅 開催日を選択", available_dates, index=len(available_dates) - 1)

races_for_date = date_races_map.get(selected_date_str, [])
race_options = [{"idx": idx, "label": f"【{r['track']}】 {r['rnum']}R {r['cond']} [{r['track_type']}{r['dist']}m] ({len(r['horses'])}頭立)", "data": r} for idx, r in enumerate(races_for_date)]

with col_search_race:
    selected_race_combo_idx = st.selectbox("🏇 レースを選択", range(len(race_options)), format_func=lambda x: race_options[x]["label"])

selected_race_obj = race_options[selected_race_combo_idx]["data"]
clean_race_title = race_options[selected_race_combo_idx]["label"]
current_race_horses = selected_race_obj["horses"]
current_race_cond_name = selected_race_obj.get("cond", "一般特別")
current_race_dist_str = selected_race_obj.get("dist", "1800")
current_track_type = selected_race_obj.get("track_type", "芝")

st.markdown(f'<div class="race-banner"><div class="race-banner-title">🔍 選択レース: {selected_date_str} 【 {clean_race_title} 】</div><div class="race-banner-sub">出走頭数: <b>{len(current_race_horses)}頭 AI完全解析</b></div></div>', unsafe_allow_html=True)

st.markdown("##### ⚙️ コンディション・バイアス設定")
col_env1, col_env2, col_env3, col_env4 = st.columns(4)
with col_env1: weather = st.selectbox("🌤️ 天気", ["晴", "曇", "雨", "雪"])
with col_env2: track_condition = st.select_slider("🌧️ 馬場状態", options=["良", "稍重", "重", "不良"])
with col_env3:
    track_bias = st.selectbox("🚩 トラックバイアス", ["フラット", "超イン伸び・最内ラチ有利", "内伸び・内前有利", "外伸び・外差し有利", "外前有利", "大外一気・外全振り", "超前残り・逃げ天国", "前崩れ・差し必至", "超高速馬場（持ち時計重視）", "タフ・スタミナ消耗馬場"])
with col_env4: expected_pace = st.radio("⏱️ 想定ペース", ["スロー", "ミドル", "ハイ"], index=1, horizontal=True)

st.divider()

processed_horses = []
tot_horses_count = len(current_race_horses)

for h_data in current_race_horses:
    horse_name, waku, umaban = h_data.get("馬名", "不明馬"), h_data["枠番"], h_data["馬番"]
    eval_res = analyze_horse_with_index(horse_name, umaban, waku, tot_horses_count, current_race_cond_name, current_race_dist_str, current_track_type, past_index, track_condition, weather, track_bias, expected_pace)
    processed_horses.append({"waku": waku, "num": umaban, "name": horse_name, "jockey": h_data.get("騎手", "未定"), "total_score": eval_res["total_score"], "real_style": eval_res["real_style"], "bad_flag": eval_res["bad_flag"], "bad_comment": eval_res["bad_comment"], "waku_comment": eval_res["waku_comment"], "dist_flag": eval_res["dist_flag"], "dist_comment": eval_res["dist_comment"]})

ranked_horses = sorted(processed_horses, key=lambda x: x["total_score"], reverse=True)
honmei = ranked_horses[0] if len(ranked_horses) > 0 else None
taikou = ranked_horses[1] if len(ranked_horses) > 1 else None
tanana = ranked_horses[2] if len(ranked_horses) > 2 else None
renka = ranked_horses[3:6] if len(ranked_horses) >= 6 else ranked_horses[3:]

tab_rank, tab_pace, tab_tickets = st.tabs(["🏆 AI分析スコア", "🏇 展開・隊列グラフィック", "🎯 AI推奨馬券"])

with tab_rank:
    st.subheader(f"🏆 【{clean_race_title}】 KUINA AI分析スコア")
    cards_html_list = []
    for rank, horse in enumerate(ranked_horses, start=1):
        crown = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))
        tags_html = ""
        if "距離短縮" in horse["dist_flag"]: tags_html += '<span style="background-color:#2563eb; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">距離短縮</span>'
        if "道悪◎" in horse["bad_flag"]: tags_html += '<span style="background-color:#059669; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◎(好実績)</span>'
        elif "道悪◯" in horse["bad_flag"]: tags_html += '<span style="background-color:#10b981; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪◯</span>'
        elif "道悪不安" in horse["bad_flag"] or "懸念" in horse["bad_flag"]: tags_html += '<span style="background-color:#dc2626; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; margin-right:4px; font-size:11px;">道悪割り引き</span>'

        card_code = f"""
        <div class="horse-card" style="display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div style="flex: 1 1 200px; min-width: 180px;">
                <h4 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 800; color: #1e1b4b;">{crown} {horse['name']}</h4>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">枠{horse['waku']} {horse['num']}番 ｜ 騎手: {horse['jockey']}</div>
                <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px;">想定脚質: <b>{horse['real_style']}</b></div>
                <div>{tags_html}</div>
            </div>
            <div style="flex: 2 1 300px; min-width: 250px;">
                <div class="analysis-label">🚩 枠順・展開配置評価</div>
                <div class="analysis-text">{horse["waku_comment"]}</div>
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
        item_html = f'<div style="display:inline-flex; align-items:center; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:5px 12px; margin:3px; font-size:13px; font-weight:700;"><span style="width:22px; height:22px; border-radius:50%; background-color:{bg_col}; color:{text_col}; display:inline-flex; align-items:center; justify-content:center; font-weight:900; font-size:11px; margin-right:8px; border:1px solid rgba(0,0,0,0.15);">{h["num"]}</span><span style="color:#1e1b4b;">{h["name"]}</span><span style="color:#64748b; font-size:11px; margin-left:6px;">({h["jockey"]})</span></div>'
        legend_html_list.append(item_html)
    st.markdown(f'<div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:8px;">{"".join(legend_html_list)}</div>', unsafe_allow_html=True)

with tab_tickets:
    st.subheader(f"🎯 【{clean_race_title}】 AI推奨 馬券フォーメーション")
    if honmei and taikou:
        col_mark1, col_mark2, col_mark3, col_mark4 = st.columns(4)
        with col_mark1: st.info(f"**◎ 本命**: {honmei['num']}番 **{honmei['name']}**\n\nスコア: {honmei['total_score']} pt")
        with col_mark2: st.success(f"**◯ 対抗**: {taikou['num']}番 **{taikou['name']}**\n\nスコア: {taikou['total_score']} pt")
        with col_mark3: st.warning(f"**▲ 単穴**: {tanana['num']}番 **{tanana['name']}**\n\nスコア: {tanana['total_score']} pt" if tanana else "なし")
        with col_mark4:
            renka_nums = [str(h['num']) for h in renka]
            st.error(f"**△ 紐・穴**: {', '.join([f'{n}番' for n in renka_nums])}\n\n展開好転予想馬")

        st.divider()
        st.markdown("##### 🎰 推奨馬券フォーメーション (全5種類)")
        h_num, t_num, a_num = str(honmei['num']), str(taikou['num']), str(tanana['num']) if tanana else ""
        r_nums = [str(h['num']) for h in renka]
        a_and_r = ([a_num] if a_num else []) + r_nums
        a_and_r_str = ", ".join(a_and_r)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown(f'<div class="ticket-card"><div class="ticket-title"><span>🤝 馬連 (1頭軸流し)</span><span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span></div><div>軸: <b>{h_num}番 ({honmei['name']})</b> ➔ 相手: {t_num}, {a_and_r_str}</div><div class="ticket-combo">買い目: {h_num} - {t_num}{", " + a_num if a_num else ""}{", " + ", ".join(r_nums) if r_nums else ""}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ticket-card"><div class="ticket-title"><span>🎯 馬単 (1着固定)</span><span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)+1} 点</span></div><div>1着: <b>{h_num}番 ({honmei['name']})</b> ➔ 2着: {t_num}, {a_and_r_str}</div><div class="ticket-combo">買い目: {h_num} ➔ {t_num}{", " + a_num if a_num else ""}{", " + ", ".join(r_nums) if r_nums else ""}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ticket-card"><div class="ticket-title"><span>💎 ワイド (上位人気・単穴BOX)</span><span style="font-size:12px; color:#6366f1;">推奨: 計 3 点</span></div><div>BOX: <b>{h_num}番, {t_num}番</b>{f", {a_num}番" if a_num else ""}</div><div class="ticket-combo">買い目: {h_num} - {t_num}{", " + a_num if a_num else ""}</div></div>', unsafe_allow_html=True)

        with col_t2:
            st.markdown(f'<div class="ticket-card"><div class="ticket-title"><span>🏆 3連複 (軸1頭ながし)</span><span style="font-size:12px; color:#6366f1;">推奨: 計 {len(a_and_r)*(len(a_and_r)+1)//2} 点</span></div><div>軸: <b>{h_num}番</b> ➔ 相手: {t_num}, {a_and_r_str}</div><div class="ticket-combo">買い目: {h_num} - {t_num} - {a_and_r_str}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ticket-card"><div class="ticket-title"><span>🔥 3連単 (フォーメーション)</span><span style="font-size:12px; color:#6366f1;">推奨高配当狙い</span></div><div>1着: <b>{h_num}番</b> ➔ 2着: {t_num}{f", {a_num}" if a_num else ""} ➔ 3着: {t_num}, {a_and_r_str}</div><div class="ticket-combo">買い目: {h_num} ➔ {t_num}{f", {a_num}" if a_num else ""} ➔ {t_num}, {a_and_r_str}</div></div>', unsafe_allow_html=True)
