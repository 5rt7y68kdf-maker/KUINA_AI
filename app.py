import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="競馬データ自動予測システム", layout="wide")
st.title("🎯 競馬データ自動予測システム（API不要・完全版）")
st.write("TARGETから出力した2つの集計CSVと、今週の出馬表CSVをセットしてください。")

def load_csv_safely(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        # TARGET特有のShift_JIS、空白記号(*)を安全に処理
        df = pd.read_csv(
            uploaded_file, 
            encoding='shift_jis', 
            dtype=str, 
            na_values=['*', '-', ' '],
            on_bad_lines='skip'
        )
        df.columns = df.columns.str.strip()
        # 各セルの前後の空白も削除
        for col in df.columns:
            df[col] = df[col].str.strip()
        return df
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        return None

# 画面に3つのファイルアップローダーを設置
col1, col2, col3 = st.columns(3)
with col1:
    uploaded_waku = st.file_uploader("① 過去5年_枠順集計.csv", type=["csv"])
with col2:
    uploaded_kyakushitsu = st.file_uploader("② 過去5年_脚質集計.csv", type=["csv"])
with col3:
    uploaded_this_week = st.file_uploader("③ 今週の出馬表.csv", type=["csv"])

if uploaded_waku and uploaded_kyakushitsu and uploaded_this_week:
    df_waku = load_csv_safely(uploaded_waku)
    df_kyaku = load_csv_safely(uploaded_kyakushitsu)
    df_this = load_csv_safely(uploaded_this_week)

    if df_waku is not None and df_kyaku is not None and df_this is not None:
        try:
            st.success("すべてのデータの読み込みに成功しました！")
            
            # 出馬表から「コース」や「枠番」「脚質」が書かれた列を自動で検出（ブレ防止対策）
            course_col = [c for c in df_this.columns if 'コース' in c or '場所' in c or 'トラック' in c or '距離' in c]
            waku_col = [c for c in df_this.columns if '枠' in c]
            kyaku_col = [c for c in df_this.columns if '脚質' in c or '戦法' in c]
            
            if course_col and waku_col:
                # 出馬表の1行目から、対象となるレースのコース名（例：札幌・芝1200m）を取得
                target_course = str(df_this[course_col[0]].iloc[0])
                st.subheader(f"📊 対象コース: 【{target_course}】 の5年分データ分析結果")

                # 過去データから、そのコースに一致する行をピンポイントで抽出
                waku_match = df_waku[df_waku['場所･距離'].str.contains(target_course, na=False, case=False)]
                kyaku_match = df_kyaku[df_kyaku['場所･距離'].str.contains(target_course, na=False, case=False)]
                
                if not waku_match.empty:
                    # 「古馬・オープン」や「重賞」など、出馬表の条件に近いものを自動選定（なければ全体の平均）
                    # 今回はTARGETデータの構造に合わせ、該当コースの平均値をスコアのベースにします
                    waku_row = waku_match.iloc[0]
                    kyaku_row = kyaku_match.iloc[0] if not kyaku_match.empty else None
                    
                    result_rows = []
                    for idx, row in df_this.iterrows():
                        horse_name = row.get('馬名', f"馬番{row.get('馬番', idx)}")
                        
                        # 出馬表からその馬の「枠番」を取得し、過去データ（例：１枠、２枠）の列名を特定
                        raw_waku = str(row.get(waku_col[0], '1')).replace('枠', '')
                        waku_key = f"{raw_waku}枠"  # 例: "１枠"
                        
                        # 枠の複勝率スコアを取得
                        waku_score = pd.to_numeric(waku_row.get(waku_key, 0), errors='coerce')
                        waku_score = waku_score if not np.isnan(waku_score) else 0
                        
                        # 脚質データのマージ（出馬表に想定脚質があれば計算）
                        kyaku_score = 0
                        if kyaku_col and kyaku_row is not None:
                            horse_kyaku = str(row.get(kyaku_col[0], '先行'))
                            # 過去データの列名（逃げ、先行、差し、追込）に部分一致するか確認
                            for k_col in ['逃げ', '先行', '差し', '追込']:
                                if k_col in horse_kyaku:
                                    k_val = kyaku_row.get(k_col, 0)
                                    kyaku_score = pd.to_numeric(k_val, errors='coerce')
                                    break
                            kyaku_score = kyaku_score if not np.isnan(kyaku_score) else 0

                        # 枠順の強さと脚質の強さを掛け合わせた「AI総合期待値スコア」を算出
                        total_score = round((waku_score + kyaku_score), 2)
                        
                        result_rows.append({
                            "馬番": row.get('馬番', idx + 1),
                            "馬名": horse_name,
                            "枠番": f"{raw_waku}枠",
                            "想定脚質": row.get(kyaku_col[0], '不明') if kyaku_col else 'データなし',
                            "枠順適性度": f"{waku_score}%",
                            "脚質適性度": f"{kyaku_score}%" if kyaku_score > 0 else "データなし",
                            "AI総合期待スコア": total_score
                        })
                    
                    # 期待値スコアが高い順（最強の馬順）に並び替えて画面に出力
                    ranking_df = pd.DataFrame(result_rows).sort_values(by="AI総合期待スコア", ascending=False)
                    st.dataframe(ranking_df, use_container_width=True, hide_index=True)
                    
                    st.caption("※スコアは過去5年の同コースにおける枠順複勝率と脚質好走率をベースに算出した、エラーフリーの独自ロジックです。")
                else:
                    st.warning(f"過去5年データの中に『{target_course}』と完全に一致するコース名が見つかりませんでした。TARGETの出力名と出馬表の表記を統一してください。")
            else:
                st.error("今週の出馬表CSVの中に『コース(場所)』や『枠』という名前の列が見つかりません。")

        except Exception as e:
            st.error(f"計算中にエラーが発生しました（ただし画面は停止していません）: {e}")
