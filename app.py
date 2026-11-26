import streamlit as st

# ページ全体の基本設定
st.set_page_config(
    page_title="KUINA AI 競馬オンラインサロン",
    page_icon="🤖",
    layout="centered"
)

# デザインのカスタマイズ（CSS）
st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: bold; color: #1a365d; text-align: center; margin-bottom: 5px; }
    .sub-header { font-size: 0.95rem; color: #4a5568; text-align: center; margin-bottom: 25px; }
    .stripe-btn {
        display: block; width: 100%; padding: 14px; background-color: #38a169; color: white !important;
        text-align: center; font-weight: bold; font-size: 1.1rem; text-decoration: none; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(56,161,105,0.3); margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# 1. サロンヘッダー
st.markdown('<div class="main-header">🤖 KUINA AI 競馬オンラインサロン</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">PC管理AIによる高精度データ解析 × 勝ち残るための初心者攻略コラム</div>', unsafe_allow_html=True)

st.divider()

# 2. 会員特典・サービス特徴
st.subheader("💡 サロンで提供する3つの価値")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("##### 📊 PC管理AI予想")
    st.caption("6つの主要ファクター（枠・馬場・距離・脚質・騎手・近走）を完全数値化したAIスコアを配信。")
with col2:
    st.markdown("##### 📱 限定LINEオプチャ")
    st.caption("リアルタイムの直前気配・最終予想をスマホのプッシュ通知で直接受信。")
with col3:
    st.markdown("##### 🎓 初心者向け上達コラム")
    st.caption("資金配分術、コース有利不利、穴馬抽出法を伝授。")

st.divider()

# 3. 料金＆Stripe決済ボタン
st.subheader("💳 入会案内")
st.write("**月額会員プラン：3,000円 / 月（税込）**")
st.caption("※Stripe決済完了後、表示される案内からLINEオープンチャットへ即時参加できます。")

# Stripe Payment Link URLを下記に入力してください
stripe_url = "YOUR_STRIPE_PAYMENT_LINK_HERE"
st.markdown(f'<a href="{stripe_url}" target="_blank" class="stripe-btn">今すぐサロンに入会する（Stripe決済）</a>', unsafe_allow_html=True)

st.divider()

# セッション状態の初期化（AIテキスト保持用）
if 'ai_text' not in st.session_state:
    st.session_state.ai_text = ""

# 4. 最新AI解析データ表示エリア
st.subheader("💎【最新】KUINA AI 厳選レース解析")
if st.session_state.ai_text:
    st.markdown(st.session_state.ai_text)
else:
    st.info("※最新の予想データは準備中です。週末に更新されます。")

st.divider()

# 5. 初心者向けコラムコーナー
st.subheader("📚 初心者向け必勝コラム（一部公開）")
st.markdown("#### 【第1回】トリガミを防ぐ「効率的な資金配分」の黄金比")
st.write("競馬で勝つコツは「当てること」以上に「不的中時の資金を減らし、本線でしっかり回収すること」です。合成オッズ2.0倍以上をキープするための資金配分術を徹底解説します。")
st.caption("※会員限定LINEオープンチャットの「ノート」にて全編・次回コラムを公開中！")

st.divider()

# 6. 運営者専用：KUINA AI テキスト貼り付け＆更新フォーム（畳んで配置）
with st.expander("⚙️ 運営者専用：KUINA AI テキスト貼り付けエリア"):
    input_text = st.text_area("KUINA AIの出力テキストを全コピペしてください", height=200)
    if st.button("サイトの予想表示を更新する"):
        if input_text:
            st.session_state.ai_text = input_text
            st.success("予想データを更新しました！")
            st.rerun()

st.divider()

# 7. 免責事項・特定商取引法表記
with st.expander("⚖️ 免責事項・特定商取引法に基づく表記"):
    st.markdown("""
    **【免責事項】**  
    当サロンで提供するAI予想データ、コラム、配信コンテンツは情報提供を目的としており、馬券の的中や利益を保証するものではありません。馬券の購入はご自身の責任と判断で行ってください。  
    
    **【特定商取引法に基づく表記】**  
    - 事業者名：[ご自身の氏名または屋号]  
    - 連絡先：[メールアドレス]  
    - 支払方法：クレジットカード（Stripe）  
    - 返金・中途解約：サービスの性質上、決済完了後の返金は応じかねます。次回更新の停止は決済マイページよりいつでも可能です。
    """)
