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

# 💡 【改善点】ファイルを固定の名前で自動読み込みするように設定
WAKU_FILE = "過去5年_枠順集計.csv"
KYAKU_FILE = "過去5年_脚質集計.csv"
THIS_WEEK_FILE = "今週の出馬表.csv"

def load_csv_safely(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_csv(
            file_path, 
            encoding='shift_jis', 
            dtype=str, 
            na_values=['*', '-', ' '],
            on_bad_lines='skip'
        )
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].str.strip()
        return df
    except Exception as e:
        st.error(f"ファイル【{file_path}】の読み込みエラー: {e}")
        return None

# ファイルが揃っているかチェック
files_exist = os.path.exists(WAKU_FILE) and os.path.exists(KYAKU_FILE) and os.path.exists(THIS_WEEK_FILE)

if not files_exist:
    st.warning("⚠️ GitHub（リポジトリ）の中にデータファイルが見つかりません。")
    st.info(f"GitHubの同じフォルダ内に、以下の【3つの日本語ファイル名】でCSVを配置してプッシュしてください。\n\n"
            f"1. `{WAKU_FILE}`\n"
            f"2. `{KYAKU_FILE}`\n"
            f"3. `{THIS_WEEK_FILE}`")
else:
    # 画面を開いた瞬間に自動でファイルを読み込む
    df_waku = load_csv_safely(WAKU_FILE)
    df_kyaku = load_csv_safely(KYAKU_FILE)
    df_this = load_csv_safely(THIS_WEEK_FILE)

    if df_waku is not None and df_kyaku is not None and df_this is not None:
        try:
            course_col = [c for c in df_this.columns if 'コース' in c or '場所' in c or 'トラック' in c or '距離' in c]
            waku_col = [c for c in df_this.columns if '枠' in c]
            kyaku_col = [c for c in df_this.columns if '脚質' in c or '戦法' in c]
            
            if course_col and waku_col:
                target_course = str(df_this[course_col].iloc[0])
                st.info(f"ANALYSIS COURSE: {target_course}")

                waku_match = df_waku[df_waku['場所･距離'].str.contains(target_course, na=False, case=False)]
                kyaku_match = df_kyaku[df_kyaku['場所･距離'].str.contains(target_course, na=False, case=False)]
                
                if not waku_match.empty:
                    waku_row = waku_match.iloc[0]
                    kyaku_row = kyaku_match.iloc[0] if not kyaku_match.empty else None
                    
                    result_rows = []
                    for idx, row in df_this.iterrows():
                        horse_name = row.get('馬名', f"馬番{row.get('馬番', idx)}")
                        raw_waku = str(row.get(waku_col[0], '1')).replace('枠', '')
                        waku_key = f"{raw_waku}枠"
                        
                        waku_score = pd.to_numeric(waku_row.get(waku_key, 0), errors='coerce')
                        waku_score = waku_score if not np.isnan(waku_score) else 0
                        
                        kyaku_score = 0
                        if kyaku_col and kyaku_row is not None:
                            horse_kyaku = str(row.get(kyaku_col[0], '先行'))
                            for k_col in ['逃げ', '先行', '差し', '追込']:
                                if k_col in horse_kyaku:
                                    k_val = kyaku_row.get(k_col, 0)
                                    kyaku_score = pd.to_numeric(k_val, errors='coerce')
                                    break
                            kyaku_score = kyaku_score if not np.isnan(kyaku_score) else 0

                        total_score = round((waku_score + kyaku_score), 2)
                        
                        result_rows.append({
                            "馬番": row.get('馬番', idx + 1),
                            "馬名": horse_name,
                            "枠番": f"{raw_waku}枠",
                            "想定脚質": row.get(kyaku_col[0], '-') if kyaku_col else '-',
                            "枠適性": waku_score,
                            "展開適性": kyaku_score,
                            "SCORE": total_score
                        })
                    
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
                        st.metric(label="総合期待値 (TOTAL SCORE)", value=f"{top_horse['SCORE']}")
                    
                    st.write("")
                    st.subheader("📋 COMPUTED EXPECTED RANKING")
                    
                    display_df = ranking_df.copy()
                    display_df["枠適性"] = display_df["枠適性"].astype(str) + "%"
                    display_df["展開適性"] = display_df["展開適性"].astype(str) + "%"
                    
                    st.dataframe(
                        display_df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "SCORE": st.column_config.NumberColumn("総合スコア", format="%.2f"),
                            "馬名": st.column_config.TextColumn("競走馬名"),
                        }
                    )
                else:
                    st.warning(f"過去データにコース『{target_course}』が見つかりません。")
            else:
                st.error("出馬表の列名に『コース』または『枠』が必要です。")
        except Exception as e:
            st.error(f"システムエラー（自動復旧済み）: {e}")
