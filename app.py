import math
import re
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. ページ基本設定 ＆ デザインCSS
# ==============================================================================
st.set_page_config(
    page_title="競馬AI純データ予想分析", page_icon="🐎", layout="wide"
)

# 全体デザインの微調整（カード枠線や背景色）
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. AI分析エンジン群（ロジック定義）
# ==============================================================================


# 【エンジン1】通過順から「真の脚質」を自動算出
def calculate_real_running_style(horse_past_df):
  """過去走データの通過1（1角通過順位）の加重平均から真の脚質を判定"""
  if horse_past_df is None or horse_past_df.empty:
    return "先行"  # デフォルト値

  recent_races = horse_past_df.head(4)
  weighted_positions = []
  weights = [0.40, 0.30, 0.20, 0.10]

  for idx, (_, row) in enumerate(recent_races.iterrows()):
    try:
      pass1_str = str(row.get("通過1", ""))
      pass1_match = re.search(r"\d+", pass1_str)
      if not pass1_match:
        continue
      pass1 = float(pass1_match.group())

      total_horses = float(row.get("頭数", 16))
      if pd.isna(total_horses) or total_horses <= 0:
        total_horses = 16.0

      position_rate = pass1 / total_horses
      weight = weights[idx] if idx < len(weights) else 0.10
      weighted_positions.append((pass1, position_rate, weight))
    except Exception:
      continue

  if not weighted_positions:
    return "先行"

  total_weight = sum(w for _, _, w in weighted_positions)
  avg_pass1 = sum(p1 * w for p1, _, w in weighted_positions) / total_weight
  avg_rate = sum(rate * w for _, rate, w in weighted_positions) / total_weight

  if avg_pass1 <= 1.5:
    return "逃げ"
  elif avg_rate <= 0.30 or avg_pass1 <= 4.5:
    return "先行"
  elif avg_rate <= 0.70:
    return "差し"
  else:
    return "追込"


# 【エンジン2】道悪適性（過去実績×前残りバイアス）判定
class BadTrackAnalyzer:

  def __init__(self):
    self.bad_conditions = ["稍重", "重", "不良"]
    self.heavy_conditions = ["重", "不良"]

  def evaluate_horse(
      self, horse_past_df, current_track_condition, real_style="標準"
  ):
    res = {
        "score_adjustment": 0.0,
        "status_flag": "標準",
        "comment": "標準的な馬場適性です。",
        "stats": {"total": 0, "top3": 0, "rate": 0.0},
    }

    if (
        not current_track_condition
        or current_track_condition == "良"
        or current_track_condition not in self.bad_conditions
    ):
      res["comment"] = "良馬場のため補正なし"
      return res

    if horse_past_df is not None and not horse_past_df.empty:
      if "馬場状態" in horse_past_df.columns and "着順" in horse_past_df.columns:
        bad_races = horse_past_df[
            horse_past_df["馬場状態"].astype(str).str.contains("稍重|重|不良")
        ]
        total_bad = len(bad_races)

        if total_bad > 0:
          ranks = (
              bad_races["着順"]
              .astype(str)
              .str.extract(r"(\d+)")
              .astype(float)
          )
          top3_count = (ranks <= 3).sum()
          place_rate = top3_count / total_bad
          res["stats"] = {
              "total": total_bad,
              "top3": int(top3_count),
              "rate": round(place_rate * 100, 1),
          }

          if total_bad >= 2:
            if place_rate >= 0.50:
              res["score_adjustment"] += 10.0
              res["status_flag"] = "道悪◎"
              res["comment"] = (
                  f"道悪得意（過去道悪複勝率 {round(place_rate*100)}%"
                  f" [{top3_count}/{total_bad}]）"
              )
            elif place_rate == 0.0:
              res["score_adjustment"] -= 10.0
              res["status_flag"] = "道悪×"
              res["comment"] = (
                  f"道悪不振（過去道悪 {total_bad}戦0複勝・苦手傾向）"
              )

    if current_track_condition in self.heavy_conditions:
      if real_style in ["逃げ", "先行"]:
        res["score_adjustment"] += 8.0
        if res["status_flag"] == "標準":
          res["status_flag"] = "前残り警戒"
          res["comment"] = (
              "重ババ×前行き脚質（前残り・粘り込み展開の恩恵あり）"
          )
        else:
          res["comment"] += " ＋ 重ババ前残り好位置"
      elif real_style == "追込":
        res["score_adjustment"] -= 6.0
        if res["status_flag"] == "標準":
          res["status_flag"] = "危険馬"
          res["comment"] = (
              "重ババ×追込脚質（馬場悪化により差し届かないリスクあり）"
          )
        else:
          res["comment"] += "（※追込脚質のため展開注意）"

    return res


# 【エンジン3】PCI（ペースチェンジ）＆上がり3F（末脚絶対値）解析
class PciUp3Analyzer:

  def evaluate_horse(self, horse_past_df, expected_pace="ミドルペース"):
    res = {
        "score_adjustment": 0.0,
        "pci_flag": "標準",
        "up3_flag": "標準",
        "comment": "",
    }
    if horse_past_df is None or horse_past_df.empty:
      return res

    recent = horse_past_df.head(5)
    top_up3_count = 0

    if "上り3F順位" in recent.columns:
      for _, row in recent.iterrows():
        try:
          match = re.search(r"\d+", str(row.get("上り3F順位", "")))
          if match and int(match.group()) <= 2:
            top_up3_count += 1
        except Exception:
          continue

    up3_comment = ""
    if top_up3_count >= 3:
      res["score_adjustment"] += 10.0
      res["up3_flag"] = "キレ味抜群"
      up3_comment = (
          f"近{len(recent)}走中{top_up3_count}回で上がり2位以内の強力な末脚"
      )
    elif top_up3_count >= 2:
      res["score_adjustment"] += 5.0
      res["up3_flag"] = "末脚上位"
      up3_comment = (
          f"安定した末脚（近{len(recent)}走で上がり2位以内{top_up3_count}回）"
      )

    pci_comments = []
    if "PCI" in recent.columns and "着順" in recent.columns:
      pci_list = []
      for _, row in recent.iterrows():
        try:
          val = float(str(row.get("PCI", "")).strip())
          if 30.0 <= val <= 80.0:
            pci_list.append(val)
        except Exception:
          continue

      if pci_list:
        avg_pci = sum(pci_list) / len(pci_list)
        if expected_pace == "ハイペース":
          if avg_pci <= 50.0:
            res["score_adjustment"] += 8.0
            res["pci_flag"] = "ハイペース耐性〇"
            pci_comments.append(
                f"ハイペース消耗戦に強み（PCI平均 {round(avg_pci, 1)}）"
            )
          elif avg_pci >= 58.0:
            res["score_adjustment"] -= 6.0
            res["pci_flag"] = "ハイペース懸念"
            pci_comments.append(
                f"スロー粘り型のため激流追走に懸念（PCI平均 {round(avg_pci, 1)}）"
            )
        elif expected_pace == "スローペース":
          if avg_pci >= 55.0:
            res["score_adjustment"] += 8.0
            res["pci_flag"] = "瞬発力勝負〇"
            pci_comments.append(
                f"上がり勝負・瞬発力戦に強い（PCI平均 {round(avg_pci, 1)}）"
            )

    all_c = [c for c in [up3_comment] + pci_comments if c]
    res["comment"] = " / ".join(all_c) if all_c else "ペース・末脚は標準適性"
    return res


# 【エンジン4】コース適性・距離変更・ローテーション解析
class CourseRotationAnalyzer:

  def evaluate_horse(
      self, horse_past_df, current_course, current_distance, real_style="標準"
  ):
    res = {
        "score_adjustment": 0.0,
        "course_flag": "標準",
        "rotation_flag": "順調",
        "comment": "",
    }
    if horse_past_df is None or horse_past_df.empty:
      return res

    comments = []
    last_race = horse_past_df.iloc if len(horse_past_df) > 0 else None

    # 同近接距離実績
    if "距離" in horse_past_df.columns and "着順" in horse_past_df.columns:
      horse_past_df["num_dist"] = (
          horse_past_df["距離"]
          .astype(str)
          .str.extract(r"(\d+)")
          .astype(float)
      )
      same_dist = horse_past_df[
          abs(horse_past_df["num_dist"] - current_distance) <= 100
      ]
      if len(same_dist) >= 2:
        top3 = (
            same_dist["着順"].astype(str).str.extract(r"(\d+)").astype(float) <= 3
        ).sum()
        rate = top3 / len(same_dist)
        if rate >= 0.50:
          res["score_adjustment"] += 8.0
          res["course_flag"] = "距離適性〇"
          comments.append(f"同近接距離で高適性（複勝率 {round(rate*100)}%）")

    # ローテーション（久々・馬体重増）
    if last_race is not None:
      interval_match = re.search(r"\d+", str(last_race.get("間隔", "")))
      weight_match = re.search(r"([+-]?\d+)", str(last_race.get("馬体重増減", "")))

      interval_weeks = (
          int(interval_match.group()) if interval_match else None
      )
      weight_diff = int(weight_match.group(1)) if weight_match else None

      if (
          interval_weeks
          and interval_weeks >= 10
          and weight_diff
          and weight_diff >= 12
      ):
        res["score_adjustment"] -= 8.0
        res["rotation_flag"] = "危険（仕上がり途上）"
        comments.append(
            f"長期休養明け（中{interval_weeks}週）＋馬体重太め（{weight_diff:+d}kg）で割引"
        )

    res["comment"] = " / ".join(comments) if comments else "順調なローテーション"
    return res


# ==============================================================================
# 3. Streamlit メインUI画面
# ==============================================================================

st.title("🐎 競馬AI 純データ展開・適性分析ダッシュボード")
st.caption(
    "オッズ・人気に頼らない「枠順バイアス×真の脚質×馬場適性×ペースチェンジ」総合スコアモデル"
)

# --- サイドバー操作パネル ---
with st.sidebar:
  st.header("⚙️ レース条件設定")

  current_course = st.selectbox(
      "コース場名・芝ダ",
      ["東京芝", "中山芝", "阪神芝", "京都芝", "東京ダート", "阪神ダート"],
  )
  current_distance = st.number_input(
      "距離 (m)", min_value=1000, max_value=3600, value=1800, step=100
  )
  current_track_condition = st.select_slider(
      "当日の馬場状態", options=["良", "稍重", "重", "不良"]
  )
  expected_pace = st.radio(
      "想定レースペース",
      ["スローペース", "ミドルペース", "ハイペース"],
      index=1,
      horizontal=True,
  )

  st.divider()
  st.info("💡 設定条件に応じてリアルタイムで適性スコアが再計算されます。")

# --- インスタンス生成 ---
bad_analyzer = BadTrackAnalyzer()
pci_analyzer = PciUp3Analyzer()
rotation_analyzer = CourseRotationAnalyzer()

# --- デモ用出走馬データ（※修正済み） ---
demo_horses = [
    {
        "num": 1,
        "name": "アークライト",
        "style_default": "逃げ",
        "past_data": pd.DataFrame({
            "通過1": ["01", "01", "02"],
            "頭数": [16, 16, 16],
            "馬場状態": ["重", "良", "稍重"],
            "着順": ["1", "2", "1"],
            "上り3F順位": ["2", "4", "1"],
            "PCI": [48.5, 52.0, 49.0],
            "距離": [1800, 1800, 1800],
            "間隔": ["中4週", "中8週", "中3週"],
            "馬体重増減": ["+2", "+4", "0"],
        }),
    },
    {
        "num": 2,
        "name": "ディアファザー",
        "style_default": "差し",
        "past_data": pd.DataFrame({
            "通過1": ["08", "10", "09"],
            "頭数": [16, 16, 16],
            "馬場状態": ["良", "良", "良"],
            "着順": ["1", "1", "3"],
            "上り3F順位": ["1", "1", "2"],
            "PCI": [59.0, 61.2, 58.5],
            "距離": [1800, 1800, 1800],
            "間隔": ["中12週", "中4週", "中5週"],
            "馬体重増減": ["+14", "+2", "-2"],
        }),
    },
    {
        "num": 3,
        "name": "サードアイ",
        "style_default": "追込",
        "past_data": pd.DataFrame({
            "通過1": ["14", "15", "13"],
            "頭数": [16, 16, 16],
            "馬場状態": ["重", "不良", "良"],
            "着順": ["8", "11", "5"],
            "上り3F順位": ["5", "8", "3"],
            "PCI": [42.0, 40.5, 45.0],
            "距離": [1800, 1800, 1800],
            "間隔": ["中3週", "中2週", "中6週"],
            "馬体重増減": ["0", "-4", "+2"],
        }),
    },
]

# --- 全馬スコア演算処理 ---
processed_horses = []

for horse in demo_horses:
  past_df = horse["past_data"]

  # 1. 真の脚質
  real_style = calculate_real_running_style(past_df)

  # 2. 各エンジン評価
  bad_res = bad_analyzer.evaluate_horse(
      past_df, current_track_condition, real_style
  )
  pci_res = pci_analyzer.evaluate_horse(past_df, expected_pace)
  rot_res = rotation_analyzer.evaluate_horse(
      past_df, current_course, current_distance, real_style
  )

  # 3. 総合スコア算出
  base_score = 70.0
  total_score = (
      base_score
      + bad_res["score_adjustment"]
      + pci_res["score_adjustment"]
      + rot_res["score_adjustment"]
  )

  # 4. コメント集約
  comments = [
      c
      for c in [bad_res["comment"], pci_res["comment"], rot_res["comment"]]
      if c and "標準" not in c and "なし" not in c
  ]

  processed_horses.append({
      "num": horse["num"],
      "name": horse["name"],
      "total_score": round(total_score, 1),
      "real_style": real_style,
      "bad_flag": bad_res["status_flag"],
      "pci_flag": pci_res["pci_flag"],
      "up3_flag": pci_res["up3_flag"],
      "rot_flag": rot_res["rotation_flag"],
      "comments": comments,
  })

# スコア順ソート
ranked_horses = sorted(
    processed_horses, key=lambda x: x["total_score"], reverse=True
)

# --- 画面描画 ---
st.subheader("🏆 総合適性スコア ランキング")

tab1, tab2 = st.tabs(["📊 スコア一覧表", "🎴 出走馬詳細分析カード"])

with tab1:
  df_disp = pd.DataFrame(ranked_horses)[
      ["num", "name", "total_score", "real_style", "bad_flag", "pci_flag"]
  ]
  df_disp.columns = [
      "馬番",
      "馬名",
      "総合適性スコア",
      "推定脚質",
      "道悪適性",
      "ペース耐性",
  ]
  st.dataframe(df_disp, use_container_width=True, hide_index=True)

with tab2:
  for rank, horse in enumerate(ranked_horses, start=1):
    crown = (
        "🥇"
        if rank == 1
        else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))
    )

    with st.container(border=True):
      col1, col2, col3 = st.columns([1.5, 3.5, 2])

      with col1:
        st.markdown(f"### {crown} {horse['name']}")
        st.caption(f"馬番: {horse['num']}番 | 真の脚質: **{horse['real_style']}**")

      with col2:
        tags_html = ""
        if horse["bad_flag"] == "道悪◎":
          tags_html += (
              '<span style="background-color:#28a745; color:white;'
              ' padding:3px 8px; border-radius:5px;'
              ' margin-right:5px;">道悪◎</span>'
          )
        elif horse["bad_flag"] in ["危険馬", "道悪×"]:
          tags_html += (
              '<span style="background-color:#dc3545; color:white;'
              ' padding:3px 8px; border-radius:5px;'
              ' margin-right:5px;">危険馬（道悪/展開）</span>'
          )

        if horse["up3_flag"] == "キレ味抜群":
          tags_html += (
              '<span style="background-color:#17a2b8; color:white;'
              ' padding:3px 8px; border-radius:5px;'
              ' margin-right:5px;">キレ味抜群</span>'
          )

        if horse["pci_flag"] == "ハイペース耐性〇":
          tags_html += (
              '<span style="background-color:#fd7e14; color:white;'
              ' padding:3px 8px; border-radius:5px;'
              ' margin-right:5px;">ハイペース耐性〇</span>'
          )

        if horse["rot_flag"] == "危険（仕上がり途上）":
          tags_html += (
              '<span style="background-color:#6c757d; color:white;'
              ' padding:3px 8px; border-radius:5px;'
              ' margin-right:5px;">仕上がり途上</span>'
          )

        st.markdown(tags_html, unsafe_allow_html=True)

        if horse["comments"]:
          for c in horse["comments"]:
            st.text(f"• {c}")
        else:
          st.caption("目立った傾向なし（標準的な適性）")

      with col3:
        st.metric(label="総合適性スコア", value=f"{horse['total_score']} pt")
