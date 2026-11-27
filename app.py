import streamlit as st
import pandas as pd
import os

# 1. ページ基本設定
st.set_page_config(
    page_title="KUINA AI 競馬オンラインサロン",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. 金枠（Gold Border）＆フォント拡大カスタムCSS
st.markdown("""
<style>
    /* 全体背景と基本フォント */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* コンテナ幅調整 */
    .block-container {
        max-width: 860px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* 👑 金枠付きヒーローヘッダー */
    .hero-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #eab308;
        border-radius: 16px;
        padding: 35px 25px;
        text-align: center;
        box-shadow: 0 0 25px rgba(234, 179, 8, 0.25);
        margin-bottom: 30px;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 900;
        background: linear-gradient(90deg, #fef08a, #eab308, #ca8a04);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 12px;
        letter-spacing: 1px;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #e2e8f0;
        font-weight: 500;
    }

    /* 👑 金枠付きサロン機能カード */
    .feature-card {
        background: #1e293b;
        border: 1.5px solid #d97706;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 15px;
        height: 100%;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4), inset 0 0 10px rgba(234, 179, 8, 0.05);
    }
    .feature-card h4 {
        color: #fef08a;
        margin-top: 0;
        font-size: 1.25rem;
        font-weight: 700;
    }
    .feature-card p {
        color: #cbd5e1;
        font-size: 0.95rem;
        margin-bottom: 0;
        line-height: 1.6;
    }

    /* 👑 金枠＆グラデーション Stripe決済ボタン */
    .stripe-button {
        display: block;
        width: 100%;
        padding: 20px;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        border: 2px solid #fef08a;
        color: #ffffff !important;
        text-align: center;
        font-weight: 800;
        font-size: 1.35rem;
        text-decoration: none;
        border-radius: 12px;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4), 0 0 15px rgba(254, 240, 138, 0.3);
        transition: all 0.3s ease;
        margin: 25px 0;
    }
    .stripe-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.6), 0 0 20px rgba(254, 240, 138, 0.5);
    }

    /* 👑 金枠付き LINEボタン */
    .line-button {
        display: block;
        width: 100%;
        padding: 16px;
        background-color: #06C755;
        border: 1.5px solid #fef08a;
        color: #ffffff !important;
        text-align: center;
        font-weight: 800;
        font-size: 1.15rem;
        text-decoration: none;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(6, 199, 85, 0.3);
        margin: 12px 0;
    }

    /* 👑 金枠付き AI解析カード装飾 */
    .ai-card {
        background: #1e293b;
        border: 2px solid #eab308;
        border-radius: 16px;
        padding: 28px;
        margin-top: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(234, 179, 8, 0.2);
    }

    /* Streamlit標準パーツのダークモード＆金枠微調整 */
    .stTextInput > div > div > input {
        background-color: #0f172a;
        color: #f8fafc;
        border: 1.5px solid #ca8a04;
        font-size: 1.05rem;
    }
    .stSelectbox > div > div {
        background-color: #0f172a;
        color: #f8fafc;
        border: 1px solid #ca8a04;
    }
    .stTextArea > div > div > textarea {
        background-color: #0f172a;
        color: #f8fafc;
        border: 1.5px solid #ca8a04;
        font-size: 1rem;
    }
    .streamlit-expanderHeader {
        background-color: #1e293b;
        color: #fef08a !important;
        border: 1px solid #ca8a04 !important;
        border-radius: 8px;
        font-size: 1.05rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# 3. メインヘッダー
st.markdown("""
<div class="hero-header">
    <div class="hero-title">🤖 KUINA AI 競馬オンラインサロン</div>
    <div class="hero-subtitle">PC管理AIによる高精度データ解析 × 勝ち残るための初心者攻略コラム</div>
</div>
""", unsafe_allow_html=True)

# 4. サロンの3大特徴
st.markdown("### 💡 サロンのサービス内容")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>🔒 有料会員限定AI解析</h4>
        <p>重賞・厳選レースの6大ファクター数値化スコア＆推奨買い目をWeb会員エリアで公開！</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>📱 無料LINEオプチャ</h4>
        <p>開設済みの無料オープンチャットにて、週末2〜4レースの予想＆サロン更新情報を無料配信！</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h4>📚 有料会員限定コラム</h4>
        <p>初心者向けの必勝コラム（資金配分術・コース攻略・穴馬抽出法）を会員エリアにて全編配信。</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 5. 無料オープンチャット案内（設定いただいたオープンチャットURL）
st.markdown("### 🟢 無料LINEオープンチャット「競馬コミュニティ」")
st.write("どなたでも無料で参加できます！週末の**無料2〜4レース予想**やサロンの最新情報を配信中。")
FREE_LINE_OC_LINK = "https://line.me/ti/g2/5sJhEhBeLhBW6ojDFOZ1Ga0wabEz67_jAlYhQg?utm_source=invitation&utm_medium=link_copy&utm_campaign=default"
st.markdown(f'<a href="{FREE_LINE_OC_LINK}" target="_blank" class="line-button">💬 無料LINEオープンチャット「競馬コミュニティ」に参加する</a>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 6. 有料会員入会案内＆Stripe決済
st.markdown("### 💳 有料会員サロン（当サイト内で閲覧完結）")
st.markdown("## **月額会員プラン：1,980円 / 月（税込）**")
st.caption("※Stripe決済完了後の画面に「会員専用パスワード」が表示されます。下部の専用ログインエリアに入力することで、KUINA AI重賞フル解析および限定コラムを全編閲覧いただけます。")

STRIPE_PAYMENT_LINK = "https://buy.stripe.com/00w3cvelM35sahn9Er0sU00"
st.markdown(f'<a href="{STRIPE_PAYMENT_LINK}" target="_blank" class="stripe-button">⚡ 今すぐ有料会員になる（Stripe月額1,980円決済）</a>', unsafe_allow_html=True)

with st.expander("❓ クレジットカードをお持ちでない方のお支払い方法について"):
    st.markdown("""
    当サロンの決済（Stripe）では、クレジットカードのほか以下がご利用いただけます。
    * **Apple Pay / Google Pay**：スマホに登録された決済手段でワンタップ支払い。
    * **デビットカード**：各銀行のデビットカード（Visa/JCB等）がそのまま利用可能。
    * **プリペイドカード**：「バンドルカード」や「Kyash」などの即時発行プリペイドカードも対応。
    """)

st.markdown("<br>", unsafe_allow_html=True)

# 7. 無料公開：コラムの目次案内（全5回対応）
st.markdown("### 📖 会員限定 競身上達コラム（目次一覧）")
st.write("有料会員エリアでは、競馬初心者から勝ち組へステップアップするための**全5回・完全版コラム**を掲載・更新しています。")

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("""
    <div class="feature-card">
        <h4 style="color:#fef08a;">📌 第1回</h4>
        <p style="font-size:0.9rem;">トリガミを防ぐ「効率的な資金配分」の黄金比（合成オッズ計算・傾斜配分）</p>
    </div>
    """, unsafe_allow_html=True)
with col_b:
    st.markdown("""
    <div class="feature-card">
        <h4 style="color:#fef08a;">📌 第2回</h4>
        <p style="font-size:0.9rem;">全国競馬場・コース別の枠順＆バイアス攻略ガイド（馬場傾向の読み解き）</p>
    </div>
    """, unsafe_allow_html=True)
with col_c:
    st.markdown("""
    <div class="feature-card">
        <h4 style="color:#fef08a;">📌 第3回</h4>
        <p style="font-size:0.9rem;">データから導く「激走穴馬」の抽出テクニック（距離短縮・鞍上替わり等）</p>
    </div>
    """, unsafe_allow_html=True)

col_d, col_e, col_f = st.columns(3)
with col_d:
    st.markdown("""
    <div class="feature-card">
        <h4 style="color:#fef08a;">📌 第4回</h4>
        <p style="font-size:0.9rem;">パドック・気配で見抜く「危険な人気馬」の見分け方（馬体重・気性・指数見切り）</p>
    </div>
    """, unsafe_allow_html=True)
with col_e:
    st.markdown("""
    <div class="feature-card">
        <h4 style="color:#fef08a;">📌 第5回</h4>
        <p style="font-size:0.9rem;">騎手×コース相性データから狙う勝負レース選定法（コースマスター騎手狙い）</p>
    </div>
    """, unsafe_allow_html=True)
with col_f:
    st.markdown("""
    <div class="feature-card">
        <h4 style="color:#fef08a;">🎁 次回予告</h4>
        <p style="font-size:0.9rem;">【第6回】重賞レース専用：AI指数を活用した高回収率3連複フォーメーション構築術</p>
    </div>
    """, unsafe_allow_html=True)

st.info("💡 各コラムの全編本文は、以下の「有料会員専用エリア」にてご覧いただけます。")

st.markdown("<br>", unsafe_allow_html=True)

# 8. 🏇 コース別データ＆騎手相性ガイド（検索・自動読み込み）
st.markdown("### 🏇 全国コース別攻略 ＆ 騎手相性データ分析")
st.write("会場・馬場・距離を選択すると、リポジトリにアップロードされたCSVから**該当コースの「得意騎手データ」**を自動検出して表示します。")

col_v, col_t, col_d_sel = st.columns(3)
with col_v:
    venue_sel = st.selectbox("競馬場", ["東京", "中山", "阪神", "京都", "札幌", "函館", "福島", "新潟", "中京", "小倉"])
with col_t:
    track_sel = st.selectbox("馬場", ["ダート", "芝"])
with col_d_sel:
    dist_sel = st.selectbox("距離区分", ["～1300", "1400～1600", "1700～2000", "2100～2400", "2500～"])

# CSVファイルの動的検索処理
csv_filename = f"{venue_sel}{track_sel}{dist_sel}騎手.csv"
possible_csv_paths = [
    f"/workspace/knowledge/{csv_filename}",
    f"./{csv_filename}",
    csv_filename
]

jockey_df = None
for p in possible_csv_paths:
    if os.path.exists(p):
        try:
            jockey_df = pd.read_csv(p, encoding='cp932')
        except:
            jockey_df = pd.read_csv(p, encoding='utf-8')
        break

if jockey_df is not None:
    st.success(f"📊 【データ連携完了】{venue_sel}{track_sel}{dist_sel}m の騎手成績データを抽出しました！")
    
    try:
        df_display = jockey_df.copy()
        df_display['複勝率_num'] = df_display['複勝率'].astype(str).str.rstrip('%').apply(pd.to_numeric, errors='coerce')
        df_display['勝率_num'] = df_display['勝率'].astype(str).str.rstrip('%').apply(pd.to_numeric, errors='coerce')
        df_display['騎乗数'] = df_display['着別度数'].astype(str).str.split('/').str[1].str.strip().apply(pd.to_numeric, errors='coerce').fillna(0)
        
        # 騎乗数10回以上のTOP5騎手
        top5_df = df_display[df_display['騎乗数'] >= 10].sort_values(by='複勝率_num', ascending=False).head(5)
        
        st.markdown(f"#### 🏆 {venue_sel}{track_sel}{dist_sel}m 複勝率TOP5騎手ランキング")
        
        cols_to_show = ['順位', '騎手', '着別度数', '勝率', '連対率', '複勝率', '単勝回収値', '複勝回収値']
        existing_cols = [c for c in cols_to_show if c in top5_df.columns]
        st.dataframe(top5_df[existing_cols], use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.dataframe(jockey_df.head(10), use_container_width=True)
else:
    st.info(f"💡 『{csv_filename}』のCSVデータは準備中です。GitHubへファイルをアップロードすると自動反映されます。")

st.markdown("<br>", unsafe_allow_html=True)

# 9. 有料会員専用エリア（パスワード認証・サイト完結）
st.markdown("### 🔒【有料会員専用エリア】AI解析データ ＆ 限定コラム")

if 'member_pass' not in st.session_state:
    st.session_state.member_pass = "kuina2026"
if 'ai_text' not in st.session_state:
    st.session_state.ai_text = """💎【KUINA AI 厳選レース解析】 2026-11-22 【京都】 11R マイルCS G1 [芝1600m] (18頭立) (良)
━━━━━━━━━━━━━━━━━━━━━━━━━━
【AI推奨予想印】
🥇 ◎ 4枠8番 ロデオドライブ (AIスコア: 107.0pt)
🥈 ◯ 1枠2番 エンブロイダリー (AIスコア: 104.0pt)
▲ 4枠7番 ココナッツブラウン (AIスコア: 98.5pt)
⭐ △ 3枠6番 ピコローズ, 2枠3番 ドラゴンブースト, 1枠1番 エルデナリ

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊【本命馬 (ロデオドライブ) AI全6ファクター完全解析】

1. 🚩 枠順・配置 & バイアス
 ➔ データ: 4枠8番 (中枠/18頭立) ｜ バイアス: 内伸び・内前有利
 ➔ 採点: +12.0 pt
 ➔ 解説: 自在性の高い4枠（中枠）。展開に応じたポジション取りがしやすく包まれるリスクも低い好配置。

2. 🌧️ 馬場・道悪適性
 ➔ データ: 当日馬場: 良 (標準)
 ➔ 採点: 0.0 pt
 ➔ 解説: 良馬場開催につき、スピード・瞬発力（上り性能）をフルに発揮できる好条件です。

3. 📏 距離推移・適性
 ➔ データ: 今回: 1600m (距離短縮(-400m))
 ➔ 採点: +3.0 pt
 ➔ 解説: 前走2000mから400mの距離短縮。追走ペースが楽になり末脚爆発の期待大。

4. ⚡ 脚質・展開適合
 ➔ データ: 想定脚質【先行】 × 想定ペース【ミドル】
 ➔ 採点: +4.0 pt
 ➔ 解説: 平均ミドルペース適合。好位～中団（先行）から確実に脚を使う展開適合度トップクラス。

5. 🏇 騎手・コース相性
 ➔ データ: 鞍上: モレイラ騎手 (当コース成績: 単勝率 23.1% / 複勝率 69.2%)
 ➔ 採点: +8.0 pt
 ➔ 解説: 当コース複勝率69.2%(単勝率23.1%)の絶対的コースマスター。仕掛け処の精度絶大。

6. 📈 近走短評 (深掘り分析)
 ➔ データ: 近5走成績: 複勝率 100.0% ｜ 前走: 2着(差0.0秒)
 ➔ 採点: +10.0 pt
 ➔ 解説: 近5走で【複勝率100.0%】。決め手・能力ともにクラス高水準の深掘り評価。

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯【AI推奨フォーメーション】
■ 馬連: 8 - 2, 7, 6, 3, 1
■ 馬単: 8 ➔ 2, 7, 6, 3, 1
■ ワイド: 8 - 2, 7
■ 3連複: 8 - 2 - 7, 6, 3, 1
■ 3連単: 8 ➔ 2, 7 ➔ 2, 7, 6, 3, 1

※馬券の購入はご自身の責任のもとお楽しみください。"""

user_input_pass = st.text_input("🔑 Stripe決済後に表示された「会員用パスワード」を入力してください", type="password")

if user_input_pass == st.session_state.member_pass:
    st.success("🔓 会員認証成功！限定解析データおよび会員限定コラムを表示しています。")
    
    st.markdown('<div class="ai-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='font-size:1.6rem; color:#fef08a;'>🤖 KUINA AI 重賞フル解析</h3>", unsafe_allow_html=True)
    st.markdown(st.session_state.ai_text)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='font-size:1.6rem; color:#fef08a;'>📚 会員限定 競身上達コラム（全5編・完全版）</h3>", unsafe_allow_html=True)
    
    with st.expander("📖 【第1回】トリガミを防ぐ「効率的な資金配分」の黄金比", expanded=True):
        st.markdown("""
        競馬で長期的に勝ち越すための最大のコツは、**「当てること」以上に「不的中時の資金を無駄に減らさず、本線でしっかり回収すること」**です。
        
        * **合成オッズ2.0倍以上を必ずキープする**: 買い目全体の平均オッズを意識し、トリガミ（当たってもマイナス）を防止。
        * **資金の傾斜配分**: 期待値の高い「本線」に資金の6〜7割を投入し、高配当狙いの「穴目」は少額でカバー。
        * **見切る勇気**: AI指数・適正オッズを下回った買い目は勇気を持って切ることで、回収率を飛躍的に高められます。
        """)

    with st.expander("📖 【第2回】全国競馬場・コース別の枠順＆バイアス攻略ガイド"):
        st.markdown("""
        コースごとの「有利・不利」を事前に把握しておくことで、馬券の精度は劇的に上がります。
        
        * **東京芝1600m**: 枠順による有利不利は少ないが、直線が長いため上り3Fの速さが最重要。
        * **中山芝2000m**: 1コーナーまでの距離が短いため、**内枠（1〜3枠）の逃げ・先行馬**が圧倒的有利。
        * **阪神ダート1400m**: 芝スタートのため、**外枠（7〜8枠）**の方が芝を長く走れてスピードに乗りやすい。
        """)

    with st.expander("📖 【第3回】データから導く「激走穴馬」の抽出テクニック"):
        st.markdown("""
        単勝人気にとらわれず、PCデータから「潜んだ実力馬」を見つけ出すポイントです。
        
        * **前走の距離短縮・延長による一変**: 得意距離に戻ったレースでの巻き返し。
        * **トラックバイアス（馬場傾向）の逆行**: 前走不利な大外を回された馬の内枠替わり。
        * **コース得意騎手への乗り替わり**: 勝率・複勝率が極端に高い騎手への手戻り。
        """)

    with st.expander("📖 【第4回】パドック・気配で見抜く「危険な人気馬」の見分け方"):
        st.markdown("""
        人気が集まりながらも飛ばしやすい過剰人気馬を排除し、回収率を高めるテクニックです。
        
        * **馬体重の極端な増減**: ＋10kg以上の太め残りや、輸送減りによる激減（-10kg以上）は能力を発揮しにくい危険信号。
        * **パドックでの踏み込みと発汗**: チャカチャカして入れ込んでいる馬や、首を極端に振って集中を欠く人気馬は消し判断。
        * **AIデータ数値との剥離**: 単勝1〜2番人気でも、KUINA AIの6ファクター数値が著しく低い馬は期待値不足としてカット。
        """)

    with st.expander("📖 【第5回】騎手×コース相性データから狙う勝負レース選定法"):
        st.markdown("""
        騎手（鞍上）のコース得意・不得意を数値化し、軸馬の信頼度を高めるロジックです。
        
        * **コースマスター騎手の狙い撃ち**: 当コースでの複勝率50%超・単勝率20%超の騎手（例：モレイラ騎手、川田騎手等）が上位人気の馬に乗った際の軸順位繰り上げ。
        * **トップジョッキーへの手戻り乗り替わり**: 前走不調だった馬が、当コース好相性のトップ騎手に乗り替わったタイミングの急激な一変。
        * **展開・仕掛け処の精度**: 直線が短いコース（中山・小倉等）で早期仕掛けが得意な騎手と、先行力のある馬の組み合わせを重視。
        """)

else:
    st.info("🔒 会員用パスワードを入力すると、ここに「KUINA AI 重賞フル解析データ」および「限定コラム（全編）」が表示されます。")

st.markdown("<br>", unsafe_allow_html=True)

# 10. 運営者専用エリア
with st.expander("⚙️ 運営者専用：KUINA AI テキスト更新・パスワード設定"):
    st.write("PCで生成されたKUINA AIの解析テキストの更新や、会員用パスワードの設定ができます。")
    new_pass = st.text_input("会員用パスワードの設定", value=st.session_state.member_pass)
    input_text = st.text_area("KUINA AI出力テキスト全貼り付け", value=st.session_state.ai_text, height=200)
    
    if st.button("🚀 サイトの情報を更新する", type="primary"):
        st.session_state.member_pass = new_pass
        st.session_state.ai_text = input_text
        st.success("予想データおよび会員パスワードを更新しました！")
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# 11. 免責事項・特商法表記
with st.expander("⚖️ 免責事項・特定商取引法に基づく表記"):
    st.markdown("""
    **【免責事項】**  
    当サロンで提供するAI予想データ、コラム、配信コンテンツは情報提供および考察の共有を目的としており、馬券の的中や利益を保証するものではありません。馬券の購入および投資の最終決定は、ご自身の責任と判断において行ってください。万が一損害が発生した場合でも、当サロンおよび運営者は一切の責任を負いかねます。  

    **【特定商取引法に基づく表記】**  
    - **事業者名**: [ご自身の氏名または屋号]  
    - **運営責任者**: [代表者氏名]  
    - **所在地**: [請求があった場合に遅滞なく開示します]  
    - **連絡先メールアドレス**: [お問い合わせ用メールアドレス]  
    - **販売価格**: 月額 1,980円（税込）  
    - **お支払い方法**: クレジットカード決済（Stripe / Apple Pay / Google Pay / デビットカード / プリペイドカード）  
    - **役務の提供時期**: Stripeでの決済完了後, 即時（会員パスワードの発行による限定ページの閲覧権限）  
    - **解約・返金について**: クレジットカード決済のマイページよりいつでも次回更新の停止（解約）が可能です。サービスの性質上、決済完了後の返金・日割り計算には応じかねます。
    """)
