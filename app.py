import datetime
import json
import os
import streamlit as st
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# ページ基本設定（横置きタブレット向け全画面・ワイド構成）
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Intelligence Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# タブレット横画面最適化 CSS (1280x800 想定 / ダークテーマ / タッチフレンドリー)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* 全体コンテナの余白調整（縦スクロールを抑え、画面を広く活用） */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.8rem !important;
        padding-right: 1.8rem !important;
        max-width: 100% !important;
    }
    
    /* ヘッダー周りのすっきり化 */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    
    /* タブ切り替えボタンの大型化（指先タップしやすいサイズ） */
    div[data-baseweb="tab-list"] {
        gap: 12px;
        margin-bottom: 1rem;
    }
    button[data-baseweb="tab"] {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        border-radius: 10px 10px 0 0 !important;
        background-color: #1E293B !important;
        color: #94A3B8 !important;
        border: 1px solid #334155 !important;
        border-bottom: none !important;
        transition: all 0.2s ease-in-out;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #312E81 !important;
        color: #EEF2FF !important;
        border-color: #6366F1 !important;
    }
    
    /* ボタンのタップ領域・視認性強化 */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 1.0rem !important;
        padding: 0.65rem 1.4rem !important;
        transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    div.stButton > button:active {
        transform: scale(0.98);
    }
    
    /* カードコンポーネント */
    .dashboard-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -2px rgba(0, 0, 0, 0.2);
    }
    .dashboard-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        border-bottom: 1px solid #334155;
        padding-bottom: 8px;
    }
    .dashboard-card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #F8FAFC;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* バッジ */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.025em;
    }
    .badge-positive {
        background-color: #064E3B;
        color: #34D399;
        border: 1px solid #059669;
    }
    .badge-caution {
        background-color: #78350F;
        color: #FBBF24;
        border: 1px solid #D97706;
    }
    .badge-neutral {
        background-color: #1E293B;
        color: #93C5FD;
        border: 1px solid #3B82F6;
    }
    
    /* ヘッダー時刻・ステータス表示バー */
    .top-status-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #0F172A;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 8px 18px;
        margin-bottom: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 利用モデルの定義
# -----------------------------------------------------------------------------
MODEL_NAME = "gemini-2.5-flash"

# -----------------------------------------------------------------------------
# パスワード認証（SecretsにAPP_PASSWORDが設定されている場合にアクセス制限）
# -----------------------------------------------------------------------------
def get_app_password() -> str:
    """Secretsまたは環境変数からアプリ保護用パスワードを取得"""
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD", "")

def check_password() -> bool:
    """パスワードが正しければTrue、未認証ならログインUIを表示して停止"""
    required_pwd = get_app_password()
    # パスワードが未設定の場合は誰でもアクセス可能（ローカル開発等）
    if not required_pwd:
        return True

    if st.session_state.get("authenticated", False):
        return True

    # ログイン画面（未認証時はサイドバーも表示させずにここでブロック）
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    auth_col1, auth_col2, auth_col3 = st.columns([1, 1.4, 1])
    with auth_col2:
        st.markdown(
            """
            <div class="dashboard-card" style="text-align: center; padding: 32px 24px; border: 1px solid #4F46E5;">
                <div style="font-size: 2.5rem; margin-bottom: 8px;">🔐</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;">AI Dashboard</div>
                <div style="font-size: 0.9rem; color: #94A3B8; margin-bottom: 20px;">このダッシュボードは保護されています。<br>アクセスパスワードを入力してください。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form(key="login_form"):
            entered_pwd = st.text_input("パスワード", type="password", placeholder="パスワードを入力", label_visibility="collapsed")
            submit = st.form_submit_button("🔓 ロック解除", use_container_width=True)
            if submit:
                if entered_pwd == required_pwd:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("パスワードが正しくありません")

    return False

# 認証チェック（未認証の場合はここで処理をストップ）
if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# APIキー取得 & クライアント初期化
# -----------------------------------------------------------------------------
def get_api_key() -> str:
    """Streamlit Secrets、環境変数、UI入力の順でAPIキーを取得"""
    # 1. st.secrets（secrets.tomlが存在しない場合でも例外で落ちないよう保護）
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # 2. 環境変数
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    # 3. session_state (UI手動入力)
    return st.session_state.get("user_gemini_api_key", "")

def get_genai_client(api_key: str):
    """最新google-genaiクライアントを作成"""
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

# サイドバー（APIキー設定や補助メニュー）
with st.sidebar:
    st.markdown("### ⚙️ 設定 & ステータス")
    current_key = get_api_key()
    if not current_key:
        st.warning("⚠️ APIキーが未検出です。")
        input_key = st.text_input(
            "Gemini API Key を入力してください",
            type="password",
            help="Google AI Studioで取得したAPIキーを入力してください",
            key="api_key_input",
        )
        if input_key:
            st.session_state["user_gemini_api_key"] = input_key
            st.success("APIキーを設定しました！")
            st.rerun()
    else:
        st.success("✅ Gemini API 接続準備完了")
        if st.button("APIキーをクリア / 再設定"):
            st.session_state.pop("user_gemini_api_key", None)
            st.rerun()

    if get_app_password():
        if st.button("🔒 ログアウト（再ロック）"):
            st.session_state["authenticated"] = False
            st.rerun()

    st.markdown("---")
    st.markdown(
        f"""
        **Fire HD 常駐ダッシュボード**  
        - 利用モデル: `{MODEL_NAME}`  
        - 画面解像度: 1280 × 800 最適化  
        - フレームワーク: Streamlit + google-genai
        """
    )

# -----------------------------------------------------------------------------
# セッション状態の初期化
# -----------------------------------------------------------------------------
if "briefing_data" not in st.session_state:
    st.session_state["briefing_data"] = None
if "briefing_last_updated" not in st.session_state:
    st.session_state["briefing_last_updated"] = None

if "brainstorm_result" not in st.session_state:
    st.session_state["brainstorm_result"] = None
if "brainstorm_input" not in st.session_state:
    st.session_state["brainstorm_input"] = ""

if "tasks" not in st.session_state:
    st.session_state["tasks"] = [
        {"id": 1, "text": "主要プロジェクトの仕様策定", "done": False},
        {"id": 2, "text": "チーム定例ミーティングの準備", "done": False},
        {"id": 3, "text": "日報・タスク棚卸しの実施", "done": True},
    ]
if "task_advice" not in st.session_state:
    st.session_state["task_advice"] = None

# -----------------------------------------------------------------------------
# トップステータスバー（現在日時・常駐感の演出）
# -----------------------------------------------------------------------------
now = datetime.datetime.now()
date_str = now.strftime("%Y年%m月%d日")
weekday_str = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]
time_str = now.strftime("%H:%M")

status_col1, status_col2 = st.columns([3, 1])
with status_col1:
    st.markdown(
        f"""
        <div style="font-size: 1.45rem; font-weight: 700; color: #F8FAFC; letter-spacing: -0.02em;">
            ⚡ AI Intelligence Dashboard
        </div>
        """,
        unsafe_allow_html=True,
    )
with status_col2:
    st.markdown(
        f"""
        <div style="text-align: right; color: #94A3B8; font-size: 0.95rem; font-weight: 500;">
            📅 {date_str} ({weekday_str}) <span style="color: #6366F1; font-weight: 700; margin-left: 8px;">{time_str}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

api_key = get_api_key()
client = get_genai_client(api_key)

# APIキー未設定時の警告バナー（メイン画面）
if not api_key:
    st.info(
        "💡 **Gemini APIキーを設定してください**  \n"
        "左側のサイドバー（または Streamlit Secrets / 環境変数 `GEMINI_API_KEY`）にAPIキーを設定すると、"
        "全機能が利用可能になります。"
    )

# -----------------------------------------------------------------------------
# メインタブ構成
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📊 情報ブリーフィング",
    "💡 思考整理・ブレスト",
    "📝 タスク・アドバイザー",
])

# =============================================================================
# タブ1：情報ブリーフィング（Intelligence Briefing）
# =============================================================================
with tab1:
    col_t1_btn, col_t1_status = st.columns([1.5, 3.5])
    with col_t1_btn:
        update_briefing = st.button("🔄 最新情報を要約更新", key="btn_update_briefing", use_container_width=True)
    with col_t1_status:
        if st.session_state["briefing_last_updated"]:
            st.caption(f"最終更新: {st.session_state['briefing_last_updated']}")
        else:
            st.caption("ボタンを押すと、最新の市況動向・テックトレンド・ビジネストピックを生成・要約します。")

    if update_briefing:
        if not client:
            st.error("APIキーが設定されていません。サイドバーから設定してください。")
        else:
            with st.spinner("AIが最新市場・テック動向を分析・要約中..."):
                prompt = """
                あなたはプロのビジネス・インテリジェンス・アナリストです。
                現代のビジネスパーソン向けに、本日押さえておくべき最新動向を分析し、以下の3カテゴリについて要約してください。

                【出力形式】
                以下のキーを持つJSONオブジェクトのみを出力してください（Markdownコードブロック ```json も不要です。純粋なJSONテキストのみ）。
                {
                    "market": {
                        "category_name": "国内・グローバル市況",
                        "sentiment": "ポジティブ" または "中立" または "警戒",
                        "summary_points": [
                            "要点1（1行で簡潔に）",
                            "要点2（1行で簡潔に）",
                            "要点3（1行で簡潔に）"
                        ],
                        "focus_point": "注目すべきポイント・インサイト（2〜3文）"
                    },
                    "tech": {
                        "category_name": "AI & テックトレンド",
                        "sentiment": "ポジティブ" または "中立" または "警戒",
                        "summary_points": [
                            "要点1（1行で簡潔に）",
                            "要点2（1行で簡潔に）",
                            "要点3（1行で簡潔に）"
                        ],
                        "focus_point": "注目すべきポイント・インサイト（2〜3文）"
                    },
                    "business": {
                        "category_name": "ビジネストピック & 産業動向",
                        "sentiment": "ポジティブ" または "中立" または "警戒",
                        "summary_points": [
                            "要点1（1行で簡潔に）",
                            "要点2（1行で簡潔に）",
                            "要点3（1行で簡潔に）"
                        ],
                        "focus_point": "注目すべきポイント・インサイト（2〜3文）"
                    }
                }
                """
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.7,
                        ),
                    )
                    parsed_json = json.loads(response.text)
                    st.session_state["briefing_data"] = parsed_json
                    st.session_state["briefing_last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    st.error(f"情報取得中にエラーが発生しました: {str(e)}")

    # 表示部（3カラム並列カード形式）
    data = st.session_state.get("briefing_data")
    if data:
        cols = st.columns(3)
        categories = [
            ("market", "📈", "国内・グローバル市況", cols[0]),
            ("tech", "🤖", "AI & テックトレンド", cols[1]),
            ("business", "💼", "ビジネストピック", cols[2]),
        ]

        def get_badge_html(sentiment: str) -> str:
            if "ポジティブ" in sentiment:
                return f'<span class="badge badge-positive">● {sentiment}</span>'
            elif "警戒" in sentiment:
                return f'<span class="badge badge-caution">▲ {sentiment}</span>'
            else:
                return f'<span class="badge badge-neutral">■ {sentiment}</span>'

        for key, icon, title, col in categories:
            cat_data = data.get(key, {})
            sentiment = cat_data.get("sentiment", "中立")
            points = cat_data.get("summary_points", [])
            focus = cat_data.get("focus_point", "")

            with col:
                points_html = "".join([f"<li style='margin-bottom: 6px; color: #CBD5E1;'>{p}</li>" for p in points])
                card_html = f"""
                <div class="dashboard-card">
                    <div class="dashboard-card-header">
                        <span class="dashboard-card-title">{icon} {title}</span>
                        {get_badge_html(sentiment)}
                    </div>
                    <div style="font-size: 0.9rem; font-weight: 600; color: #94A3B8; margin-bottom: 8px;">【3行要点要約】</div>
                    <ul style="padding-left: 18px; margin-bottom: 14px; font-size: 0.92rem; line-height: 1.5;">
                        {points_html}
                    </ul>
                    <div style="background-color: #0F172A; border-left: 3px solid #6366F1; padding: 10px 12px; border-radius: 6px;">
                        <div style="font-size: 0.82rem; font-weight: 700; color: #818CF8; margin-bottom: 4px;">🔍 注目インサイト</div>
                        <div style="font-size: 0.88rem; color: #E2E8F0; line-height: 1.45;">{focus}</div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div style="background-color: #1E293B; border: 2px dashed #334155; border-radius: 14px; padding: 40px; text-align: center; color: #94A3B8; margin-top: 10px;">
                <div style="font-size: 2rem; margin-bottom: 10px;">📊</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #F1F5F9;">情報ブリーフィングがまだ取得されていません</div>
                <div style="font-size: 0.9rem; margin-top: 6px;">上の「最新情報を要約更新」ボタンを押すと、AIが最新の市況やテック動向をまとめます。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# =============================================================================
# タブ2：思考整理・ブレスト（Brainstorm & Wall-hit）
# =============================================================================
with tab2:
    st.markdown(
        """
        <div style="font-size: 0.95rem; color: #94A3B8; margin-bottom: 10px;">
            新規事業案、技術的課題、日々のモヤモヤなどを入力して「壁打ち」を行いましょう。
            Geminiが<strong>「共感・アイデア拡張」「批判的検証（悪魔の代弁者）」「ネクストアクション」</strong>の3視点からフィードバックします。
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_input = st.text_area(
        "ブレストテーマ・相談内容を入力",
        value=st.session_state["brainstorm_input"],
        placeholder="例: 社内向けに生成AIチャットボットを導入したいが、定着率を高めて業務効率化を実感してもらうにはどんな施策が有効だろうか？",
        height=100,
        key="txt_brainstorm",
    )

    col_b_btn, col_b_clear = st.columns([1.5, 3.5])
    with col_b_btn:
        start_brainstorm = st.button("🚀 ブレスト開始", key="btn_brainstorm", use_container_width=True)
    with col_b_clear:
        if st.session_state["brainstorm_result"]:
            if st.button("結果をクリア", key="btn_clear_brainstorm"):
                st.session_state["brainstorm_result"] = None
                st.session_state["brainstorm_input"] = ""
                st.rerun()

    if start_brainstorm:
        if not user_input.strip():
            st.warning("ブレストのテーマや内容を入力してください。")
        elif not client:
            st.error("APIキーが設定されていません。サイドバーから設定してください。")
        else:
            st.session_state["brainstorm_input"] = user_input
            with st.spinner("多角的な視点からアイデアを深掘り・検証中..."):
                prompt = f"""
                あなたは最高峰のアイデア壁打ちパートナーであり、鋭い戦略コンサルタントです。
                以下のユーザーからの相談内容に対して、3つの異なる視点から思考整理・フィードバックを行ってください。

                【ユーザーの相談内容】
                {user_input}

                【出力形式】
                以下のキーを持つJSONオブジェクトのみを出力してください（Markdownコードブロック不要、純粋なJSONテキスト）。
                {{
                    "expansion": {{
                        "title": "共感・アイデア拡張",
                        "summary": "アイデアの魅力やポテンシャルを肯定しつつ、スケールアップさせる具体例や応用案（2〜3文）",
                        "points": [
                            "拡張アイデア1",
                            "拡張アイデア2",
                            "拡張アイデア3"
                        ]
                    }},
                    "criticism": {{
                        "title": "批判的検証（悪魔の代弁者）",
                        "summary": "見落としがちな盲点、潜在的リスク、想定される反対意見（2〜3文）",
                        "points": [
                            "注意すべきリスク1",
                            "見落としがちな点2",
                            "クリアすべきハードル3"
                        ]
                    }},
                    "actions": {{
                        "title": "ネクストアクション",
                        "summary": "今すぐまたは48時間以内に着手すべき具体的な第一歩",
                        "points": [
                            "アクション1（具体的に）",
                            "アクション2（具体的に）",
                            "アクション3（具体的に）"
                        ]
                    }}
                }}
                """
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.8,
                        ),
                    )
                    st.session_state["brainstorm_result"] = json.loads(response.text)
                except Exception as e:
                    st.error(f"ブレスト生成中にエラーが発生しました: {str(e)}")

    # 結果表示（横並び3カード）
    b_data = st.session_state.get("brainstorm_result")
    if b_data:
        b_cols = st.columns(3)

        # 1. 拡張
        with b_cols[0]:
            exp = b_data.get("expansion", {})
            pts = "".join([f"<li style='margin-bottom: 6px; color: #CBD5E1;'>{p}</li>" for p in exp.get("points", [])])
            st.markdown(
                f"""
                <div class="dashboard-card" style="border-top: 4px solid #10B981;">
                    <div class="dashboard-card-header">
                        <span class="dashboard-card-title">🌱 共感 & アイデア拡張</span>
                    </div>
                    <div style="font-size: 0.92rem; color: #E2E8F0; line-height: 1.5; margin-bottom: 12px;">
                        {exp.get("summary", "")}
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #34D399; margin-bottom: 6px;">💡 具体的な展開案</div>
                    <ul style="padding-left: 18px; font-size: 0.88rem; line-height: 1.5;">
                        {pts}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 2. 批判的検証
        with b_cols[1]:
            crit = b_data.get("criticism", {})
            pts = "".join([f"<li style='margin-bottom: 6px; color: #CBD5E1;'>{p}</li>" for p in crit.get("points", [])])
            st.markdown(
                f"""
                <div class="dashboard-card" style="border-top: 4px solid #F59E0B;">
                    <div class="dashboard-card-header">
                        <span class="dashboard-card-title">🛡️ 批判的検証（悪魔の代弁者）</span>
                    </div>
                    <div style="font-size: 0.92rem; color: #E2E8F0; line-height: 1.5; margin-bottom: 12px;">
                        {crit.get("summary", "")}
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #FBBF24; margin-bottom: 6px;">⚠️ 盲点 & リスクチェック</div>
                    <ul style="padding-left: 18px; font-size: 0.88rem; line-height: 1.5;">
                        {pts}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 3. アクション
        with b_cols[2]:
            act = b_data.get("actions", {})
            pts = "".join([f"<li style='margin-bottom: 6px; color: #CBD5E1;'>{p}</li>" for p in act.get("points", [])])
            st.markdown(
                f"""
                <div class="dashboard-card" style="border-top: 4px solid #6366F1;">
                    <div class="dashboard-card-header">
                        <span class="dashboard-card-title">🎯 ネクストアクション</span>
                    </div>
                    <div style="font-size: 0.92rem; color: #E2E8F0; line-height: 1.5; margin-bottom: 12px;">
                        {act.get("summary", "")}
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #818CF8; margin-bottom: 6px;">🏃 次の3ステップ</div>
                    <ul style="padding-left: 18px; font-size: 0.88rem; line-height: 1.5;">
                        {pts}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

# =============================================================================
# タブ3：タスク・アドバイザー（Daily Task Advisor）
# =============================================================================
with tab3:
    task_col_left, task_col_right = st.columns([1.1, 1.1], gap="large")

    # 左側：ToDoリスト管理
    with task_col_left:
        st.markdown(
            """
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 8px;">
                📋 今日のタスク一覧
            </div>
            """,
            unsafe_allow_html=True,
        )

        # タスク追加フォーム
        with st.form(key="add_task_form", clear_on_submit=True):
            add_col1, add_col2 = st.columns([3.5, 1.2])
            with add_col1:
                new_task_text = st.text_input("タスク名", placeholder="新しいタスクを入力...", label_visibility="collapsed")
            with add_col2:
                submitted = st.form_submit_button("＋ 追加", use_container_width=True)
            if submitted and new_task_text.strip():
                new_id = max([t["id"] for t in st.session_state["tasks"]], default=0) + 1
                st.session_state["tasks"].append({"id": new_id, "text": new_task_text.strip(), "done": False})
                st.rerun()

        # タスク一覧表示
        tasks = st.session_state["tasks"]
        if not tasks:
            st.info("登録されているタスクはありません。上のフォームから追加してください。")
        else:
            for task in tasks:
                t_col1, t_col2 = st.columns([4, 1])
                with t_col1:
                    is_done = st.checkbox(
                        task["text"],
                        value=task["done"],
                        key=f"task_check_{task['id']}",
                    )
                    if is_done != task["done"]:
                        task["done"] = is_done
                        st.rerun()
                with t_col2:
                    if st.button("削除", key=f"del_task_{task['id']}", help="このタスクを削除"):
                        st.session_state["tasks"] = [t for t in tasks if t["id"] != task["id"]]
                        st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        t_btn_col1, t_btn_col2 = st.columns([2, 1])
        with t_btn_col1:
            get_advice = st.button("✨ AIアドバイスを生成", key="btn_get_task_advice", use_container_width=True)
        with t_btn_col2:
            if st.button("完了を一括消去", key="btn_clear_done", use_container_width=True):
                st.session_state["tasks"] = [t for t in tasks if not t["done"]]
                st.rerun()

    # 右側：AIアドバイスパネル
    with task_col_right:
        st.markdown(
            """
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 8px;">
                🧭 AI タスク・アドバイザー
            </div>
            """,
            unsafe_allow_html=True,
        )

        if get_advice:
            active_tasks = [t["text"] for t in st.session_state["tasks"] if not t["done"]]
            done_tasks = [t["text"] for t in st.session_state["tasks"] if t["done"]]

            if not active_tasks and not done_tasks:
                st.warning("分析するタスクがありません。先にタスクを登録してください。")
            elif not client:
                st.error("APIキーが設定されていません。サイドバーから設定してください。")
            else:
                with st.spinner("タスクの優先度と段取りを分析中..."):
                    task_summary_text = f"【未完了タスク】: {', '.join(active_tasks) if active_tasks else 'なし'}\n"
                    task_summary_text += f"【完了済みタスク】: {', '.join(done_tasks) if done_tasks else 'なし'}"

                    prompt = f"""
                    あなたは卓越した生産性コーチです。
                    以下のユーザーのタスクリストを分析し、最も効果的に一日を過ごすためのアドバイスを提供してください。

                    {task_summary_text}

                    【出力形式】
                    以下のキーを持つJSONオブジェクトのみを出力してください（Markdownコードブロック不要、純粋なJSONテキスト）。
                    {{
                        "priority_task": "最も優先して取り組むべきタスクとその理由（2〜3文）",
                        "strategy": "時間配分や集中すべき時間帯、段取りの具体的なコツ（2〜3文）",
                        "motivation": "ユーザーが一日の活力を得られる、温かく前向きな一言エール（1〜2文）"
                    }}
                    """
                    try:
                        response = client.models.generate_content(
                            model=MODEL_NAME,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.7,
                            ),
                        )
                        st.session_state["task_advice"] = json.loads(response.text)
                    except Exception as e:
                        st.error(f"アドバイス生成中にエラーが発生しました: {str(e)}")

        advice = st.session_state.get("task_advice")
        if advice:
            st.markdown(
                f"""<div class="dashboard-card" style="border-left: 4px solid #6366F1;">
<div style="font-size: 0.95rem; font-weight: 700; color: #818CF8; margin-bottom: 6px;">🔥 最優先で終わらせるべきタスク</div>
<div style="font-size: 0.92rem; color: #F8FAFC; line-height: 1.5; margin-bottom: 14px;">{advice.get("priority_task", "")}</div>
<div style="font-size: 0.95rem; font-weight: 700; color: #34D399; margin-bottom: 6px;">⏱️ 進め方 & 段取りのコツ</div>
<div style="font-size: 0.92rem; color: #F8FAFC; line-height: 1.5; margin-bottom: 14px;">{advice.get("strategy", "")}</div>
<div style="font-size: 0.95rem; font-weight: 700; color: #F472B6; margin-bottom: 6px;">💬 モチベーションメッセージ</div>
<div style="font-size: 0.92rem; color: #FDE047; font-style: italic; line-height: 1.5;">"{advice.get("motivation", "")}"</div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background-color: #1E293B; border: 2px dashed #334155; border-radius: 14px; padding: 35px; text-align: center; color: #94A3B8;">
                    <div style="font-size: 1.8rem; margin-bottom: 8px;">💡</div>
                    <div style="font-size: 1.05rem; font-weight: 600; color: #F1F5F9;">AIアドバイスはまだ生成されていません</div>
                    <div style="font-size: 0.88rem; margin-top: 6px;">左の「AIアドバイスを生成」ボタンを押すと、優先度や段取りの提案がここに表示されます。</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
