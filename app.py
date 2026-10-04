import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)

class RaceAnalyzer:
    def __init__(self, frame_csv="2020_2025_枠番.csv", style_csv="2020_2025脚質.csv"):
        # 過去5年データの読み込み
        self.df_frame = pd.read_csv(frame_csv, encoding='cp932')
        self.df_style = pd.read_csv(style_csv, encoding='cp932')

    def analyze_race(self, course_name, condition, horses, track_bias_front=True):
        """
        コース・条件・出走馬データからデータ適性スコアを算出し、危険馬を抽出するロジック
        """
        # コース別データの取得
        frame_data = self.df_frame[(self.df_frame['場所･距離'] == course_name) & (self.df_frame['条件'] == condition)]
        style_data = self.df_style[(self.df_style['場所･距離'] == course_name) & (self.df_style['条件'] == condition)]

        if frame_data.empty or style_data.empty:
            return None

        frame_row = frame_data.iloc[0]
        style_row = style_data.iloc[0]

        # 黄金パターン情報の整理
        golden_pattern = {
            "top_frame": f"{frame_row['５枠']}% (5枠)",
            "top_style": f"{style_row['差し']}% (差し) / {style_row['先行']}% (先行)",
            "bias_note": "前残りバイアス適用中: 先行・逃げ馬のスコア補正あり" if track_bias_front else "標準バイアス"
        }

        analyzed_horses = []
        for horse in horses:
            frame_num = f"{horse['frame']}枠"
            frame_rate = float(frame_row.get(frame_num, 0.0))
            style_rate = float(style_row.get(horse['style'], 0.0))

            # 基本データスコア（枠複勝率 + 脚質複勝率）
            base_score = (frame_rate + style_rate) / 2

            # トラックバイアス補正（前残り傾向時の加減算）
            bias_score = 0
            if track_bias_front:
                if horse['style'] in ['逃げ', '先行']:
                    bias_score += 15.0  # 前残り補正で加点
                elif horse['style'] in ['追込']:
                    bias_score -= 10.0  # 前残りバイアス下で減点

            final_score = min(round(base_score + bias_score, 1), 99.9)

            # 危険な人気馬判定（人気順位上位かつ枠または脚質の複勝率が低迷している場合）
            is_dangerous = False
            danger_reason = ""
            if horse['popularity'] <= 2:
                if frame_rate <= 10.0:
                    is_dangerous = True
                    danger_reason = f"コース不振枠（{frame_num}：複勝率{frame_rate}%）に入った人気馬"
                elif track_bias_front and horse['style'] == '追込':
                    is_dangerous = True
                    danger_reason = "前残りバイアス下での後方一気脚質（追込）リスク"

            analyzed_horses.append({
                **horse,
                "frame_rate": frame_rate,
                "style_rate": style_rate,
                "score": final_score,
                "is_dangerous": is_dangerous,
                "danger_reason": danger_reason
            })

        # スコア順にソート（ランキング化）
        analyzed_horses.sort(key=lambda x: x['score'], reverse=True)
        return {"golden_pattern": golden_pattern, "horses": analyzed_horses}

analyzer = RaceAnalyzer()

@app.route('/')
def index():
    # 毎日王冠（東京・芝1800m）の出走馬データ例
    tokyo_horses = [
        {"num": 1, "name": "セイウンハーデス", "frame": 1, "style": "先行", "odds": 10.2, "popularity": 4},
        {"num": 2, "name": "リアライズシリウス", "frame": 1, "style": "差し", "odds": 2.7, "popularity": 1},
        {"num": 9, "name": "ドラゴンブースト", "frame": 5, "style": "差し", "odds": 29.7, "popularity": 9},
        {"num": 10, "name": "エルトンバローズ", "frame": 5, "style": "先行", "odds": 25.3, "popularity": 6},
        {"num": 13, "name": "ホウオウビスケッツ", "frame": 7, "style": "先行", "odds": 25.5, "popularity": 7},
        {"num": 17, "name": "ダノンエアズロック", "frame": 8, "style": "先行", "odds": 28.2, "popularity": 8},
    ]

    result = analyzer.analyze_race("東京・芝1800m", "古馬・オープン", tokyo_horses, track_bias_front=True)
    return render_template('index.html', race_title="毎日王冠（GII）データ分析ダッシュボード", data=result)

if __name__ == '__main__':
    app.run(debug=True)
