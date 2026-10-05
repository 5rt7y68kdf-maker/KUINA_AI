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
