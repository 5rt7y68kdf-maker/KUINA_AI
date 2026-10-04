import os
import io
import urllib.request
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

class RaceAnalyzer:
    def __init__(self, frame_csv="2020_2025_枠番.csv", style_csv="2020_2025脚質.csv", default_race_csv="DG261004.CSV"):
        self.frame_csv = frame_csv
        self.style_csv = style_csv
        self.default_race_csv = default_race_csv

    def parse_races_from_source(self, github_url=""):
        """ローカルCSVまたはGitHub Raw URLから出馬表データを読み込んで解析"""
        lines = []
        if github_url and github_url.startswith("http"):
            try:
                # GitHubからの取得
                req = urllib.request.Request(github_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    content = response.read().decode('cp932', errors='replace')
                    lines = [line.strip() for line in content.splitlines() if line.strip()]
            except Exception as e:
                print(f"GitHub fetch error: {e}")

        if not lines and os.path.exists(self.default_race_csv):
            try:
                with open(self.default_race_csv, 'r', encoding='cp932', errors='replace') as f:
                    lines = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"Local CSV read error: {e}")

        if not lines:
            return self._get_default_races()

        return self._parse_lines_to_races(lines)

    def _parse_lines_to_races(self, lines):
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
                    jockey = parts[12].strip()
                    odds = float(parts[15]) if parts[15].replace('.','',1).isdigit() else 99.0
                    
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
                        "jockey": jockey, "odds": odds, "style": style,
                        "popularity": 0
                    })

            horses.sort(key=lambda x: x['odds'])
            for p_idx, h in enumerate(horses):
                h['popularity'] = p_idx + 1
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

    def analyze_race(self, race_data, custom_track_bias="良馬場・前残り"):
        course_name = race_data['course']
        condition = race_data['condition_type']
        horses = race_data['horses']

        # 馬場入力から前残り傾向か差し傾向かを判定
        is_front_bias = "前" in custom_track_bias or "逃げ" in custom_track_bias or "先行" in custom_track_bias
        is_sashi_bias = "差し" in custom_track_bias or "外" in custom_track_bias or "追込" in custom_track_bias

        pace_analysis = self._predict_pace_and_scenario(horses, custom_track_bias)

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
            
            # 手入力された馬場コンディションによるスコア補正
            bias_score = 0.0
            if is_front_bias and h['style'] in ['逃げ', '先行']:
                bias_score += 15.0
            elif is_sashi_bias and h['style'] in ['差し', '追込']:
                bias_score += 15.0

            final_score = min(round(base_score + bias_score, 1), 99.9)

            is_dangerous = False
            danger_reason = ""
            if h['popularity'] <= 2:
                if f_rate <= 10.0:
                    is_dangerous = True
                    danger_reason = f"コース不振枠（{h['frame']}枠：複勝率{f_rate}%）に入った人気馬"
                elif is_front_bias and h['style'] == '追込':
                    is_dangerous = True
                    danger_reason = "入力された前残り馬場バイアス下での不発リスク（追込）"

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
            "top_frame": f"{max(frame_rate_map.values())}% ({[k for k,v in frame_rate_map.items() if v==max(frame_rate_map.values())][0]}枠)",
            "top_style": f"{max(style_rate_map.values())}% ({[k for k,v in style_rate_map.items() if v==max(style_rate_map.values())][0]})",
            "bias_note": custom_track_bias
        }

        return {
            "golden_pattern": golden_pattern,
            "pace_analysis": pace_analysis,
            "horses": analyzed_horses
        }

    def _predict_pace_and_scenario(self, horses, track_bias):
        nige_list = [h['name'] for h in horses if h['style'] == '逃げ']
        senko_list = [h['name'] for h in horses if h['style'] == '先行']
        
        nige_count = len(nige_list)
        senko_count = len(senko_list)

        if nige_count >= 2 or (nige_count + senko_count) >= 6:
            pace = "ハイペース（ハナ争い激化）"
            scenario = f"先頭争いが激しくなる展開。基本は差しの展開ですが、指定された馬場コンディション『{track_bias}』の影響を考慮して立ち回りを選択する必要があります。"
        elif nige_count == 1:
            pace = "スロー〜ミドルペース（単騎逃げ濃厚）"
            scenario = f"【ハナ主張: {', '.join(nige_list)}】単騎マイペースの逃げ。馬場条件『{track_bias}』と連動して好位グループからの好走率が非常に高くなります。"
        else:
            pace = "超スローペース（逃げ馬不在）"
            scenario = f"明確な逃げ馬がおらず超スローペース濃厚。指定馬場『{track_bias}』を踏まえ、4コーナーで前目に付けられる馬が有利です。"

        return {
            "pace": pace,
            "scenario": scenario,
            "front_runners": f"逃げ: {nige_count}頭 / 先行: {senko_count}頭"
        }

    def _get_default_races(self):
        return [{
            "id": 0, "title": "東京 11R - 毎日王冠 (GII) (東京・芝1800m)",
            "venue": "東京", "r_num": 11, "course": "東京・芝1800m", "condition_type": "古馬・オープン",
            "horses": [
                {"num": 1, "frame": 1, "name": "セイウンハーデス", "jockey": "幸英明", "odds": 10.2, "style": "先行", "popularity": 4},
                {"num": 2, "frame": 1, "name": "リアライズシリウス", "jockey": "津村明秀", "odds": 2.7, "style": "差し", "popularity": 1},
                {"num": 9, "frame": 5, "name": "ドラゴンブースト", "jockey": "丹内祐次", "odds": 29.7, "style": "差し", "popularity": 9},
                {"num": 10, "frame": 5, "name": "エルトンバローズ", "jockey": "松若風馬", "odds": 25.3, "style": "先行", "popularity": 6},
                {"num": 13, "frame": 7, "name": "ホウオウビスケッツ", "jockey": "岩田康誠", "odds": 25.5, "style": "先行", "popularity": 7},
                {"num": 17, "frame": 8, "name": "ダノンエアズロック", "jockey": "田辺裕信", "odds": 28.2, "style": "先行", "popularity": 8},
            ]
        }]

analyzer = RaceAnalyzer()

@app.route('/', methods=['GET', 'POST'])
def index():
    github_url = request.args.get('github_url', request.form.get('github_url', '')).strip()
    custom_track_bias = request.args.get('track_bias', request.form.get('track_bias', '良馬場・前残り')).strip()
    selected_race_id = int(request.args.get('race_id', request.form.get('race_id', 10)))

    all_races = analyzer.parse_races_from_source(github_url)
    
    if selected_race_id >= len(all_races):
        selected_race_id = 0

    selected_race = all_races[selected_race_id]
    analysis_result = analyzer.analyze_race(selected_race, custom_track_bias=custom_track_bias)

    return render_template(
        'index.html',
        all_races=all_races,
        selected_race=selected_race,
        data=analysis_result,
        github_url=github_url,
        track_bias=custom_track_bias
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
