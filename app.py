import os
import re
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

class RaceAnalyzer:
    def __init__(self, frame_csv="2020_2025_枠番.csv", style_csv="2020_2025脚質.csv", race_csv="DG261004.CSV"):
        self.frame_csv = frame_csv
        self.style_csv = style_csv
        self.race_csv = race_csv

    def parse_all_races(self):
        """出馬表CSVから全レースを自動抽出"""
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
                        jockey = parts[12].strip()
                        odds = float(parts[15]) if parts[15].replace('.','',1).isdigit() else 99.0
                        
                        # 脚質簡易推定（1番人気〜2番人気・先行騎手等のダミー補正込み）
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
                            "popularity": 0  # 後でソートして設定
                        })

                # 単勝オッズ順に人気を設定
                horses.sort(key=lambda x: x['odds'])
                for p_idx, h in enumerate(horses):
                    h['popularity'] = p_idx + 1
                horses.sort(key=lambda x: x['num'])

                # コース設定の判定
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
        """レース番号に応じたコース・条件マップ"""
        mapping = {
            ("東京", 11): {"name": "毎日王冠 (GII)", "course": "東京・芝1800m", "condition": "古馬・オープン"},
            ("京都", 11): {"name": "京都大賞典 (GII)", "course": "京都・芝2400m", "condition": "古馬・オープン"},
            ("東京", 1): {"name": "2歳未勝利", "course": "東京・芝1400m", "condition": "２歳・未勝利"},
            ("東京", 2): {"name": "2歳未勝利", "course": "東京・ダ1400m", "condition": "２歳・未勝利"},
            ("京都", 1): {"name": "2歳未勝利", "course": "京都・ダ1200m", "condition": "２歳・未勝利"},
        }
        return mapping.get((venue, r_num), {
            "name": f"{venue}{r_num}R",
            "course": f"{venue}・芝1600m" if r_num % 2 == 1 else f"{venue}・ダ1400m",
            "condition": "古馬・１勝"
        })

    def analyze_race(self, race_data, track_bias_front=True):
        course_name = race_data['course']
        condition = race_data['condition_type']
        horses = race_data['horses']

        # 展開予想（ペース & 隊列分析）
        pace_analysis = self._predict_pace_and_scenario(horses, track_bias_front)

        # コース別5年集計データの参照
        frame_rate_map = {1: 8.0, 2: 10.0, 3: 8.0, 4: 12.0, 5: 18.0, 6: 12.0, 7: 16.0, 8: 16.0}
        style_rate_map = {"逃げ": 10.0, "先行": 36.0, "差し": 38.0, "追込": 16.0}

        if os.path.exists(self.frame_csv) and os.path.exists(self.style_csv):
            try:
                df_f = pd.read_csv(self.frame_csv, encoding='cp932')
                df_s = pd.read_csv(self.style_csv, encoding='cp932')
                f_match = df_f[(df_f['場所･距離'] == course_name) & (df_f['条件'] == condition)]
                s_match = df_s[(df_s['場所･距離'] == course_name) & (df_s['条件'] == condition)]

                if not f_match.empty and not s_match.empty:
                    f_row = f_match.iloc
                    s_row = s_match.iloc
                    for i in range(1, 9):
                        frame_rate_map[i] = float(f_row.get(f"{i}枠", 12.0))
                    for st in ["逃げ", "先行", "差し", "追込"]:
                        style_rate_map[st] = float(s_row.get(st, 20.0))
            except Exception as e:
                print(f"CSV read error: {e}")

        # 各馬のスコアリングと危険度判定
        analyzed_horses = []
        for h in horses:
            f_rate = frame_rate_map.get(h['frame'], 12.0)
            s_rate = style_rate_map.get(h['style'], 20.0)

            base_score = (f_rate + s_rate) / 2
            bias_score = 15.0 if track_bias_front and h['style'] in ['逃げ', '先行'] else 0.0
            final_score = min(round(base_score + bias_score, 1), 99.9)

            is_dangerous = False
            danger_reason = ""
            if h['popularity'] <= 2:
                if f_rate <= 10.0:
                    is_dangerous = True
                    danger_reason = f"コース不振枠（{h['frame']}枠：複勝率{f_rate}%）に入った人気馬"
                elif track_bias_front and h['style'] == '追込':
                    is_dangerous = True
                    danger_reason = "前残りバイアス下での後方一気（追込）不発リスク"

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
            "bias_note": "良馬場・前残りバイアス適用中" if track_bias_front else "標準"
        }

        return {
            "golden_pattern": golden_pattern,
            "pace_analysis": pace_analysis,
            "horses": analyzed_horses
        }

    def _predict_pace_and_scenario(self, horses, track_bias_front):
        """展開予想（ペースと隊列シナリオ）の自動生成"""
        nige_list = [h['name'] for h in horses if h['style'] == '逃げ']
        senko_list = [h['name'] for h in horses if h['style'] == '先行']
        
        nige_count = len(nige_list)
        senko_count = len(senko_list)

        if nige_count >= 2 or (nige_count + senko_count) >= 6:
            pace = "ハイペース（ハナ争い激化）"
            scenario = f"【先頭争い: {', '.join(nige_list[:2])}】前目に行きたい馬が多く先行争いが激しくなる展開。基本は差し馬に展開が向きますが、当日は『前残りバイアス』が出ているため、粘り強い先行馬（{', '.join(senko_list[:2]) if senko_list else '好位馬'}）の残りに警戒が必要です。"
        elif nige_count == 1:
            pace = "スロー〜ミドルペース（単騎逃げ濃厚）"
            scenario = f"【ハナ主張: {nige_list[0]}】単騎マイペースの逃げが濃厚。無駄な競り合いがなくペースが落ち着くため、『前残りバイアス』と完全に合致。逃げ・先行グループ（{', '.join((nige_list+senko_list)[:3])}）が直線でそのまま押し切る展開が最有力です。"
        else:
            pace = "超スローペース（逃げ馬不在・瞬発力勝負）"
            scenario = "【展開: 押し出される逃げ】明確な逃げ馬がおらず超スローペース濃厚。直線での上がり勝負になりますが、前残りバイアスが強力なため、4コーナーで好位5番手以内に付けられる馬が絶対的に有利です。"

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
    all_races = analyzer.parse_all_races()
    
    # 選択されたレースID（デフォルトは毎日王冠のレースID）
    selected_race_id = int(request.args.get('race_id', request.form.get('race_id', 10)))
    if selected_race_id >= len(all_races):
        selected_race_id = 0

    selected_race = all_races[selected_race_id]
    analysis_result = analyzer.analyze_race(selected_race, track_bias_front=True)

    return render_template(
        'index.html',
        all_races=all_races,
        selected_race=selected_race,
        data=analysis_result
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
