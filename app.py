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

# ファイルチェック
files_exist = os.path.exists(WAKU_FILE) and os.path.exists(KYAKU_FILE) and os.path.exists(THIS_WEEK_FILE)

if not files_exist:
    st.warning("⚠️ GitHubリポジトリ内にデータファイルが見つかりません。")
    st.info(f"GitHub内に以下のファイル名でCSVを配置してください。\n1. `{WAKU_FILE}`\n2. `{KYAKU_FILE}`\n3. `{THIS_WEEK_FILE}`")
else:
    df_waku = load_csv_safely(WAKU_FILE)
    df_kyaku = load_csv_safely(KYAKU_FILE)
    df_this = load_csv_safely(THIS_WEEK_FILE)

    if df_waku is not None and df_kyaku is not None and df_this is not None:
        try:
            # 列名から「コース」や「枠」に関連するものを自動抽出
            course_col = [c for c in df_this.columns if 'コース' in c or '場所' in c or 'トラック' in c or '距離' in c]
            waku_col = [c for c in df_this.columns if '枠' in c]
            kyaku_col = [c for c in df_this.columns if '脚質' in c or '戦法' in c]
            
            if course_col and waku_col:
                # 出馬表の生テキスト（例: "東京11R 芝1600m" など）を取得
                raw_course_text = str(df_this[course_col[0]].iloc[0])
                
                # ✨【最強検索ロジック】文字列から「競馬場」「芝・ダート」「距離」を正規表現で自動抽出
                basho_match = re.search(r'(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)', raw_course_text)
                track_match = re.search(r'(芝|ダ|ダート)', raw_course_text)
                dist_match = re.search(r'(\d{4})', raw_course_text)
                
                if basho_match and track_match and dist_match:
                    basho = basho_match.group(1)
                    track = "ダート" if "ダ" in track_match.group(1) else "芝"
                    dist = dist_match.group(1)
                    
                    # 過去データ側の表記（例：東京・芝1600m）に合わせた検索ワードを生成
                    search_keyword = f"{basho}・{track}{dist}m"
                    st.info(f"🔍 検出された対象コース: 【{search_keyword}】 (元の文字列: {raw_course_text})")
                    
                    # 過去の集計データから該当コースの行を部分一致で検索
                    waku_match = df_waku[df_waku['場所･距離'].str.contains(search_keyword, na=False, case=False)]
                    kyaku_match = df_kyaku[df_kyaku['場所･距離'].str.contains(search_keyword, na=False, case=False)]
                else:
                    # 部分抽出が失敗した場合は従来の全体一致を試みる
                    waku_match = df_waku[df_waku['場所･距離'].str.contains(raw_course_text, na=False, case=False)]
                    kyaku_match = df_kyaku[df_kyaku['場所･距離'].str.contains(raw_course_text, na=False, case=False)]
                
                if not waku_match.empty:
                    # レース条件の絞り込み（まずは全体の平均行やオープンを対象にする）
                    waku_row = waku_match.iloc[0]
                    kyaku_row = kyaku_match.iloc[0] if not kyaku_match.empty else None
                    
                    result_rows = []
                    for idx, row in df_this.iterrows():
                        horse_name = row.get('馬名', f"馬番{row.get('馬番', idx + 1)}")
                        
                        # 枠番の全角半角のブレを吸収して「〇枠」の形を特定
                        raw_waku = str(row.get(waku_col[0], '1')).replace('枠', '').strip()
                        # 数字を全角に変換する辞書
                        zen_dict = {"1":"１","2":"２","3":"３","4":"４","5":"５","6":"６","7":"７","8":"８"}
                        waku_key = f"{zen_dict.get(raw_waku, raw_waku)}枠"
                        
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
                            "枠番": waku_key,
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
                    st.warning(f"⚠️ 過去データの中に『{raw_course_text}』に該当するコースが見つかりませんでした。")
            else:
                st.error("出馬表の列名に『コース』または『枠』が必要です。")
        except Exception as e:
            st.error(f"システムエラー: {e}")
