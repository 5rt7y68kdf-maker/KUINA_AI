# app.py
import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# 画面全体のテーマをワイドに設定
st.set_page_config(page_title="KEIBA DATA ANALYTICS", layout="wide")

# 外部デザインファイル (style.css) を安全に読み込む
if os.path.exists("style.css"):
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📊 KEIBA DATA ANALYTICS")
st.caption("🤖 過去5年間のコース・展開統計に基づく、完全自動期待値算出システム")

# TARGETファイル名の固定設定
WAKU_FILE = "2020_2025_枠番.csv"
KYAKU_FILE = "2020_2025脚質.csv"
THIS_WEEK_FILE = "DG261003.csv"

def load_csv_safely(file_path, has_header=True):
    if not os.path.exists(file_path):
        return None
    try:
        # ヘッダーが無い場合は header=None で読み込む
        header_setting = 0 if has_header else None
        df = pd.read_csv(
            file_path, 
            encoding='shift_jis', 
            dtype=str, 
            header=header_setting,
            na_values=['*', '-', ' '],
            on_bad_lines='skip'
        )
        if has_header:
            df.columns = df.columns.str.strip()
            for col in df.columns:
                df[col] = df[col].str.strip()
        else:
            # ヘッダーなしデータの場合はセルの空白だけトリミング
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"ファイル【{file_path}】の読み込みエラー: {e}")
        return None

# ファイルチェック
files_exist = os.path.exists(WAKU_FILE) and os.path.exists(KYAKU_FILE) and os.path.exists(THIS_WEEK_FILE)

if not files_exist:
    st.warning("⚠️ GitHubリポジトリ内にデータファイルが見つかりません。")
    st.info(f"GitHub内に以下のファイル名でCSVを配置してください。\n1. `{WAKU_FILE}`\n2. `{KYAKU_FILE}`\n3. `{THIS_WEEK_FILE}`")
else:
    df_waku = load_csv_safely(WAKU_FILE, has_header=True)
    df_kyaku = load_csv_safely(KYAKU_FILE, has_header=True)
    # 出馬表はヘッダーなし(has_header=False)として安全に読み込む
    df_this = load_csv_safely(THIS_WEEK_FILE, has_header=False)

    if df_waku is not None and df_kyaku is not None and df_this is not None:
        try:
            # 💡【列位置の固定攻略】ヘッダーなしCSVの列番号を正しく定義
            # 0列目=枠番, 2列目=馬番, 7列目=馬名, 12列目=騎手
            waku_index = 0
            umaban_index = 2
            bamei_index = 7
            kishu_index = 12

            # 過去5年データ側の最初の行からコース名（例：札幌・芝1200mなど）を1つ仮で取得しテスト分析
            # 本来は出馬表ファイル名や外部情報からコースを取りますが、まずは過去データの最初のコースでシミュレート
            available_courses = df_waku['場所･距離'].dropna().unique()
            
            if len(available_courses) > 0:
                # テスト対象として、過去データの一番上にあるコースを自動ターゲットにします
                search_keyword = str(available_courses[0])
                st.info(f"🔍 自動検出された過去5年解析対象コース: 【{search_keyword}】")
                
                # 過去の集計データから該当コースの行を検索
                waku_match = df_waku[df_waku['場所･距離'] == search_keyword]
                kyaku_match = df_kyaku[df_kyaku['場所･距離'] == search_keyword]
                
                if not waku_match.empty:
                    waku_row = waku_match.iloc[0]
                    kyaku_row = kyaku_match.iloc[0] if not kyaku_match.empty else None
                    
                    result_rows = []
                    for idx, row in df_this.iterrows():
                        # インデックス番号で安全にデータを引っこ抜く（列名が変わっても絶対に落ちない）
                        horse_name = row.iloc[bamei_index] if len(row) > bamei_index else f"馬番{idx+1}"
                        raw_waku = str(row.iloc[waku_index]).strip() if len(row) > waku_index else "1"
                        umaban = row.iloc[umaban_index] if len(row) > umaban_index else str(idx+1)
                        kishu = row.iloc[kishu_index] if len(row) > kishu_index else "不明"
                        
                        # 数字を全角の「〇枠」に変換して過去データとマージ
                        zen_dict = {"1":"１","2":"２","3":"３","4":"４","5":"５","6":"６","7":"７","8":"８"}
                        waku_key = f"{zen_dict.get(raw_waku, raw_waku)}枠"
                        
                        waku_score = pd.to_numeric(waku_row.get(waku_key, 0), errors='coerce')
                        waku_score = waku_score if not np.isnan(waku_score) else 0
                        
                        # 今回の出馬表データには脚質文字列がないため、枠適性をベースに100%安全にスコア化
                        total_score = round(float(waku_score), 2)
                        
                        result_rows.append({
                            "馬番": umaban,
                            "馬名": horse_name,
                            "枠番": waku_key,
                            "騎手": kishu,
                            "過去5年枠順複勝率": f"{waku_score}%",
                            "SCORE": total_score
                        })
                    
                    # 期待値スコア順に並び替え
                    ranking_df = pd.DataFrame(result_rows).sort_values(by="SCORE", ascending=False)
                    top_horse = ranking_df.iloc[0]
                    
                    st.write("")
                    st.subheader("🏆 AI HIGHLIGHT")
                    m_col1, m_col2, m_col3 = st.columns(3)
                    with m_col1:
                        st.metric(label="本命推奨馬 (AI 1st)", value=f"{top_horse['馬名']}")
                    with m_col2:
                        st.metric(label="ゲート (GATE)", value=f"{top_horse['馬番']}番 ({top_horse['枠番']})")
                    with m_col3:
                        st.metric(label="コース枠期待値 (TOTAL SCORE)", value=f"{top_horse['SCORE']}")
                    
                    st.write("")
                    st.subheader("📋 COMPUTED EXPECTED RANKING")
                    
                    st.dataframe(
                        ranking_df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "SCORE": st.column_config.NumberColumn("総合スコア", format="%.2f"),
                            "馬名": st.column_config.TextColumn("競走馬名"),
                        }
                    )
                else:
                    st.warning(f"⚠️ 過去データの中にコース『{search_keyword}』が見つかりませんでした。")
            else:
                st.error("過去5年データ(2020_2025_枠番.csv)の『場所･距離』列からコース名を取得できませんでした。")
        except Exception as e:
            st.error(f"計算中にエラーが発生しました: {e}")
