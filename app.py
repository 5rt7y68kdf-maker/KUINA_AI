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
    .line-button {
        display: block;
        width: 100%;
        padding: 14px;
        background-color: #06C755;
        color: white !important;
        text-align: center;
        font-weight: bold;
        font-size: 1.05rem;
        text-decoration: none;
        border-radius: 8px;
        margin: 10px 0;
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
st.subheader("💡 サロンのサービス内容")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>🔒 有料会員限定AI解析</h4>
        <p style="font-size:0.85rem; color:#4A5568;">重賞・厳選レースの6大ファクター数値化スコア＆推奨買い目をWeb会員エリアで公開！</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>📱 無料LINEオプチャ</h4>
        <p style="font-size:0.85rem; color:#4A5568;">開設済みの無料オープンチャットにて、週末2〜4レースの予想＆サロン更新情報を無料配信！</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h4>📚 有料会員限定コラム</h4>
        <p style="font-size:0.85rem; color:#4A5568;">初心者向けの必勝コラム（資金配分術・コース攻略・穴馬抽出法）を会員エリアにて全編配信。</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# 5. 無料オープンチャット案内（開設済みオプチャURLを設定）
st.subheader("🟢 無料LINEオープンチャット（開設済み）")
st.write("どなたでも無料で参加できます！週末の**無料2〜4レース予想**やサロンの最新情報を配信中。")
FREE_LINE_OC_LINK = "YOUR_FREE_LINE_OPENCHAT_URL_HERE"  # ご自身の無料オープンチャットURLがあればここに貼り付けてください
st.markdown(f'<a href="{FREE_LINE_OC_LINK}" target="_blank" class="line-button">💬 無料LINEオープンチャットに参加する</a>', unsafe_allow_html=True)

st.divider()

# 6. 有料会員入会案内＆Stripe決済
st.subheader("💳 有料会員サロン（当サイト内で閲覧完結）")
st.markdown("### **月額会員プラン：1,980円 / 月（税込）**")
st.caption("※Stripe決済完了後の画面に「会員専用パスワード」が表示されます。下部の専用ログインエリアに入力することで、KUINA AI重賞フル解析および限定コラムを全編閲覧いただけます。")

# 設定いただいたStripe決済リンク
STRIPE_PAYMENT_LINK = "https://buy.stripe.com/00w3cvelM35sahn9Er0sU00"
st.markdown(f'<a href="{STRIPE_PAYMENT_LINK}" target="_blank" class="stripe-button">今すぐ有料会員になる（Stripe月額1,980円決済）</a>', unsafe_allow_html=True)

with st.expander("❓ クレジットカードをお持ちでない方のお支払い方法について"):
    st.markdown("""
    当サロンの決済（Stripe）では、クレジットカードのほか以下がご利用いただけます。
    * **Apple Pay / Google Pay**：スマホに登録された決済手段でワンタップ支払い。
    * **デビットカード**：各銀行のデビットカード（Visa/JCB等）がそのまま利用可能。
    * **プリペイドカード**：「バンドルカード」や「Kyash」などの即時発行プリペイドカードも対応。
    """)

st.divider()

# 7. 無料公開：コラムの目次・紹介（有料化の導線）
st.subheader("📖 会員限定 競身上達コラム（目次案内）")
st.write("有料会員エリアでは、競馬初心者から勝ち組へステップアップするための**完全版コラム**を順次配信・公開しています。")

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("##### 📌 第1回")
    st.caption("トリガミを防ぐ「効率的な資金配分」の黄金比（合成オッズ計算・傾斜配分）")
with col_b:
    st.markdown("##### 📌 第2回")
    st.caption("全国競馬場・コース別の枠順＆バイアス攻略ガイド（馬場傾向の読み解き）")
with col_c:
    st.markdown("##### 📌 第3回")
    st.caption("データから導く「激走穴馬」の抽出テクニック（距離短縮・鞍上替わり等）")

st.info("💡 全編の本文は、以下の「有料会員専用エリア」にてご覧いただけます。")

st.divider()

# 8. 有料会員専用エリア（パスワード認証・サイト完結）
st.subheader("🔒【有料会員専用エリア】AI解析データ ＆ 限定コラム")

# 初期状態の設定（デフォルトパスワードおよび予想テキスト）
if 'member_pass' not in st.session_state:
    st.session_state.member_pass = "kuina2026"  # デフォルトの会員パスワード
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

# パスワード入力フォーム
user_input_pass = st.text_input("🔑 Stripe決済後に表示された「会員用パスワード」を入力してください", type="password")

if user_input_pass == st.session_state.member_pass:
    st.success("🔓 会員認証成功！限定解析データおよび会員限定コラムを表示しています。")
    
    # 8-1. 有料限定 AI予想
    st.markdown("### 🤖 KUINA AI 重賞フル解析")
    st.markdown(st.session_state.ai_text)
    
    st.divider()
    
    # 8-2. 有料限定 コラム全編
    st.markdown("### 📚 会員限定 競馬上達コラム（全編）")
    
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

else:
    st.info("🔒 会員用パスワードを入力すると、ここに「KUINA AI 重賞フル解析データ」および「限定コラム（全編）」が表示されます。")

st.divider()

# 9. 運営者専用エリア（パスワード＆予想テキストの管理）
with st.expander("⚙️ 運営者専用：KUINA AI テキスト更新・パスワード設定"):
    st.write("PCで生成されたKUINA AIの解析テキストの更新や、会員用パスワードの設定ができます。")
    new_pass = st.text_input("会員用パスワードの設定", value=st.session_state.member_pass)
    input_text = st.text_area("KUINA AI出力テキスト全貼り付け", value=st.session_state.ai_text, height=200)
    
    if st.button("🚀 サイトの情報を更新する", type="primary"):
        st.session_state.member_pass = new_pass
        st.session_state.ai_text = input_text
        st.success("予想データおよび会員パスワードを更新しました！")
        st.rerun()

st.divider()

# 10. 免責事項・特商法表記
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
    - **役務の提供時期**: Stripeでの決済完了後、即時（会員パスワードの発行による限定ページの閲覧権限）  
    - **解約・返金について**: クレジットカード決済のマイページよりいつでも次回更新の停止（解約）が可能です。サービスの性質上、決済完了後の返金・日割り計算には応じかねます。
    """)
