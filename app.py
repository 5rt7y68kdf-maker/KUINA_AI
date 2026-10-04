# app.py
import streamlit as st
import pandas as pd
import numpy as np
import os

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
    df_this = load_csv_safely(THIS_WEEK_FILE, has_header=False)

    if df_waku is not None and df_kyaku is not None and df_this is not None:
        try:
            # ヘッダーなしCSVの列位置を定義
            waku_index = 0   # 枠番
            umaban_index = 2 # 馬番
            bamei_index = 7  # 馬名
            kishu_index = 12 # 騎手

            # 💡【新検索機能】過去5年データ内にある「全てのコース名」を自動でリスト化
            all_courses = sorted(df_waku['場所･距離'].dropna().unique())
            
            # 🎯 画面最上部にコース選択の検索ドロップダウンを設置！
            selected_course = st.selectbox(
                "🏁 分析したい競馬場・コースを選択してください", 
                options=all_courses,
                index=0
            )
            
            st.info(f"🔍 選択中のコース: 【{selected_course}】")
            
            # 選択されたコースの行を過去データから抽出
            waku_match = df_waku[df_waku['場所･距離'] == selected_course]
            kyaku_match = df_kyaku[df_kyaku['場所･距離'] == selected_course]
            
            if not waku_match.empty:
                # 該当コースの一番上の条件（または全体の平均行）をベースに設定
                waku_row = waku_match.iloc[0]
                kyaku_row = kyaku_match.iloc[0] if not kyaku_match.empty else None
                
                result_rows = []
                for idx, row in df_this.iterrows():
                    # データの長さを安全にチェックして抽出
                    if len(row) > bamei_index:
                        horse_name = row.iloc[bamei_index]
                        raw_waku = str(row.iloc[waku_index]).strip()
                        umaban = row.iloc[umaban_index]
                        kishu = row.iloc[kishu_index]
                        
                        # 数字を全角の「〇枠」に変換
                        zen_dict = {"1":"１","2":"２","3":"３","4":"４","5":"５","6":"６","7":"７","8":"８"}
                        waku_key = f"{zen_dict.get(raw_waku, raw_waku)}枠"
                        
                        # 枠の複勝率スコアを取得
                        waku_score_raw = waku_row.get(waku_key, 0)
                        waku_score = pd.to_numeric(waku_score_raw, errors='coerce')
                        waku_score = waku_score if not np.isnan(waku_score) else 0
                        
                        total_score = round(float(waku_score), 2)
                        
                        result_rows.append({
                            "馬番": umaban,
                            "馬名": horse_name,
                            "枠番": waku_key,
                            "騎手": kishu,
                            "過去5年枠複勝率": f"{waku_score}%",
                            "AI期待値スコア": total_score
                        })
                
                if result_rows:
                    ranking_df = pd.DataFrame(result_rows).sort_values(by="AI期待値スコア", ascending=False)
                    top_horse = ranking_df.iloc[0]
                    
                    st.write("")
                    st.subheader("🏆 AI HIGHLIGHT")
                    m_col1, m_col2, m_col3 = st.columns(3)
                    with m_col1:
                        st.metric(label="本命推奨馬 (AI 1st)", value=f"{top_horse['馬名']}")
                    with m_col2:
                        st.metric(label="ゲート (GATE)", value=f"{top_horse['馬番']}番 ({top_horse['枠番']})")
                    with m_col3:
                        st.metric(label="コース適性期待値", value=f"{top_horse['AI期待値スコア']}%")
                    
                    st.write("")
                    st.subheader("📋 COMPUTED EXPECTED RANKING")
                    
                    st.dataframe(
                        ranking_df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "AI期待値スコア": st.column_config.NumberColumn("総合スコア", format="%.2f"),
                            "馬名": st.column_config.TextColumn("競走馬名"),
                        }
                    )
                else:
                    st.error("出馬表データの解析に失敗しました。")
            else:
                st.warning(f"⚠️ 過去データの中にコース『{selected_course}』の枠順データが見つかりませんでした。")
        except Exception as e:
            st.error(f"計算中にエラーが発生しました: {e}")
