python
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="競馬データ自動予測システム", layout="wide")
st.title("🎯 競馬データ自動予測システム（API不要版）")
st.write("TARGETから出力した2つの集計CSVと今週の出馬表（CSV）をセットしてください。")

# 1. 鉄壁のデータ読み込み関数（型エラー・文字化けを強制スルー）
def load_csv_safely(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        df = pd.read_csv(
            uploaded_file, 
            encoding='shift_jis', 
            dtype=str, 
            na_values=['*', '-', ' '],
            on_bad_lines='skip'
        )
        # 列名とデータをキレイにトリミング
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        return None

# 2. 画面上のファイルアップローダー
col1, col2, col3 = st.columns(3)
with col1:
    uploaded_waku = st.file_uploader("① 過去5年_枠順集計.csv", type=["csv"])
with col2:
    uploaded_kyakushitsu = st.file_uploader("② 過去5年_脚質集計.csv", type=["csv"])
with col3:
    uploaded_this_week = st.file_uploader("③ 今週の出馬表.csv (レース名・馬番・枠番・脚質を含むもの)", type=["csv"])

# 3. 3つのファイルが揃ったらPythonだけで高速計算
if uploaded_waku and uploaded_kyakushitsu and uploaded_this_week:
    df_waku = load_csv_safely(uploaded_waku)
    df_kyaku = load_csv_safely(uploaded_kyakushitsu)
    df_this = load_csv_safely(uploaded_this_week)

    if df_waku is not None and df_kyaku is not None and df_this is not None:
        try:
            st.success("すべてのデータの読み込みに成功しました！計算を開始します。")

            # 例として、今週の出馬表の1レース目を対象にします
            # ※出馬表CSVに「コース名」（例：東京芝1600）という列があると仮定
            course_col = [c for c in df_this.columns if 'コース' in c or 'トラック' in c]
            waku_col = [c for c in df_this.columns if '枠' in c]
            
            if course_col and waku_col:
                target_course = df_this[course_col[0]].iloc[0]
                st.subheader(f"📊 対象コース: {target_course} の分析結果")

                # 過去5年データから、該当コースの行を自動検索
                # 1列目にコース名が入っていると仮定して検索します
                waku_match = df_waku[df_waku.iloc[:, 0].str.contains(target_course, na=False, case=False)]
                
                if not waku_match.empty:
                    st.write("💡 過去5年の該当コースデータを検出しました。")
                    
                    # ここで出馬表の各馬に対して、過去の枠順複勝率を自動マージしてスコア化
                    # エラーを防ぐため、存在しない枠は自動的にスコア0にします
                    result_rows = []
                    for idx, row in df_this.iterrows():
                        horse_name = row.get('馬名', f"馬番{row.get('馬番', idx)}")
                        horse_waku = str(row.get(waku_col[0], '1'))
                        
                        # 過去データからその枠の数値を引っ張る（「複勝率」と書かれた列などを自動判定）
                        # ここでは簡易的に、枠番と一致する列の数値を参照
                        score = 0
                        for col in waku_match.columns:
                            if horse_waku in col and ('率' in col or '複' in col):
                                score = pd.to_numeric(waku_match[col].iloc[0], errors='coerce')
                                break
                        
                        result_rows.append({
                            "馬番": row.get('馬番', '-'),
                            "馬名": horse_name,
                            "枠番": horse_waku,
                            "過去5年枠複勝率スコア": score if not np.isnan(score) else 0
                        })
                    
                    # ランキング表にして画面に表示
                    ranking_df = pd.DataFrame(result_rows).sort_values(by="過去5年枠複勝率スコア", ascending=False)
                    st.dataframe(ranking_df, use_container_width=True)
                else:
                    st.warning(f"過去データの中に『{target_course}』と完全に一致するコース名が見つかりませんでした。TARGETの出力名を確認してください。")
            else:
                st.error("今週の出馬表CSVの中に『コース』や『枠』という名前の列が見つかりません。")

        except Exception as e:
            st.error(f"計算中にエラーが発生しました（アプリは停止していません）: {e}")
# KUINA_AI
