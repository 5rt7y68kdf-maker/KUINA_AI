import streamlit as st

# 1. ページ基本設定
st.set_page_config(
    page_title="KUINA AI 競馬オンラインサロン",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. デザインカスタム（CSS）
st.markdown("""
<style>
    .main-title {
        font-size: 1.9rem;
        font-weight: 800;
        color: #1A365D;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #4A5568;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .stripe-button {
        display: block;
        width: 100%;
        padding: 16px;
        background-color: #2F855A;
        color: white !important;
        text-align: center;
        font-weight: bold;
        font-size: 1.15rem;
        text-decoration: none;
        border-radius: 8px;
        box-shadow: 0 4px 14px rgba(47,133,90,0.35);
        margin: 20px 0;
    }
    .feature-card {
        background-color: #EDF2F7;
        padding: 16px;
        border-radius: 8px;
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 3. ヘッダー表示
st.markdown('<div class="main-title">🤖 KUINA AI 競馬オンラインサロン</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">PC管理AIによる高精度データ解析 × 勝ち残るための初心者攻略コラム</div>', unsafe_allow_html=True)

st.divider()

# 4. サロンの3大特徴
st.subheader("💡 サロンで提供する3つの特徴")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>📊 PC管理AI予想</h4>
        <p style="font-size:0.85rem; color:#4A5568;">枠・馬場・距離・脚質・騎手・近走の6大ファクターを数値化したAIスコアと推奨買い目を公開。</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>📱 LINEオプチャ配信</h4>
        <p style="font-size:0.85rem; color:#4A5568;">重賞予想＋無料で週末2〜4レースを配信！当日の馬場・パドック気配に応じた直前速報を受信。</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h4>📚 コラム完全公開</h4>
        <p style="font-size:0.85rem; color:#4A5568;">初心者向けの必勝コラム（資金配分術・コース攻略・穴馬抽出法）を当サイトにて全編完全公開。</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# 5. 入会案内＆Stripe決済ボタン（月額1,980円）
st.subheader("💳 サロン入会案内")
st.markdown("### **月額会員プラン：1,980円 / 月（税込）**")
st.caption("※Stripeでの決済完了後、限定LINEオープンチャット（重賞予想＆無料2〜4レース配信）へ即時ご案内いたします。")

# Stripeで発行した「1,980円/月」のPayment Link URLを下記に入力してください
STRIPE_PAYMENT_LINK = "YOUR_STRIPE_PAYMENT_LINK_HERE"

st.markdown(f'<a href="{STRIPE_PAYMENT_LINK}" target="_blank" class="stripe-button">今すぐサロンに入会する（Stripe月額1,980円決済）</a>', unsafe_allow_html=True)

st.divider()

# 6. 最新AI予想データのセッション状態管理
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

# 最新AI解析データ表示エリア
st.subheader("💎【最新】KUINA AI 厳選レース解析")
if st.session_state.ai_text:
    st.markdown(st.session_state.ai_text)
else:
    st.info("※最新の予想データは準備中です。週末に更新されます。")

st.divider()

# 7. 初心者向けコラムコーナー（サイトにて完全公開）
st.subheader("📚 初心者向け競馬上達コラム（当サイトにて完全公開中）")

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

st.divider()

# 8. 運営者専用：KUINA AI テキスト貼り付け・一発更新フォーム
with st.expander("⚙️ 運営者専用：KUINA AI テキスト貼り付け・更新フォーム"):
    st.write("PCで生成されたKUINA AIの解析テキストをそのまま下にコピペし、「予想表示を更新する」を押してください。")
    input_text = st.text_area("KUINA AI出力テキスト全貼り付け", value=st.session_state.ai_text, height=250)
    if st.button("🚀 サイトの予想表示を即時更新する", type="primary"):
        if input_text.strip():
            st.session_state.ai_text = input_text
            st.success("サイト上の予想解析データを更新しました！")
            st.rerun()
        else:
            st.warning("テキストを入力してください。")

st.divider()

# 9. 免責事項＆特定商取引法に基づく表記
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
    - **お支払い方法**: クレジットカード決済（Stripe）  
    - **役務の提供時期**: Stripeでの決済完了後、即時（限定LINEオープンチャットへの案内）  
    - **解約・返金について**: クレジットカード決済のマイページよりいつでも次回更新の停止（解約）が可能です。サービスの性質上、決済完了後の返金・日割り計算には応じかねます。
    """)
