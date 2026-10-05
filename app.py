import os
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

class RaceAnalyzer:
    def __init__(self, frame_csv="2020_2025_枠番.csv", style_csv="2020_2025脚質.csv", race_csv="DG261004.CSV"):
        self.frame_csv = frame_csv
        self.style_csv = style_csv
        self.race_csv = race_csv

    def parse_all_races(self):
        """出馬表CSVから全24レースを自動抽出"""
        if not os.path.exists(self.race_csv):
            return self._get_default_races()

        try:
            with open(self.race_csv, 'r', encoding='cp932', errors='replace') as f:
                lines = [line.strip() for line in f if line.strip()]

            races = []
            current_race_lines = []
            
            for line in lines:
                if line.startswith('枠番,B,番,印') and current_race_lines:
                    races.append(current_race_lines)
                    current_race_lines = [line]
                else:
                    current_race_lines.append(line)
            if current_race_lines:
                races.append(current_race_lines)

            parsed_races = []
            for idx, rlines in enumerate(races):
                venue = "東京" if idx < 12 else "京都"
                r_num = (idx % 12) + 1
                
                horses = []
                for l in rlines[1:]:
                    parts = [p.strip() for p in l.split(',')]
                    if len(parts) >= 16 and parts[0].isdigit():
                        frame = int(parts[0])
                        num = int(parts[2])
                        name = parts[7].strip()
                        
                        style = "差し"
                        if frame in [1, 2] and num <= 3:
                            style = "逃げ" if num == 1 else "先行"
                        elif frame in [3, 4, 5]:
                            style = "先行"
                        elif frame in [6, 7]:
                            style = "差し"
                        else:
                            style = "追込"

                        horses.append({
                            "num": num, "frame": frame, "name": name,
                            "style": style
                        })

                horses.sort(key=lambda x: x['num'])
                course_info = self._get_course_info(venue, r_num)

                parsed_races.append({
                    "id": idx,
                    "title": f"{venue} {r_num}R - {course_info['name']} ({course_info['course']})",
                    "venue": venue,
                    "r_num": r_num,
                    "course": course_info['course'],
                    "condition_type": course_info['condition'],
                    "horses": horses
                })

            return parsed_races
        except Exception as e:
            print(f"Parse error: {e}")
            return self._get_default_races()

    def _get_course_info(self, venue, r_num):
        mapping = {
            ("東京", 11): {"name": "毎日王冠 (GII)", "course": "東京・芝1800m", "condition": "古馬・オープン"},
            ("京都", 11): {"name": "京都大賞典 (GII)", "course": "京都・芝2400m", "condition": "古馬・オープン"},
        }
        return mapping.get((venue, r_num), {
            "name": f"{venue}{r_num}R",
            "course": f"{venue}・芝1600m" if r_num % 2 == 1 else f"{venue}・ダ1400m",
            "condition": "古馬・１勝"
        })

    def analyze_race(self, race_data, weather="晴", track_condition="良", track_bias="前・先行有利"):
        course_name = race_data['course']
        condition = race_data['condition_type']
        horses = race_data['horses']

        pace_analysis = self._predict_pace_and_scenario(horses, weather, track_condition, track_bias)

        frame_rate_map = {1: 8.0, 2: 10.0, 3: 8.0, 4: 12.0, 5: 18.0, 6: 12.0, 7: 16.0, 8: 16.0}
        style_rate_map = {"逃げ": 10.0, "先行": 36.0, "差し": 38.0, "追込": 16.0}

        if os.path.exists(self.frame_csv) and os.path.exists(self.style_csv):
            try:
                df_f = pd.read_csv(self.frame_csv, encoding='cp932')
                df_s = pd.read_csv(self.style_csv, encoding='cp932')
                f_match = df_f[(df_f['場所･距離'] == course_name) & (df_f['条件'] == condition)]
                s_match = df_s[(df_s['場所･距離'] == course_name) & (df_s['条件'] == condition)]

                if not f_match.empty and not s_match.empty:
                    f_row = f_match.iloc[0]
                    s_row = s_match.iloc[0]
                    for i in range(1, 9):
                        frame_rate_map[i] = float(f_row.get(f"{i}枠", 12.0))
                    for st in ["逃げ", "先行", "差し", "追込"]:
                        style_rate_map[st] = float(s_row.get(st, 20.0))
            except Exception as e:
                print(f"CSV read error: {e}")

        analyzed_horses = []
        for h in horses:
            f_rate = frame_rate_map.get(h['frame'], 12.0)
            s_rate = style_rate_map.get(h['style'], 20.0)

            base_score = (f_rate + s_rate) / 2
            
            # 純データ補正（馬場状態・コースバイアス・展開適合）
            bias_score = 0.0
            if track_condition in ["重", "不良"]:
                if h['style'] in ["逃げ", "先行"]:
                    bias_score += 10.0
                elif h['style'] == "追込":
                    bias_score -= 8.0

            if track_bias == "前・先行有利":
                if h['style'] in ["逃げ", "先行"]:
                    bias_score += 12.0
                elif h['style'] == "追込":
                    bias_score -= 6.0
            elif track_bias == "内枠有利":
                if h['frame'] in [1, 2, 3]:
                    bias_score += 10.0
                elif h['frame'] in [6, 7, 8]:
                    bias_score -= 5.0
            elif track_bias == "差し・外有利":
                if h['style'] in ["差し", "追込"]:
                    bias_score += 10.0
                if h['frame'] in [6, 7, 8]:
                    bias_score += 5.0

            final_score = min(round(base_score + bias_score, 1), 99.9)

            # 純データによる不振・危険条件判定
            is_dangerous = False
            danger_reason = ""
            if f_rate <= 10.0:
                is_dangerous = True
                danger_reason = f"コース不振枠（{h['frame']}枠：5年複勝率{f_rate}%）該当馬"
            elif track_bias == "前・先行有利" and h['style'] == '追込':
                is_dangerous = True
                danger_reason = "前・先行有利傾向下での不発リスク（追込脚質）"
            elif track_condition in ["重", "不良"] and h['style'] == '追込':
                is_dangerous = True
                danger_reason = "道悪馬場（重・不良）での後方一気不発リスク"

            analyzed_horses.append({
                **h,
                "frame_rate": f_rate,
                "style_rate": s_rate,
                "score": final_score,
                "is_dangerous": is_dangerous,
                "danger_reason": danger_reason
            })

        analyzed_horses.sort(key=lambda x: x['score'], reverse=True)

        golden_pattern = {
            "top_frame": f"{max(frame_rate_map.values())}% ({[k for k,v in frame_rate_map.items() if v==max(frame_rate_map.values())]}枠)",
            "top_style": f"{max(style_rate_map.values())}% ({[k for k,v in style_rate_map.items() if v==max(style_rate_map.values())]})",
            "bias_note": f"天気: {weather} / 馬場: {track_condition} ({track_bias})"
        }

        betting_patterns = self._generate_betting_patterns(analyzed_horses, pace_analysis)

        return {
            "golden_pattern": golden_pattern,
            "pace_analysis": pace_analysis,
            "betting_patterns": betting_patterns,
            "horses": analyzed_horses
        }

    def _predict_pace_and_scenario(self, horses, weather, track_condition, track_bias):
        nige_list = [h['name'] for h in horses if h['style'] == '逃げ']
        senko_list = [h['name'] for h in horses if h['style'] == '先行']
        
        nige_count = len(nige_list)
        senko_count = len(senko_list)

        if nige_count >= 2 or (nige_count + senko_count) >= 6:
            pace = "ハイペース（ハナ争い激化）"
            scenario = f"同型馬が揃いハイペース想定。差し脚質に適性がありますが、馬場『{track_condition}』・傾向『{track_bias}』の適合度が鍵となります。"
        elif nige_count == 1:
            pace = "スロー〜ミドルペース（単騎逃げ濃厚）"
            scenario = f"【ハナ主張: {', '.join(nige_list)}】単騎マイペース濃厚。馬場『{track_condition}』・傾向『{track_bias}』下で好位グループ（{', '.join((nige_list+senko_list)[:3])}）が優位に立ちます。"
        else:
            pace = "超スローペース（逃げ馬不在）"
            scenario = f"明確な逃げ馬不在の超スロー想定。上がり勝負になりますが、選択条件『{weather} / {track_condition}』の影響で前目に付けられる馬が優勢です。"

        return {
            "pace": pace,
            "scenario": scenario,
            "front_runners": f"逃げ: {nige_count}頭 / 先行: {senko_count}頭"
        }

    def _generate_betting_patterns(self, horses, pace_analysis):
        if not horses:
            return []

        top_1 = horses[0]
        top_2 = horses[1] if len(horses) > 1 else top_1
        top_3 = horses[2] if len(horses) > 2 else top_2
        top_4 = horses[3] if len(horses) > 3 else top_3

        dangerous_horses = [h for h in horses if h.get('is_dangerous')]
        dangerous_names = [h['name'] for h in dangerous_horses]
        dangerous_nums = {h['num'] for h in dangerous_horses}

        # データ展開適合馬（上位以外の好適性馬）
        tactical_fit = [h for h in horses[1:] if not h.get('is_dangerous')]
        match_horse = tactical_fit[0] if tactical_fit else top_2

        # 1. 本命・最高データ適性
        p1_rec = f"{top_1['num']} - {top_2['num']}" + (f", {top_1['num']} - {top_3['num']}" if top_2['num'] != top_3['num'] else "")

        # 2. 展開・条件ジャストフィット
        p2_rec = f"{match_horse['num']} (軸) ➔ {top_1['num']}, {top_2['num']}"

        # 3. 不振データ・リスク回避
        safe_horses = [h for h in horses if h['num'] not in dangerous_nums][:5]
        if len(safe_horses) < 3:
            safe_horses = horses[:5]
        p3_rec = f"1頭目: {safe_horses[0]['num']} / 2頭目: {', '.join([str(h['num']) for h in safe_horses[1:3]])} / 3頭目: {', '.join([str(h['num']) for h in safe_horses[1:5]])}"

        # 4. データ上位BOX
        box_nums = [str(h['num']) for h in [top_1, top_2, top_3, top_4]]
        p4_rec = f"BOX: {', '.join(box_nums)} （計4点）"

        # 5. 3連単データフォーメーション
        t1 = [str(top_1['num']), str(top_2['num'])]
        t2 = [str(top_1['num']), str(top_2['num']), str(top_3['num'])]
        t3 = [str(h['num']) for h in [top_1, top_2, top_3, top_4, match_horse] if h['num']]
        p5_rec = f"1着: {', '.join(dict.fromkeys(t1))} ➔ 2着: {', '.join(dict.fromkeys(t2))} ➔ 3着: {', '.join(dict.fromkeys(t3))}"

        return [
            {
                "id": 1,
                "badge": "最高適性",
                "badge_class": "badge-solid",
                "name": "① データ軸・標準推奨（馬連・ワイド）",
                "type": "馬連・ワイド流し",
                "recommendation": p1_rec,
                "description": f"データ適性スコア最上位【{top_1['name']}】を軸に、高適性馬【{top_2['name']}】・【{top_3['name']}】へ流す着実な買い目。",
                "risk": "データ最高適合 / 安定重視"
            },
            {
                "id": 2,
                "badge": "条件ジャスト",
                "badge_class": "badge-hole",
                "name": "② 展開・馬場ジャストフィット（ワイド流し）",
                "type": "ワイド軸1頭流し",
                "recommendation": p2_rec,
                "description": f"設定された馬場コンディションと展開シナリオに最も合致する【{match_horse['name']}】を軸に固定した効率重視パターン。",
                "risk": "展開・馬場適合重視"
            },
            {
                "id": 3,
                "badge": "不振枠カット",
                "badge_class": "badge-danger-cut",
                "name": "③ 不振データ・リスクカット（3连複フォーメーション）",
                "type": "3連複フォーメーション",
                "recommendation": p3_rec,
                "description": f"コース不振枠やバイアス逆風の馬（{', '.join(dangerous_names) if dangerous_names else 'なし'}）を除外し、高適性馬のみで構成した買い目。",
                "risk": "低適性データ完全排除"
            },
            {
                "id": 4,
                "badge": "データ上位BOX",
                "badge_class": "badge-pace",
                "name": "④ データ上位4頭（3連複BOX）",
                "type": "3連複BOX",
                "recommendation": p4_rec,
                "description": f"純データ適性スコア上位4頭（{', '.join([h['name'] for h in [top_1, top_2, top_3, top_4]])}）による安定性重視のBOX買い。",
                "risk": "上位適性馬の網羅"
            },
            {
                "id": 5,
                "badge": "高適性フォーメーション",
                "badge_class": "badge-max",
                "name": "⑤ 高適性3連単フォーメーション",
                "type": "3連単フォーメーション",
                "recommendation": p5_rec,
                "description": f"データ上位馬を1・2着軸に据え、展開適合馬【{match_horse['name']}】まで網羅した高精度フォーメーション。",
                "risk": "適性重視・高配当狙い"
            }
        ]

    def _get_default_races(self):
        return [{
            "id": 0, "title": "東京 11R - 毎日王冠 (GII) (東京・芝1800m)",
            "venue": "東京", "r_num": 11, "course": "東京・芝1800m", "condition_type": "古馬・オープン",
            "horses": [
                {"num": 1, "frame": 1, "name": "セイウンハーデス", "style": "先行"},
                {"num": 2, "frame": 1, "name": "リアライズシリウス", "style": "差し"},
                {"num": 9, "frame": 5, "name": "ドラゴンブースト", "style": "差し"},
                {"num": 10, "frame": 5, "name": "エルトンバローズ", "style": "先行"},
                {"num": 13, "frame": 7, "name": "ホウオウビスケッツ", "style": "先行"},
                {"num": 17, "frame": 8, "name": "ダノンエアズロック", "style": "先行"},
            ]
        }]

analyzer = RaceAnalyzer()

@app.route('/', methods=['GET', 'POST'])
def index():
    selected_race_id = int(request.args.get('race_id', request.form.get('race_id', 10)))
    weather = request.args.get('weather', request.form.get('weather', '晴'))
    track_condition = request.args.get('track_condition', request.form.get('track_condition', '良'))
    track_bias = request.args.get('track_bias', request.form.get('track_bias', '前・先行有利'))

    all_races = analyzer.parse_all_races()
    
    if selected_race_id >= len(all_races):
        selected_race_id = 0

    selected_race = all_races[selected_race_id]
    analysis_result = analyzer.analyze_race(
        selected_race,
        weather=weather,
        track_condition=track_condition,
        track_bias=track_bias
    )

    return render_template(
        'index.html',
        all_races=all_races,
        selected_race=selected_race,
        data=analysis_result,
        weather=weather,
        track_condition=track_condition,
        track_bias=track_bias
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# --- app.py のメイン計算ロジック内（イメージ） ---

# 1. クラスのインスタンス化
analyzer = BadTrackAnalyzer()

# 2. 該当馬の「過去データ」「当日の馬場（重・不良等）」「算出済みの真の脚質」を渡して評価
eval_res = analyzer.evaluate_horse(
    horse_past_df, current_track_condition, real_style
)

# 3. 総合適性スコアに加減算を反映
horse_total_score += eval_res['score_adjustment']

# 4. 画面（UI）表示用のデータにフラグやコメントをセット
horse_display_data['bad_track_flag'] = eval_res['status_flag']  # 例: '道悪◎', '危険馬'
horse_display_data['bad_track_comment'] = eval_res['comment']

import re
import pandas as pd


class PciUp3Analyzer:
  """PCI（ペース耐性）と上がり3F（末脚の絶対値）を解析し、

  想定ペースに応じた適性スコアと評価コメントを自動生成するクラス
  """

  def __init__(self):
    pass

  def evaluate_horse(self, horse_past_df, expected_pace='ミドルペース'):
    """該当馬のPCIおよび上がり3F適性を評価する関数

    Parameters:
    - horse_past_df (pd.DataFrame): 該当馬の過去走データ
    - expected_pace (str): 今回のレース予想ペース ('ハイペース',
    'ミドルペース', 'スローペース')

    Returns:
    - dict: {
        'score_adjustment': float (スコア補正値 +/-),
        'pci_flag': str ('ハイペース耐性〇', '瞬発力勝負〇', 'ハイペース懸念',
        '標準'),
        'up3_flag': str ('キレ味抜群', '末脚上位', '標準'),
        'comment': str (画面表示用コメント),
        'stats': dict (解析結果サマリー)
      }
    """
    res = {
        'score_adjustment': 0.0,
        'pci_flag': '標準',
        'up3_flag': '標準',
        'comment': '',
        'stats': {
            'avg_pci_top3': None,
            'top_up3_count': 0,
            'recent_races': 0,
        },
    }

    if horse_past_df is None or horse_past_df.empty:
      res['comment'] = '過去走データなし'
      return res

    # 直近5走を取得
    recent = horse_past_df.head(5)
    res['stats']['recent_races'] = len(recent)

    # -------------------------------------------------------------
    # 軸1: 上がり3F順位の分析（末脚の絶対値評価）
    # -------------------------------------------------------------
    top_up3_count = 0
    if '上り3F順位' in recent.columns:
      for _, row in recent.iterrows():
        try:
          rank_str = str(row.get('上り3F順位', ''))
          match = re.search(r'\d+', rank_str)
          if match:
            rank = int(match.group())
            if rank <= 2:  # 上がり1〜2位をカウント
              top_up3_count += 1
        except Exception:
          continue

    res['stats']['top_up3_count'] = top_up3_count

    # 上がり3Fによる評価・スコア加算
    up3_comment = ''
    if top_up3_count >= 3:
      res['score_adjustment'] += 10.0
      res['up3_flag'] = 'キレ味抜群'
      up3_comment = (
          f'近{len(recent)}走中{top_up3_count}回で上がり2位以内の強力な末脚'
      )
    elif top_up3_count >= 2:
      res['score_adjustment'] += 5.0
      res['up3_flag'] = '末脚上位'
      up3_comment = (
          f'安定した末脚（近{len(recent)}走で上がり2位以内{top_up3_count}回）'
      )

    # -------------------------------------------------------------
    # 軸2: PCI（ペース耐性）と想定ペースの合致判定
    # -------------------------------------------------------------
    pci_comments = []
    if 'PCI' in recent.columns and '着順' in recent.columns:
      # 好走時（3着以内）のPCI平均を優先計算
      good_races = recent[
          recent['着順'].astype(str).str.extract(r'(\d+)')[0].astype(float) <= 3
      ]
      target_races = good_races if not good_races.empty else recent

      pci_list = []
      for _, row in target_races.iterrows():
        try:
          pci_val = float(str(row.get('PCI', '')).strip())
          if 30.0 <= pci_val <= 80.0:  # 正常範囲内のPCIデータ
            pci_list.append(pci_val)
        except Exception:
          continue

      if pci_list:
        avg_pci = sum(pci_list) / len(pci_list)
        res['stats']['avg_pci_top3'] = round(avg_pci, 1)

        # 想定ペースとの相性判定
        if expected_pace == 'ハイペース':
          if avg_pci <= 50.0:
            res['score_adjustment'] += 8.0
            res['pci_flag'] = 'ハイペース耐性〇'
            pci_comments.append(
                f'ハイペース消耗戦に強み（好走PCI平均 {round(avg_pci, 1)}）'
            )
          elif avg_pci >= 58.0:
            res['score_adjustment'] -= 6.0
            res['pci_flag'] = 'ハイペース懸念'
            pci_comments.append(
                f'スロー粘り型のため激流追走に懸念（好走PCI平均 {round(avg_pci, 1)}）'
            )

        elif expected_pace == 'スローペース':
          if avg_pci >= 55.0:
            res['score_adjustment'] += 8.0
            res['pci_flag'] = '瞬発力勝負〇'
            pci_comments.append(
                f'上がり勝負・瞬発力戦に強い（好走PCI平均 {round(avg_pci, 1)}）'
            )
          elif avg_pci <= 45.0:
            res['score_adjustment'] -= 4.0
            res['pci_flag'] = '瞬発力不足'
            pci_comments.append('瞬発力比べの上がり勝負ではやや割り引き')

    # コメントの結合
    all_comments = [c for c in [up3_comment] + pci_comments if c]
    res['comment'] = (
        ' / '.join(all_comments)
        if all_comments
        else 'ペース・末脚ともに標準的な適性です。'
    )

    return res

import re
import pandas as pd


class CourseRotationAnalyzer:
  """コース・距離適性およびローテーション（休養・馬体重）を解析するクラス"""

  def __init__(self):
    pass

  def evaluate_horse(
      self, horse_past_df, current_course, current_distance, real_style='標準'
  ):
    """該当馬のコース適性およびローテーションを評価する関数

    Parameters:
    - horse_past_df (pd.DataFrame): 該当馬の過去走データ
    - current_course (str): 今回の場名・芝ダ（例: '東京芝', '阪神ダート'）
    - current_distance (int): 今回の距離（例: 1800, 2400）
    - real_style (str): 算出済みの真の脚質

    Returns:
    - dict: 評価結果スコアと表示用データ
    """
    res = {
        'score_adjustment': 0.0,
        'course_flag': '標準',
        'rotation_flag': '順調',
        'comment': '',
    }

    if horse_past_df is None or horse_past_df.empty:
      res['comment'] = '過去走データなし'
      return res

    recent = horse_past_df.head(5)
    last_race = recent.iloc[0] if len(recent) > 0 else None

    comments = []

    # -------------------------------------------------------------
    # 軸1: 同コース・同距離での過去実績
    # -------------------------------------------------------------
    if (
        '距離' in horse_past_df.columns
        and '着順' in horse_past_df.columns
    ):
      # 距離データから数値抽出
      horse_past_df['num_dist'] = (
          horse_past_df['距離']
          .astype(str)
          .str.extract(r'(\d+)')
          .astype(float)
      )
      same_dist_races = horse_past_df[
          abs(horse_past_df['num_dist'] - current_distance) <= 100
      ]

      if len(same_dist_races) >= 2:
        top3 = (
            same_dist_races['着順']
            .astype(str)
            .str.extract(r'(\d+)')
            .astype(float)
            <= 3
        ).sum()
        dist_rate = top3 / len(same_dist_races)

        if dist_rate >= 0.50:
          res['score_adjustment'] += 8.0
          res['course_flag'] = '距離適性〇'
          comments.append(f'同近接距離で高適性（複勝率 {round(dist_rate*100)}%）')

    # -------------------------------------------------------------
    # 軸2: 距離変更（短縮 / 延長）の適性チェック
    # -------------------------------------------------------------
    if last_race is not None and 'num_dist' in horse_past_df.columns:
      prev_dist = last_race.get('num_dist', None)
      if pd.notna(prev_dist) and prev_dist > 0:
        dist_diff = current_distance - prev_dist

        if dist_diff <= -200:  # 200m以上の距離短縮
          if real_style in ['逃げ', '先行']:
            res['score_adjustment'] += 5.0
            comments.append(
                f'前走({int(prev_dist)}m)から距離短縮（先行力活きる好条件）'
            )
        elif dist_diff >= 300:  # 300m以上の大幅距離延長
          if real_style in ['追込']:
            res['score_adjustment'] -= 5.0
            comments.append(
                f'前走({int(prev_dist)}m)から大幅距離延長（折り合い・スタミナ懸念）'
            )

    # -------------------------------------------------------------
    # 軸3: ローテーション（間隔・馬体重増減）による状態リスク判定
    # -------------------------------------------------------------
    if last_race is not None:
      interval_str = str(last_race.get('間隔', ''))
      weight_diff_str = str(last_race.get('馬体重増減', ''))

      # 間隔（週数）の抽出
      interval_match = re.search(r'\d+', interval_str)
      interval_weeks = (
          int(interval_match.group()) if interval_match else None
      )

      # 馬体重増減の抽出
      weight_match = re.search(r'([+-]?\d+)', weight_diff_str)
      weight_diff = int(weight_match.group(1)) if weight_match else None

      # 久々（中10週以上）かつ馬体重大幅増（+12kg以上）
      if (
          interval_weeks
          and interval_weeks >= 10
          and weight_diff
          and weight_diff >= 12
      ):
        res['score_adjustment'] -= 8.0
        res['rotation_flag'] = '危険（仕上がり途上）'
        comments.append(
            f'長期休養明け（中{interval_weeks}週）＋馬体重太め（{weight_diff:+d}kg）で割引'
        )

    res['comment'] = (
        ' / '.join(comments) if comments else 'ローテーション・距離適性は順調です。'
    )
    return res

import pandas as pd
import streamlit as st

# ページ基本設定
st.set_page_config(
    page_title="競馬AI純データ予想分析", page_icon="🐎", layout="wide"
)

# タイトルヘッダー
st.title("🐎 競馬AI 純データ展開・適性分析ダッシュボード")
st.caption(
    "オッズ・人気に頼らない「枠順バイアス×真の脚質×馬場適性×ペースチェンジ」総合スコアモデル"
)

# -------------------------------------------------------------
# 1. サイドバー：レース条件設定
# -------------------------------------------------------------
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
  st.info("💡 過去走データと枠順データからスコアを自動計算します。")

# -------------------------------------------------------------
# 2. メインコンテンツ：分析実行＆スコア算出（サンプルデータの統合例）
# -------------------------------------------------------------
# 各分析エンジンのインスタンス化
bad_analyzer = BadTrackAnalyzer()
pci_analyzer = PciUp3Analyzer()
rotation_analyzer = CourseRotationAnalyzer()

# ※以下は各馬の計算結果を格納するイメージループです
# (実運用では出馬表CSVからループ処理)
processed_horses = []

# （サンプルデータ用データ構造）
sample_horses = [
    {"num": 1, "name": "アークライト", "past_df": None},
    {"num": 2, "name": "ディアファザー", "past_df": None},
    {"num": 3, "name": "サードアイ", "past_df": None},
]

for horse in sample_horses:
  # 1. 真の脚質算出
  real_style = calculate_real_running_style(horse["past_df"]) or "先行"

  # 2. 各エンジンの評価実行
  bad_res = bad_analyzer.evaluate_horse(
      horse["past_df"], current_track_condition, real_style
  )
  pci_res = pci_analyzer.evaluate_horse(horse["past_df"], expected_pace)
  rot_res = rotation_analyzer.evaluate_horse(
      horse["past_df"], current_course, current_distance, real_style
  )

  # 3. 総合スコアの合計（ベース100pt + 各補正値）
  base_score = 70.0
  total_score = (
      base_score
      + bad_res["score_adjustment"]
      + pci_res["score_adjustment"]
      + rot_res["score_adjustment"]
  )

  # コメントの集約
  all_comments = [
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
      "comments": all_comments,
  })

# スコア順にソート（ランキング化）
ranked_horses = sorted(
    processed_horses, key=lambda x: x["total_score"], reverse=True
)

# -------------------------------------------------------------
# 3. UI表示：上位推奨馬ランキング＆詳細カード表示
# -------------------------------------------------------------
st.subheader("🏆 総合適性スコア ランキング")

# タブ切り替え（一覧表示 / 詳細カード表示）
tab1, tab2 = st.tabs(["📊 スコア一覧表", "🎴 出走馬詳細分析カード"])

with tab1:
  # ランキングサマリーテーブル
  df_display = pd.DataFrame(ranked_horses)[
      ["num", "name", "total_score", "real_style", "bad_flag", "pci_flag"]
  ]
  df_display.columns = [
      "馬番",
      "馬名",
      "総合適性スコア",
      "推定脚質",
      "道悪適性",
      "ペース耐性",
  ]
  st.dataframe(df_display, use_container_width=True, hide_index=True)

with tab2:
  # カード型詳細UIレイアウト
  for rank, horse in enumerate(ranked_horses, start=1):
    # クラウン（1〜3位）の装飾
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
        # タグ・バッジ装飾表示
        tags_html = ""
        if horse["bad_flag"] == "道悪◎":
          tags_html += (
              '<span style="background-color:#28a745; color:white;'
              ' padding:3px 8px; border-radius:5px; margin-right:5px;">道悪◎</span>'
          )
        elif horse["bad_flag"] == "危険馬":
          tags_html += (
              '<span style="background-color:#dc3545; color:white;'
              ' padding:3px 8px; border-radius:5px;'
              ' margin-right:5px;">危険馬（重ババ）</span>'
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

        st.markdown(tags_html, unsafe_allow_html=True)

        # 分析評価コメント
        if horse["comments"]:
          for c in horse["comments"]:
            st.text(f"• {c}")
        else:
          st.caption("目立ったマイナス要素・突出した加点要素なし（標準）")

      with col3:
        # 総合スコア表示
        st.metric(label="総合適性スコア", value=f"{horse['total_score']} pt")
