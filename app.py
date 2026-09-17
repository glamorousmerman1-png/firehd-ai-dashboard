import calendar
import datetime
import json
import os
import re
import time
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

def get_custom_instructions() -> str:
    """custom_instructions.txt からユーザー定義の指示（回答トーン・スタイル）を読み込む"""
    instruction_path = os.path.join(os.path.dirname(__file__), "custom_instructions.txt")
    if os.path.exists(instruction_path):
        try:
            with open(instruction_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""

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
    
    # カスタム指示のステータス表示
    custom_inst = get_custom_instructions()
    if custom_inst:
        st.markdown("**🎨 カスタム指示: 有効**")
        with st.expander("指示内容を確認"):
            st.text(custom_inst)
    else:
        st.caption("カスタム指示: 未設定（標準モード）")

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

TASKS_DATA_FILE = os.path.join(os.path.dirname(__file__), "tasks_data.json")

def load_shared_tasks_data():
    """全端末（仕事PC・プライベート端末・タブレット）で共通同期するタスクとAIアドバイスを読み込む"""
    default_tasks = [
        {"id": 1, "text": "主要プロジェクトの仕様策定", "done": False},
        {"id": 2, "text": "チーム定例ミーティングの準備", "done": False},
        {"id": 3, "text": "日報・タスク棚卸しの実施", "done": True},
    ]
    if os.path.exists(TASKS_DATA_FILE):
        try:
            with open(TASKS_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data, None, ""
                elif isinstance(data, dict):
                    return data.get("tasks", default_tasks), data.get("task_advice", None), data.get("updated_at", "")
        except Exception:
            pass
    return default_tasks, None, ""

def save_shared_tasks_data(tasks, advice=None):
    """全端末共通のタスクとAIアドバイスをJSONファイルに永続化保存"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    data = {
        "tasks": tasks,
        "task_advice": advice,
        "updated_at": now_str
    }
    try:
        with open(TASKS_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"タスクデータの保存に失敗しました: {e}")

shared_tasks, shared_advice, _ = load_shared_tasks_data()
if "tasks" not in st.session_state:
    st.session_state["tasks"] = shared_tasks
if "task_advice" not in st.session_state:
    st.session_state["task_advice"] = shared_advice

# -----------------------------------------------------------------------------
# 習慣・健康・個別タスク（taskkanri統合）ストレージ & ヘルパー
# -----------------------------------------------------------------------------
TASKKANRI_FILE = os.path.join(os.path.dirname(__file__), "taskkanri_data.json")

HABITS_LIST = [
    "血圧測定",
    "プランク",
    "スクワット",
    "降圧ストレッチ",
    "パター練習",
    "Google AI Studioの日記記入",
    "Google AI Studioの家計簿記入",
    "エクセルでの株価チェック",
]

HABIT_CATEGORIES = {
    "運動・健康": ["血圧測定", "プランク", "スクワット", "降圧ストレッチ", "パター練習"],
    "記録・管理": ["Google AI Studioの日記記入", "Google AI Studioの家計簿記入", "エクセルでの株価チェック"],
}

def load_taskkanri_data():
    """習慣トラッカーおよび個別タスクの全端末共通データを読み込む"""
    default_data = {
        "trackerData": {},
        "adhocTasks": [],
        "updated_at": ""
    }
    if os.path.exists(TASKKANRI_FILE):
        try:
            with open(TASKKANRI_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "trackerData" not in data:
                        data["trackerData"] = {}
                    if "adhocTasks" not in data:
                        data["adhocTasks"] = []
                    return data
        except Exception:
            pass
    return default_data

def save_taskkanri_data(data):
    """習慣トラッカーおよび個別タスクの全端末共通データを保存"""
    data["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(TASKKANRI_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"習慣・タスクデータの保存に失敗しました: {e}")

def calculate_habit_streak(tracker_data, habit_name):
    """特定習慣の現在連続達成日数（ストリーク）を計算"""
    streak = 0
    today = datetime.date.today()
    for i in range(365):
        d_str = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        day_info = tracker_data.get(d_str, {})
        is_done = day_info.get(habit_name, False) if isinstance(day_info, dict) else bool(day_info)
        if i == 0 and not is_done:
            continue
        if is_done:
            streak += 1
        else:
            break
    return streak

def calculate_habit_stats(tracker_data, habit_name):
    """今月の達成日数と通算達成日数を計算"""
    today = datetime.date.today()
    this_month_prefix = today.strftime("%Y-%m")
    total_days = 0
    month_days = 0
    for d_str, day_info in tracker_data.items():
        is_done = day_info.get(habit_name, False) if isinstance(day_info, dict) else bool(day_info)
        if is_done:
            total_days += 1
            if d_str.startswith(this_month_prefix):
                month_days += 1
    return month_days, total_days

def get_monthly_habit_summary(tracker_data, year, month):
    """指定年月の実績サマリー（記録日数、クリア総数、パーフェクト数、血圧、ゴルフ、メッセージ）を算出"""
    import calendar
    _, last_day = calendar.monthrange(year, month)
    days_recorded = 0
    total_clears = 0
    perfect_days = 0
    bp_sys_list = []
    bp_dia_list = []
    golf_days = 0
    golf_balls = 0

    for day in range(1, last_day + 1):
        d_str = f"{year:04d}-{month:02d}-{day:02d}"
        rec = tracker_data.get(d_str, {})
        if not isinstance(rec, dict):
            continue
        
        # 習慣クリア数
        done_count = sum(1 for h in HABITS_LIST if rec.get(h, False))
        has_bp = bool(rec.get("bpSys") and rec.get("bpDia"))
        has_golf = bool(rec.get("golf", {}).get("practiced", False))
        has_note = bool(rec.get("note", "").strip()) if isinstance(rec.get("note"), str) else False

        if done_count > 0 or has_bp or has_golf or has_note:
            days_recorded += 1
            total_clears += done_count
            if done_count >= len(HABITS_LIST):
                perfect_days += 1
        
        if has_bp:
            try:
                bp_sys_list.append(int(rec["bpSys"]))
                bp_dia_list.append(int(rec["bpDia"]))
            except (ValueError, TypeError):
                pass
        
        if has_golf:
            golf_days += 1
            try:
                golf_balls += int(rec.get("golf", {}).get("balls", 0))
            except (ValueError, TypeError):
                pass

    avg_sys = int(sum(bp_sys_list) / len(bp_sys_list)) if bp_sys_list else None
    avg_dia = int(sum(bp_dia_list) / len(bp_dia_list)) if bp_dia_list else None

    # 温かく励みになるメッセージの選定
    if perfect_days >= 8 or total_clears >= 100:
        message = "圧倒的な継続力です！パーフェクト達成が多数あり、健康・学習習慣が完全に自分の力になっていますね！素晴らしいです！"
    elif perfect_days >= 3 or total_clears >= 50:
        message = "とても素晴らしいペースで習慣をクリアできています！毎日の積み重ねが確実に大きな成果につながっていますね！"
    elif days_recorded >= 10:
        message = "安定したペースでしっかり記録できています！体調や予定に合わせて無理なく継続していきましょうね！"
    elif days_recorded > 0:
        message = "今月も一歩ずつ着実に積み重ねています！自分のペースを大切に、気持ちよく日課を続けていきましょうね！"
    else:
        message = "新しい月のスタートです！体調と相談しながら、日々の習慣を楽しく記録していきましょう！"

    return {
        "days_recorded": days_recorded,
        "last_day": last_day,
        "total_clears": total_clears,
        "perfect_days": perfect_days,
        "bp_count": len(bp_sys_list),
        "avg_sys": avg_sys,
        "avg_dia": avg_dia,
        "golf_days": golf_days,
        "golf_balls": golf_balls,
        "message": message,
    }

def render_monthly_calendar_html(tracker_data, year, month, selected_date, today):
    """指定年月のカレンダーをHTMLグリッドで描画"""
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    month_matrix = cal.monthdatescalendar(year, month)

    html_parts = []
    html_parts.append('<div style="background-color: #0F172A; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin-bottom: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">')

    # 曜日ヘッダー
    week_headers = [
        ("日", "#F87171"),
        ("月", "#CBD5E1"),
        ("火", "#CBD5E1"),
        ("水", "#CBD5E1"),
        ("木", "#CBD5E1"),
        ("金", "#CBD5E1"),
        ("土", "#60A5FA"),
    ]
    html_parts.append('<div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; text-align: center; font-weight: 700; font-size: 0.85rem; margin-bottom: 8px;">')
    for label, col in week_headers:
        html_parts.append(f'<div style="color: {col}; padding: 4px 0; background: rgba(30, 41, 59, 0.5); border-radius: 6px;">{label}</div>')
    html_parts.append('</div>')

    # 日付グリッド
    html_parts.append('<div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px;">')

    for week in month_matrix:
        for d in week:
            d_str = d.strftime("%Y-%m-%d")
            is_cur_month = (d.month == month)
            is_today = (d == today)
            is_selected = (d == selected_date)

            rec = tracker_data.get(d_str, {}) if is_cur_month else {}
            if not isinstance(rec, dict):
                rec = {}

            done_count = sum(1 for h in HABITS_LIST if rec.get(h, False))
            total_habits = len(HABITS_LIST)
            bp_sys = rec.get("bpSys")
            bp_dia = rec.get("bpDia")
            golf_info = rec.get("golf", {})
            has_golf = bool(isinstance(golf_info, dict) and golf_info.get("practiced", False))
            golf_balls = golf_info.get("balls", 0) if has_golf else 0
            note = str(rec.get("note", "")).strip() if rec.get("note") else ""

            # マス目のスタイリング
            if not is_cur_month:
                cell_style = "background: rgba(15, 23, 42, 0.4); border: 1px dashed rgba(51, 65, 85, 0.4); opacity: 0.35;"
                badge_html = ""
            else:
                if done_count == total_habits and total_habits > 0:
                    cell_style = "background: linear-gradient(135deg, rgba(6, 78, 59, 0.65), rgba(5, 150, 105, 0.45)); border: 1.5px solid #10B981;"
                    badge_html = f'<span style="background: #10B981; color: white; font-weight: 700; border-radius: 4px; padding: 1px 5px; font-size: 0.72rem; box-shadow: 0 0 6px rgba(16,185,129,0.5);">👑 {done_count}/{total_habits}</span>'
                elif done_count >= 5:
                    cell_style = "background: rgba(6, 95, 70, 0.35); border: 1px solid #059669;"
                    badge_html = f'<span style="background: #059669; color: #ECFDF5; font-weight: 600; border-radius: 4px; padding: 1px 5px; font-size: 0.72rem;">✨ {done_count}/{total_habits}</span>'
                elif done_count >= 1:
                    cell_style = "background: rgba(22, 78, 99, 0.3); border: 1px solid #0891B2;"
                    badge_html = f'<span style="background: #0891B2; color: #CFFAFE; font-weight: 600; border-radius: 4px; padding: 1px 5px; font-size: 0.72rem;">{done_count}/{total_habits}</span>'
                else:
                    cell_style = "background: rgba(30, 41, 59, 0.4); border: 1px solid #334155;"
                    badge_html = '<span style="color: #475569; font-size: 0.72rem;">-</span>'

            # 選択中と今日の特別ハイライト
            if is_selected:
                cell_style += " outline: 2.5px solid #F59E0B; box-shadow: 0 0 12px rgba(245, 158, 11, 0.5); z-index: 2;"
            elif is_today:
                cell_style += " outline: 2px solid #6366F1; box-shadow: 0 0 8px rgba(99, 102, 241, 0.4);"

            # 日付の色
            if d.weekday() == 6:  # 日曜
                date_num_color = "#F87171"
            elif d.weekday() == 5:  # 土曜
                date_num_color = "#60A5FA"
            else:
                date_num_color = "#F1F5F9"

            top_tag = ""
            if is_selected:
                top_tag = '<span style="background: #F59E0B; color: #0F172A; font-size: 0.62rem; font-weight: 800; padding: 1px 4px; border-radius: 3px; margin-left: 3px;">選択中</span>'
            elif is_today:
                top_tag = '<span style="background: #6366F1; color: white; font-size: 0.62rem; font-weight: 700; padding: 1px 4px; border-radius: 3px; margin-left: 3px;">TODAY</span>'

            # サブ情報（血圧・ゴルフ・メモ）
            sub_info = []
            if bp_sys and bp_dia:
                sub_info.append(f'<div style="color: #FCA5A5; font-size: 0.68rem; margin-top: 2px; white-space: nowrap;">🩺 {bp_sys}/{bp_dia}</div>')
            if has_golf:
                sub_info.append(f'<div style="color: #C4B5FD; font-size: 0.68rem; margin-top: 1px; white-space: nowrap;">🏌️ {golf_balls}球</div>')
            if note:
                escaped_note = note.replace('"', '&quot;')
                sub_info.append(f'<div style="color: #94A3B8; font-size: 0.66rem; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{escaped_note}">📝 {escaped_note[:7]}</div>')

            html_parts.append(f'''
            <div style="{cell_style} border-radius: 8px; padding: 6px 7px; min-height: 82px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 3px;">
                        <span style="color: {date_num_color}; font-weight: 700; font-size: 0.88rem;">{d.day}</span>
                        <div>{top_tag}</div>
                    </div>
                    <div>{badge_html}</div>
                </div>
                <div>{"".join(sub_info)}</div>
            </div>
            ''')

    html_parts.append('</div>')

    # カレンダー凡例
    html_parts.append('''
    <div style="margin-top: 12px; padding-top: 8px; border-top: 1px dashed #334155; display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.76rem; color: #94A3B8; align-items: center;">
        <span style="font-weight: 600; color: #CBD5E1;">凡例:</span>
        <span style="display: inline-flex; align-items: center; gap: 4px;"><span style="background: #10B981; width: 10px; height: 10px; border-radius: 2px; display: inline-block;"></span> 👑 8/8 全達成</span>
        <span style="display: inline-flex; align-items: center; gap: 4px;"><span style="background: #059669; width: 10px; height: 10px; border-radius: 2px; display: inline-block;"></span> ✨ 5〜7項目</span>
        <span style="display: inline-flex; align-items: center; gap: 4px;"><span style="background: #0891B2; width: 10px; height: 10px; border-radius: 2px; display: inline-block;"></span> 1〜4項目</span>
        <span style="display: inline-flex; align-items: center; gap: 4px;"><span style="outline: 2px solid #F59E0B; width: 8px; height: 8px; border-radius: 2px; display: inline-block;"></span> 選択中の編集日</span>
        <span style="display: inline-flex; align-items: center; gap: 4px;"><span style="outline: 2px solid #6366F1; width: 8px; height: 8px; border-radius: 2px; display: inline-block;"></span> 本日(TODAY)</span>
    </div>
    ''')

    html_parts.append('</div>')
    return "".join(html_parts)

def load_stocks_config():
    """stock-monitorのCSVが存在すればそこから最新読み込み、無ければstocks_config.jsonから読み込む"""
    portfolio_csv = "G:/マイドライブ/Antiglavity/.agent/stock-monitor/portfolio.csv"
    watchlist_csv = "G:/マイドライブ/Antiglavity/.agent/stock-monitor/watchlist.csv"
    
    holdings = []
    watchlist = []
    
    # 1. ローカルPC上でstock-monitorのCSVが存在する場合（優先）
    if os.path.exists(portfolio_csv):
        try:
            import csv
            with open(portfolio_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    c = row.get("銘柄コード", "").strip()
                    n = row.get("銘柄名", "").strip()
                    if c and n:
                        holdings.append({
                            "code": c,
                            "name": n,
                            "buy_price": row.get("取得単価", "").strip(),
                            "shares": row.get("株数", "").strip(),
                            "account_type": row.get("特定口座区分", "").strip(),
                            "category": row.get("カテゴリ", "").strip(),
                            "current_price": row.get("最新株価", "").strip(),
                            "dividend_yield": row.get("配当利回り", "").strip(),
                            "target_price": row.get("目標株価", "").strip(),
                            "per": row.get("PER", "").strip(),
                            "pbr": row.get("PBR", "").strip(),
                            "profit_val": row.get("評価損益", "").strip(),
                            "profit_rate": row.get("評価損益率", "").strip(),
                        })
        except Exception:
            pass
            
    if os.path.exists(watchlist_csv):
        try:
            import csv
            with open(watchlist_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    c = row.get("銘柄コード", "").strip()
                    n = row.get("銘柄名", "").strip()
                    cat = row.get("カテゴリ", "").strip()
                    diff = row.get("目標乖離率", "").strip()
                    if c and n:
                        watchlist.append({
                            "code": c,
                            "name": n,
                            "category": cat,
                            "diff": diff,
                            "memo": f"{cat} (目標乖離: {diff})" if diff else cat
                        })
        except Exception:
            pass
            
    # stocks_config.json から追加資産情報（米国株、投資信託、DC年金等）を取得
    other_assets = {
        "us_stocks": 4590000,
        "mutual_funds": 4430000,
        "dc_pension": 3830000,
        "bonds_other": 200000,
        "memo": "米国株式、積立投資信託、確定拠出年金(DC:外国株・債券等)"
    }
    config_path = os.path.join(os.path.dirname(__file__), "stocks_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not holdings:
                    holdings = data.get("holdings", [])
                if not watchlist:
                    watchlist = data.get("watchlist", [])
                if "other_assets" in data:
                    other_assets = data["other_assets"]
        except Exception:
            pass
                
    return {"holdings": holdings, "watchlist": watchlist, "other_assets": other_assets}

def save_watchlist_config(watchlist_items):
    """ウォッチリストをstocks_config.jsonに保存して永続化"""
    config_path = os.path.join(os.path.dirname(__file__), "stocks_config.json")
    try:
        data = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["watchlist"] = watchlist_items
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_other_assets_config(other_assets):
    """日本株以外の資産（米国株、投資信託、DC等）をstocks_config.jsonに保存して永続化"""
    config_path = os.path.join(os.path.dirname(__file__), "stocks_config.json")
    try:
        data = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["other_assets"] = other_assets
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

default_stocks = load_stocks_config()
if "stock_holdings" not in st.session_state:
    st.session_state["stock_holdings"] = default_stocks.get("holdings", [])
if "stock_watchlist" not in st.session_state:
    st.session_state["stock_watchlist"] = default_stocks.get("watchlist", [])
if "other_assets" not in st.session_state:
    st.session_state["other_assets"] = default_stocks.get("other_assets", {
        "us_stocks": 4590000,
        "mutual_funds": 4430000,
        "dc_pension": 3830000,
        "bonds_other": 200000,
        "memo": "米国株式、積立投資信託、確定拠出年金(DC:外国株・債券等)"
    })
if "stock_news_results" not in st.session_state:
    st.session_state["stock_news_results"] = None
if "stock_news_markdown" not in st.session_state:
    st.session_state["stock_news_markdown"] = None
if "stock_news_sources" not in st.session_state:
    st.session_state["stock_news_sources"] = []
if "stock_news_last_updated" not in st.session_state:
    st.session_state["stock_news_last_updated"] = None
if "stock_selected_tab_mode" not in st.session_state:
    st.session_state["stock_selected_tab_mode"] = "保有銘柄"
if "stock_discovery_results" not in st.session_state:
    st.session_state["stock_discovery_results"] = None
if "stock_discovery_sources" not in st.session_state:
    st.session_state["stock_discovery_sources"] = []
if "stock_discovery_last_updated" not in st.session_state:
    st.session_state["stock_discovery_last_updated"] = None
if "stock_discovery_title" not in st.session_state:
    st.session_state["stock_discovery_title"] = ""
if "portfolio_diagnosis_results" not in st.session_state:
    st.session_state["portfolio_diagnosis_results"] = None
if "portfolio_diagnosis_last_updated" not in st.session_state:
    st.session_state["portfolio_diagnosis_last_updated"] = None

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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 市況ブリーフィング",
    "📈 銘柄ニュース",
    "🎯 銘柄発掘",
    "💼 ポートフォリオAI診断",
    "💡 思考整理・ブレスト",
    "📝 タスク・アドバイザー",
    "🏃 習慣・健康・ToDo",
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
                    custom_instruction_text = get_custom_instructions()
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.7,
                            system_instruction=custom_instruction_text if custom_instruction_text else None,
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
# タブ2：銘柄ニュース・材料（Stock Intelligence）
# =============================================================================
with tab2:
    col_s_mode, col_s_mgmt = st.columns([2.8, 1.2])
    with col_s_mode:
        stock_mode = st.radio(
            "対象カテゴリ",
            ["💼 保有銘柄 (ポートフォリオ)", "⭐ 購入検討銘柄 (ウォッチリスト)", "🔎 自由検索 (リスト外の銘柄)"],
            horizontal=True,
            label_visibility="collapsed",
            key="rad_stock_mode",
        )
    is_portfolio = "保有銘柄" in stock_mode
    is_watchlist = "購入検討銘柄" in stock_mode
    is_free_search = "自由検索" in stock_mode

    # 購入検討銘柄の追加・管理（ウォッチリスト時のみ表示）
    if is_watchlist:
        with st.expander("➕ 新しい購入検討銘柄の追加・削除管理"):
            f_col1, f_col2, f_col3, f_col4 = st.columns([1.2, 2.0, 2.5, 1.0])
            with f_col1:
                new_code = st.text_input("コード", placeholder="例: 7203", key="in_new_stock_code")
            with f_col2:
                new_name = st.text_input("銘柄名", placeholder="例: トヨタ自動車", key="in_new_stock_name")
            with f_col3:
                new_memo = st.text_input("メモ・注目点", placeholder="例: EV/HV世界首位、好業績", key="in_new_stock_memo")
            with f_col4:
                st.write("")
                add_stock_btn = st.button("追加", key="btn_add_watchlist_stock", use_container_width=True)

            if add_stock_btn and new_code.strip() and new_name.strip():
                existing_codes = [s["code"] for s in st.session_state["stock_watchlist"]]
                if new_code.strip() not in existing_codes:
                    st.session_state["stock_watchlist"].append({
                        "code": new_code.strip(),
                        "name": new_name.strip(),
                        "memo": new_memo.strip() or "購入検討"
                    })
                    save_watchlist_config(st.session_state["stock_watchlist"])
                    st.success(f"{new_name.strip()} ({new_code.strip()}) をウォッチリストに追加しました！")
                    st.rerun()
                else:
                    st.warning("すでに登録されている銘柄コードです。")

            if st.session_state["stock_watchlist"]:
                st.caption("【登録済みの購入検討銘柄（クリックで削除可能）】")
                del_cols = st.columns(min(len(st.session_state["stock_watchlist"]), 4))
                for idx, s in enumerate(st.session_state["stock_watchlist"]):
                    col_idx = idx % min(len(st.session_state["stock_watchlist"]), 4)
                    with del_cols[col_idx]:
                        if st.button(f"🗑️ {s['code']} {s['name']}", key=f"del_wl_{s['code']}", help="クリックで削除"):
                            st.session_state["stock_watchlist"] = [item for item in st.session_state["stock_watchlist"] if item["code"] != s["code"]]
                            save_watchlist_config(st.session_state["stock_watchlist"])
                            st.rerun()

    # 銘柄選択または自由検索の入力
    targets_to_analyze = []
    execute_search = False

    if is_free_search:
        st.markdown(
            """
            <div style="font-size: 0.88rem; color: #94A3B8; margin-bottom: 6px;">
                リスト外の企業でも、銘柄コードや会社名（例: 6526 ソシオネクスト、テスラ、Apple など）を入力して、最新ニュース・開示情報をGoogle検索から即座に調査できます。
            </div>
            """,
            unsafe_allow_html=True
        )
        f_in_col, f_btn_col = st.columns([3.5, 1.5])
        with f_in_col:
            free_query = st.text_input(
                "検索する銘柄（コードまたは社名）",
                placeholder="例: 6526 ソシオネクスト、テスラ、任天堂、9984 ソフトバンクG など",
                key="in_free_stock_query",
                label_visibility="collapsed"
            )
        with f_btn_col:
            execute_search = st.button("🔍 最新ニュース・材料を検索", key="btn_search_free_stock", use_container_width=True)
        
        if execute_search and free_query.strip():
            targets_to_analyze = [free_query.strip()]
        elif execute_search and not free_query.strip():
            st.warning("調べたい銘柄名またはコードを入力してくださいね。")
    else:
        current_list = st.session_state["stock_watchlist"] if is_watchlist else st.session_state["stock_holdings"]
        stock_options = [f"{s['code']} {s['name']}" for s in current_list]

        if not is_watchlist:
            default_selected = [opt for opt in stock_options if any(c in opt for c in ["7011", "5803", "9147", "6501", "8316", "2914"])]
        else:
            default_selected = stock_options[:4]

        sel_col1, sel_col2 = st.columns([3.5, 1.5])
        with sel_col1:
            selected_stocks = st.multiselect(
                "分析対象銘柄（最大6銘柄推奨）",
                options=stock_options,
                default=default_selected,
                key=f"mselect_stocks_{'wl' if is_watchlist else 'hold'}",
                help="最新ニュース・適時開示・材料を分析したい銘柄を選んでください",
                label_visibility="collapsed"
            )
        with sel_col2:
            execute_search = st.button("🔍 銘柄ニュースをAI要約更新", key="btn_update_stock_news", use_container_width=True)
        
        if execute_search and selected_stocks:
            targets_to_analyze = selected_stocks
        elif execute_search and not selected_stocks:
            st.warning("分析する銘柄を少なくとも1つ選んでくださいね。")

    if st.session_state["stock_news_last_updated"]:
        st.caption(f"最終更新: {st.session_state['stock_news_last_updated']}（Google Web検索グラウンディング連携）")
    else:
        st.caption("ボタンを押すと、Google Web検索を活用して対象銘柄の最新ニュース、適時開示、株価材料をリアルタイムに調査します。")

    # AI分析実行（Google Search Grounding）
    if execute_search and targets_to_analyze:
        if not client:
            st.error("APIキーが設定されていません。サイドバーから設定してくださいね。")
        else:
            with st.spinner("Google検索と連携して、最新ニュース・適時開示・元記事リンクを調査中..."):
                target_str = "\n".join([f"- {s}" for s in targets_to_analyze])
                prompt = f"""
あなたは一流の株式・証券アナリストです。
Google検索ツールを活用し、以下の対象銘柄に関する【直近最新のニュース、決算発表・業績動向、適時開示、株価材料】を徹底調査し、詳しく分析・要約してください。

【対象銘柄】
{target_str}

【重要出力要件】
・各銘柄について、必ず以下のMarkdownフォーマットに厳格に従って出力してください。
・各銘柄の先頭は必ず「### [銘柄コードまたは略称] [銘柄名]」で始めてください。
・気になった際にユーザーが元記事を直接読めるよう、「🔗 参照元ニュース記事・情報源」に参照したWeb記事のタイトルとURLをMarkdownリンク `[記事見出しや媒体名](URL)` で必ず記載してください。

### [銘柄コードまたは略称] [銘柄名]
- **状況ステータス**: 【好材料】または【堅調】または【中立】または【警戒】または【決算注目】
- **直近の最新ニュース・適時開示**:
  （直近の具体的な出来事、日付、発表内容などを2〜3文で簡潔に）
- **好材料・強み**:
  - （材料や株価プラス要因1）
  - （材料や株価プラス要因2）
- **懸念点・リスク**:
  - （リスク要因や注意点）
- **AIインサイト・投資視点**:
  （保有継続や新規投資判断に向けたプロの着眼点を2〜3文で）
- **🔗 参照元ニュース記事・情報源**:
  - [記事タイトルや媒体名](URL)
  - [記事タイトルや媒体名](URL)
"""
                try:
                    custom_instruction_text = get_custom_instructions()
                    config = types.GenerateContentConfig(
                        temperature=0.3,
                        tools=[{"google_search": {}}],
                        system_instruction=custom_instruction_text if custom_instruction_text else None,
                    )
                    
                    response = None
                    last_error = None
                    for attempt in range(3):
                        try:
                            response = client.models.generate_content(
                                model=MODEL_NAME,
                                contents=prompt,
                                config=config,
                            )
                            if response and response.text:
                                break
                        except Exception as e:
                            last_error = e
                            time.sleep(2)
                    
                    if not response or not response.text:
                        raise last_error or Exception("ニュース情報の取得に失敗しました。")

                    # 元記事リンクの抽出（グラウンディングメタデータからバックアップ取得）
                    grounding_sources = []
                    if response.candidates and response.candidates[0].grounding_metadata:
                        gm = response.candidates[0].grounding_metadata
                        if gm.grounding_chunks:
                            for chunk in gm.grounding_chunks:
                                if chunk.web and chunk.web.uri:
                                    title = chunk.web.title or "参照元記事"
                                    uri = chunk.web.uri
                                    if not any(s["uri"] == uri for s in grounding_sources):
                                        grounding_sources.append({"title": title, "uri": uri})

                    st.session_state["stock_news_markdown"] = response.text
                    st.session_state["stock_news_sources"] = grounding_sources
                    st.session_state["stock_news_last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state["stock_news_last_targets"] = targets_to_analyze
                    st.rerun()
                except Exception as e:
                    st.error(f"銘柄ニュース取得中にエラーが発生しました: {str(e)}")

    # 自由検索で見つけた銘柄をウォッチリストに保存できる補助機能
    if is_free_search and st.session_state.get("stock_news_last_targets"):
        last_target = st.session_state["stock_news_last_targets"][0]
        with st.expander(f"⭐ 調べた銘柄（{last_target}）を購入検討銘柄に保存する"):
            parts = last_target.strip().split(maxsplit=1)
            suggested_code = parts[0] if parts[0].isdigit() else ""
            suggested_name = parts[1] if len(parts) > 1 else (parts[0] if not parts[0].isdigit() else "")
            
            s_col1, s_col2, s_col3 = st.columns([1.5, 2.5, 1.2])
            with s_col1:
                wl_code = st.text_input("コード", value=suggested_code, placeholder="例: 6526", key="in_wl_add_code")
            with s_col2:
                wl_name = st.text_input("銘柄名", value=suggested_name, placeholder="例: ソシオネクスト", key="in_wl_add_name")
            with s_col3:
                st.write("")
                if st.button("ウォッチリストに追加", key="btn_add_free_to_wl", use_container_width=True):
                    if wl_name.strip():
                        existing_codes = [s["code"] for s in st.session_state["stock_watchlist"]]
                        if wl_code.strip() and wl_code.strip() in existing_codes:
                            st.warning("すでに登録されている銘柄コードです。")
                        else:
                            st.session_state["stock_watchlist"].append({
                                "code": wl_code.strip() or "-",
                                "name": wl_name.strip(),
                                "memo": "自由検索より追加"
                            })
                            save_watchlist_config(st.session_state["stock_watchlist"])
                            st.success(f"{wl_name.strip()} をウォッチリストに追加しました！")
                            st.rerun()
                    else:
                        st.warning("銘柄名を入力してください。")

    # 表示部（最新Markdown出力＋元記事リンク）
    md_content = st.session_state.get("stock_news_markdown")
    if md_content:
        raw_blocks = [b.strip() for b in re.split(r'(?=^###\s+)', md_content, flags=re.MULTILINE) if b.strip()]
        intro_text = ""
        blocks = []
        for b in raw_blocks:
            if b.startswith("###"):
                blocks.append(b)
            else:
                intro_text = b

        if intro_text:
            st.info(intro_text)

        if blocks:
            cols_count = 2 if len(blocks) >= 2 else 1
            for i in range(0, len(blocks), cols_count):
                row_blocks = blocks[i : i + cols_count]
                cols = st.columns(cols_count)
                for idx, block in enumerate(row_blocks):
                    with cols[idx]:
                        with st.container(border=True):
                            st.markdown(block)
        else:
            with st.container(border=True):
                st.markdown(md_content)

        # 全体参照元Web記事リスト（直接開けるリンク一覧）
        sources = st.session_state.get("stock_news_sources", [])
        if sources:
            with st.expander("🌐 Google検索による参照元Web記事一覧（クリックで直接開く）", expanded=False):
                s_cols = st.columns(min(len(sources), 3))
                for s_idx, src in enumerate(sources):
                    c_col = s_cols[s_idx % min(len(sources), 3)]
                    with c_col:
                        st.markdown(
                            f"""
                            <div style="background-color: #1E293B; padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #334155;">
                                <a href="{src['uri']}" target="_blank" style="color: #60A5FA; text-decoration: none; font-size: 0.84rem; font-weight: 500; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    🔗 {src['title']}
                                </a>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
    else:
        st.markdown(
            """
            <div style="background-color: #1E293B; border: 2px dashed #334155; border-radius: 14px; padding: 40px; text-align: center; color: #94A3B8; margin-top: 10px;">
                <div style="font-size: 2rem; margin-bottom: 10px;">📈</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #F1F5F9;">銘柄ニュース・材料がまだ取得されていません</div>
                <div style="font-size: 0.9rem; margin-top: 6px;">対象銘柄を選択または入力して検索ボタンを押すと、Google Web検索から最新の材料や適時開示をAIが要約します。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# =============================================================================
# タブ3：銘柄発掘・スクリーニング（Stock Discovery & Screening）
# =============================================================================
with tab3:
    col_d_mode, col_d_info = st.columns([2.8, 1.2])
    with col_d_mode:
        discovery_mode = st.radio(
            "発掘モード",
            [
                "🚀 最近好調・テーマ別発掘",
                "🎁 株主優待おすすめ検索",
                "📅 今月決算・発表予定銘柄",
            ],
            horizontal=True,
            label_visibility="collapsed",
            key="rad_discovery_mode",
        )
    with col_d_info:
        st.caption("Google Web検索連携 🌐")

    is_trending_mode = "好調" in discovery_mode
    is_yutai_mode = "株主優待" in discovery_mode
    is_earnings_mode = "決算" in discovery_mode

    target_query_title = ""
    prompt_query_detail = ""
    run_discovery = False

    # 1. 🚀 最近好調・テーマ別発掘
    if is_trending_mode:
        st.markdown(
            """
            <div style="font-size: 0.88rem; color: #94A3B8; margin-bottom: 8px;">
                関心のあるセクターや投資テーマを選ぶと、直近で好調な理由や業績の裏付け、おすすめ度（★）付きの注目銘柄をAIが発掘・提案します。
            </div>
            """,
            unsafe_allow_html=True
        )
        t_col1, t_col2 = st.columns([3.2, 1.3])
        with t_col1:
            theme_category = st.selectbox(
                "投資テーマ・カテゴリを選択",
                [
                    "🔥 半導体・AIインフラ・先端技術（世界的な設備投資活況）",
                    "💰 高配当・バリュー・割安優良株（株主還元・低PBR是正）",
                    "🛡️ 防衛・航空宇宙・重工（地政学リスク・国策予算拡大）",
                    "🌐 総合商社・資源・エネルギー（強固な収益基盤と高還元）",
                    "🚗 自動車・EV・次世代モビリティ（円安恩恵・次世代技術）",
                    "🏦 メガバンク・大手金融（利上げ・金利上昇メリット）",
                    "💻 クラウド・DX・AIソリューション（高成長SaaS・企業変革）",
                    "🛍️ 内需拡大・インバウンド・小売消費（訪日客需要・賃上げ）",
                    "💊 医薬品・バイオ・ヘルスケア（ディフェンシブ・新薬開発）",
                    "✏️ 自由入力（任意のテーマ・業種キーワード）",
                ],
                key="sb_trending_category",
                label_visibility="collapsed"
            )
            custom_theme = ""
            if "自由入力" in theme_category:
                custom_theme = st.text_input("調べたいテーマや業種を入力してください", placeholder="例: データセンター電力、量子コンピュータ、ロボティクス など", key="in_custom_theme")
        with t_col2:
            run_discovery = st.button("🔍 好調銘柄を発掘・提案", key="btn_run_trending_discovery", use_container_width=True)

        clean_cat = theme_category.split("（")[0].replace("🔥 ", "").replace("💰 ", "").replace("🛡️ ", "").replace("🌐 ", "").replace("🚗 ", "").replace("🏦 ", "").replace("💻 ", "").replace("🛍️ ", "").replace("💊 ", "").replace("✏️ ", "")
        selected_theme = custom_theme.strip() if ("自由入力" in theme_category and custom_theme.strip()) else clean_cat
        target_query_title = f"テーマ：{selected_theme}"
        prompt_query_detail = f"""
【調査テーマ】
「{selected_theme}」分野において、直近（2026年最新動向）で業績が好調、株価が堅調、または強い買い材料・カタリストが存在するおすすめの日本株・上場企業を3〜4銘柄厳選してください。

【出力要件】
各銘柄について、必ず以下のMarkdownフォーマットに厳格に従って出力してください。
各銘柄の先頭は「### [証券コード] [銘柄名]」で始めてください。
参照した元記事や開示情報のURLを「🔗 参照元ニュース・情報源」にMarkdownリンク `[記事見出しや媒体名](URL)` で記載してください。

### [銘柄コード] [銘柄名]
- **おすすめ度**: ★★★★★（または ★★★★☆、★★★☆☆）
- **おすすめ理由・好調の背景**:
  （なぜ今好調なのか、業績の伸びや業界トレンド、受注動向などを2〜3文で具体的に解説）
- **直近の株価材料・ポジティブ要因**:
  - （直近の決算発表、適時開示、目標株価引き上げなどの具体的事実）
  - （競合に対する優位性や強み）
- **留意点・投資リスク**:
  - （株価過熱感や為替・地政学などのリスク要因）
- **プロの投資視点・着眼点**:
  （中長期または短期での投資アプローチ）
- **🔗 参照元ニュース・情報源**:
  - [記事タイトルや媒体名](URL)
"""

    # 2. 🎁 株主優待おすすめ検索
    elif is_yutai_mode:
        st.markdown(
            """
            <div style="font-size: 0.88rem; color: #94A3B8; margin-bottom: 8px;">
                権利確定月や優待ジャンル（食事券、買い物券、QUOカード等）から、利回りが高く生活に役立つおすすめ優待銘柄をリサーチします。
            </div>
            """,
            unsafe_allow_html=True
        )
        y_col1, y_col2, y_col3 = st.columns([2.2, 2.2, 1.3])
        with y_col1:
            yutai_month = st.selectbox(
                "権利確定月",
                [
                    "📅 今月（9月）権利確定の注目優待銘柄",
                    "📅 来月（10月）権利確定の優待銘柄",
                    "🌸 3月決算・超人気優待銘柄",
                    "⭐ 通年・利回り重視でいつでも持っておきたい定番優待",
                ],
                key="sb_yutai_month",
                label_visibility="collapsed"
            )
        with y_col2:
            yutai_genre = st.selectbox(
                "優待ジャンル",
                [
                    "🍽️ 人気飲食・外食チェーン食事券",
                    "🛒 買い物優待券・割引・ECクーポン",
                    "💳 QUOカード・ギフトカード等の金券",
                    "🎁 カタログギフト・各地名産品・食品",
                    "📦 自社製品詰め合わせ・日用品",
                    "🌟 全ジャンルから総合的におすすめ",
                ],
                key="sb_yutai_genre",
                label_visibility="collapsed"
            )
        with y_col3:
            run_discovery = st.button("🎁 優待銘柄をリサーチ", key="btn_run_yutai_discovery", use_container_width=True)

        target_query_title = f"株主優待：{yutai_month.split('（')[0].replace('📅 ', '').replace('🌸 ', '').replace('⭐ ', '')} × {yutai_genre.split('・')[0].replace('🍽️ ', '').replace('🛒 ', '').replace('💳 ', '').replace('🎁 ', '').replace('📦 ', '').replace('🌟 ', '')}"
        prompt_query_detail = f"""
【調査テーマ】
「{yutai_month}」かつ「ジャンル: {yutai_genre}」に該当する、個人投資家に極めて人気が高く、おすすめできる優待実施企業を3〜4銘柄厳選してください。

【出力要件】
各銘柄について、必ず以下のMarkdownフォーマットに厳格に従って出力してください。
各銘柄の先頭は「### [証券コード] [銘柄名]」で始めてください。
参照した元記事やIR情報のURLを「🔗 参照元ニュース・情報源」にMarkdownリンク `[記事見出しや媒体名](URL)` で記載してください。

### [銘柄コード] [銘柄名]
- **おすすめ度**: ★★★★★（実用性や総合利回り）
- **優待内容・権利月**:
  （優待品の内容、必要株数、権利確定月、長期保有特典の有無）
- **おすすめ理由・企業の安定性**:
  （優待の魅力に加え、業績や財務健全性、優待廃止リスクの低さを解説）
- **利回りと投資額の目安**:
  - 配当利回り＋優待利回りの総合利回り目安
  - 最低投資金額の目安
- **注意点・留意事項**:
  - （権利落ち日の株価下落リスクや優待改悪リスクなど）
- **🔗 参照元ニュース・情報源**:
  - [記事タイトルや媒体名](URL)
"""

    # 3. 📅 今月決算・発表予定銘柄
    elif is_earnings_mode:
        now_month_str = f"{now.year}年{now.month}月"
        st.markdown(
            f"""
            <div style="font-size: 0.88rem; color: #94A3B8; margin-bottom: 8px;">
                当月（{now_month_str}）および直近に決算発表を控える注目企業をリサーチし、発表予定日や事前期待値、注目着眼点を整理します。
            </div>
            """,
            unsafe_allow_html=True
        )
        e_col1, e_col2 = st.columns([3.2, 1.3])
        with e_col1:
            earnings_target = st.selectbox(
                "決算調査対象",
                [
                    f"📅 当月（{now_month_str}）に決算発表を予定している主要・注目銘柄",
                    "⚡ 直近1〜2週間以内に発表予定の重要決算銘柄",
                    "🚀 上方修正や増配発表が期待されている注目決算銘柄",
                ],
                key="sb_earnings_target",
                label_visibility="collapsed"
            )
        with e_col2:
            run_discovery = st.button("📅 注目決算銘柄をリサーチ", key="btn_run_earnings_discovery", use_container_width=True)

        target_query_title = f"決算発表：{earnings_target.split('（')[0].replace('📅 ', '').replace('⚡ ', '').replace('🚀 ', '')}"
        prompt_query_detail = f"""
【調査テーマ】
「{earnings_target}」に関して、日本株市場で機関投資家や個人投資家からの注目度が特に高い主要企業を3〜4銘柄ピックアップしてください。

【出力要件】
各銘柄について、必ず以下のMarkdownフォーマットに厳格に従って出力してください。
各銘柄の先頭は「### [証券コード] [銘柄名]」で始めてください。
参照した元記事や適時開示情報のURLを「🔗 参照元ニュース・情報源」にMarkdownリンク `[記事見出しや媒体名](URL)` で記載してください。

### [銘柄コード] [銘柄名]
- **注目度**: ★★★★★
- **決算発表予定日・決算期**:
  （予定日、2026年度第何四半期決算か）
- **今回の決算の最重要着眼点**:
  （業績進捗率、売上・利益の伸び、通期上方修正や自社株買い・増配の期待値）
- **事前コンセンサス・市場の期待動向**:
  （アナリスト予想や直近の業績トレンド、事前観測）
- **決算を控えた投資スタンス・リスク**:
  （好決算出尽くしリスクや為替影響など、発表前後の値動きに対する注意点）
- **🔗 参照元ニュース・情報源**:
  - [記事タイトルや媒体名](URL)
"""

    if st.session_state["stock_discovery_last_updated"]:
        st.caption(f"発掘結果（{st.session_state['stock_discovery_title']}）- 最終更新: {st.session_state['stock_discovery_last_updated']}")

    # AIスクリーニング実行
    if run_discovery:
        if not client:
            st.error("APIキーが設定されていません。サイドバーから設定してくださいね。")
        else:
            with st.spinner("Google検索と連携して、条件に合致する最新の銘柄・開示情報・ニュースを調査中..."):
                prompt = f"""
あなたは一流のプロ株式アナリスト・スクリーニング専門家です。
Google検索ツールを活用し、2026年直近の最新市場データ、適時開示、アナリストレポートを徹底調査した上で、以下の依頼に回答してください。

{prompt_query_detail}
"""
                try:
                    custom_instruction_text = get_custom_instructions()
                    config = types.GenerateContentConfig(
                        temperature=0.3,
                        tools=[{"google_search": {}}],
                        system_instruction=custom_instruction_text if custom_instruction_text else None,
                    )
                    
                    response = None
                    last_error = None
                    for attempt in range(3):
                        try:
                            response = client.models.generate_content(
                                model=MODEL_NAME,
                                contents=prompt,
                                config=config,
                            )
                            if response and response.text:
                                break
                        except Exception as e:
                            last_error = e
                            time.sleep(2)

                    if not response or not response.text:
                        raise last_error or Exception("銘柄情報のスクリーニングに失敗しました。")

                    # 元記事リンクの抽出
                    grounding_sources = []
                    if response.candidates and response.candidates[0].grounding_metadata:
                        gm = response.candidates[0].grounding_metadata
                        if gm.grounding_chunks:
                            for chunk in gm.grounding_chunks:
                                if chunk.web and chunk.web.uri:
                                    title = chunk.web.title or "参照元記事"
                                    uri = chunk.web.uri
                                    if not any(s["uri"] == uri for s in grounding_sources):
                                        grounding_sources.append({"title": title, "uri": uri})

                    st.session_state["stock_discovery_results"] = response.text
                    st.session_state["stock_discovery_sources"] = grounding_sources
                    st.session_state["stock_discovery_last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state["stock_discovery_title"] = target_query_title
                    st.rerun()
                except Exception as e:
                    st.error(f"銘柄スクリーニング中にエラーが発生しました: {str(e)}")

    # 表示部（2カラムカード形式 ＋ ウォッチリスト追加連携）
    disc_content = st.session_state.get("stock_discovery_results")
    if disc_content:
        raw_blocks = [b.strip() for b in re.split(r'(?=^###\s+)', disc_content, flags=re.MULTILINE) if b.strip()]
        intro_text = ""
        blocks = []
        for b in raw_blocks:
            if b.startswith("###"):
                blocks.append(b)
            else:
                intro_text = b

        if intro_text:
            st.info(intro_text)

        if blocks:
            cols_count = 2 if len(blocks) >= 2 else 1
            for i in range(0, len(blocks), cols_count):
                row_blocks = blocks[i : i + cols_count]
                cols = st.columns(cols_count)
                for idx, block in enumerate(row_blocks):
                    with cols[idx]:
                        with st.container(border=True):
                            st.markdown(block)
                            
                            # カードから銘柄コード・銘柄名を自動抽出してウォッチリスト追加ボタンを配置
                            first_line = block.split("\n")[0]
                            header_clean = first_line.replace("###", "").replace("[", "").replace("]", "").strip()
                            parts = header_clean.split(maxsplit=1)
                            p_code = parts[0] if (parts and parts[0].isdigit()) else ""
                            p_name = parts[1] if len(parts) > 1 else header_clean
                            
                            btn_label = f"⭐ {p_name} ({p_code}) をウォッチリストに追加" if p_code else f"⭐ {p_name} をウォッチリストに追加"
                            btn_key = f"btn_add_disc_wl_{i}_{idx}"
                            
                            if st.button(btn_label, key=btn_key, use_container_width=True):
                                existing_codes = [s["code"] for s in st.session_state["stock_watchlist"]]
                                if p_code and p_code in existing_codes:
                                    st.warning("すでにウォッチリストに登録されています。")
                                else:
                                    st.session_state["stock_watchlist"].append({
                                        "code": p_code or "-",
                                        "name": p_name,
                                        "memo": f"銘柄発掘（{st.session_state.get('stock_discovery_title', '')}）より追加"
                                    })
                                    save_watchlist_config(st.session_state["stock_watchlist"])
                                    st.success(f"{p_name} をウォッチリストに追加しました！「銘柄ニュース」タブでいつでも最新ニュースを確認できます。")
                                    st.rerun()
        else:
            with st.container(border=True):
                st.markdown(disc_content)

        # 参照元Web記事リスト（直接開けるリンク一覧）
        d_sources = st.session_state.get("stock_discovery_sources", [])
        if d_sources:
            with st.expander("🌐 Google検索による参照元Web記事一覧（クリックで直接開く）", expanded=False):
                s_cols = st.columns(min(len(d_sources), 3))
                for s_idx, src in enumerate(d_sources):
                    c_col = s_cols[s_idx % min(len(d_sources), 3)]
                    with c_col:
                        st.markdown(
                            f"""
                            <div style="background-color: #1E293B; padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #334155;">
                                <a href="{src['uri']}" target="_blank" style="color: #60A5FA; text-decoration: none; font-size: 0.84rem; font-weight: 500; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    🔗 {src['title']}
                                </a>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
    else:
        st.markdown(
            """
            <div style="background-color: #1E293B; border: 2px dashed #334155; border-radius: 14px; padding: 40px; text-align: center; color: #94A3B8; margin-top: 10px;">
                <div style="font-size: 2rem; margin-bottom: 10px;">🎯</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #F1F5F9;">条件を選択して銘柄をリサーチしてみましょう</div>
                <div style="font-size: 0.9rem; margin-top: 6px;">「最近好調なテーマ銘柄」「おすすめ株主優待」「今月の注目決算」から選んでボタンを押すと、AIがGoogle Web検索から銘柄を発掘・提案します。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# =============================================================================
# タブ4：ポートフォリオAI診断・リスク評価（Portfolio Intelligence）
# =============================================================================
with tab4:
    holdings_data = st.session_state.get("stock_holdings", [])
    watchlist_data = st.session_state.get("stock_watchlist", [])
    other_assets = st.session_state.get("other_assets", {})

    # 日本株（個別株）メトリクス計算
    total_buy_val = 0.0
    total_cur_val = 0.0
    total_profit_val = 0.0
    total_annual_div = 0.0
    nisa_val = 0.0
    tokutei_val = 0.0
    cat_distribution = {}
    valid_stocks_count = 0
    stock_shares_list = []

    for s in holdings_data:
        try:
            buy_p = float(str(s.get("buy_price", 0)).replace(",", "").strip() or 0)
            shs = float(str(s.get("shares", 0)).replace(",", "").strip() or 0)
            cur_p = float(str(s.get("current_price", 0)).replace(",", "").strip() or buy_p or 0)
            div_s = str(s.get("dividend_yield", "")).replace("%", "").strip()
            div_y = float(div_s) / 100.0 if div_s and div_s != "-" else 0.0

            b_val = buy_p * shs
            c_val = cur_p * shs
            profit = c_val - b_val
            ann_div = c_val * div_y

            total_buy_val += b_val
            total_cur_val += c_val
            total_profit_val += profit
            total_annual_div += ann_div

            if s.get("account_type") == "NISA":
                nisa_val += c_val
            else:
                tokutei_val += c_val

            cat = s.get("category") or "その他"
            cat_distribution[cat] = cat_distribution.get(cat, 0.0) + c_val

            if b_val > 0:
                valid_stocks_count += 1
                stock_shares_list.append({
                    "code": s.get("code", ""),
                    "name": s.get("name", ""),
                    "cur_val": c_val,
                    "profit": profit,
                    "profit_rate": (profit / b_val * 100) if b_val > 0 else 0.0,
                    "category": cat
                })
        except Exception:
            pass

    total_profit_rate = (total_profit_val / total_buy_val * 100) if total_buy_val > 0 else 0.0
    avg_dividend_rate = (total_annual_div / total_cur_val * 100) if total_cur_val > 0 else 0.0

    # 日本株以外の保有・積立資産（米国株、投資信託、確定拠出年金等）の計算
    us_stocks_val = float(other_assets.get("us_stocks", 4590000))
    mutual_funds_val = float(other_assets.get("mutual_funds", 4430000))
    dc_pension_val = float(other_assets.get("dc_pension", 3830000))
    bonds_val = float(other_assets.get("bonds_other", 200000))
    total_other_val = us_stocks_val + mutual_funds_val + dc_pension_val + bonds_val

    # 総資産額と構成比率
    grand_total_val = total_cur_val + total_other_val
    japan_stock_ratio = (total_cur_val / grand_total_val * 100) if grand_total_val > 0 else 0.0
    other_assets_ratio = (total_other_val / grand_total_val * 100) if grand_total_val > 0 else 0.0

    # 4つの上部メトリクスカード（総資産全体を可視化）
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-top: 4px solid #10B981; padding: 14px 18px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">💰 総資産評価額（全体）</div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #F8FAFC; margin-top: 4px;">¥{grand_total_val:,.0f}</div>
                <div style="font-size: 0.85rem; color: #34D399; margin-top: 4px; font-weight: 600;">
                    日本株含み益: +¥{total_profit_val:,.0f} (+{total_profit_rate:.1f}%)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m_col2:
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-top: 4px solid #3B82F6; padding: 14px 18px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">🇯🇵 国内株式（現物）</div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #F8FAFC; margin-top: 4px;">{japan_stock_ratio:.1f}%</div>
                <div style="font-size: 0.85rem; color: #60A5FA; margin-top: 4px; font-weight: 500;">
                    ¥{total_cur_val:,.0f} ({len(holdings_data)}銘柄)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m_col3:
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-top: 4px solid #8B5CF6; padding: 14px 18px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">🌏 海外・積立資産比率</div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #F8FAFC; margin-top: 4px;">{other_assets_ratio:.1f}%</div>
                <div style="font-size: 0.85rem; color: #A78BFA; margin-top: 4px; font-weight: 500;">
                    ¥{total_other_val:,.0f} (米国株・投信・DC)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m_col4:
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-top: 4px solid #F59E0B; padding: 14px 18px;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">💵 年間予想配当金</div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #F8FAFC; margin-top: 4px;">¥{total_annual_div:,.0f} <span style="font-size: 0.85rem; font-weight: 500; color: #94A3B8;">/年</span></div>
                <div style="font-size: 0.85rem; color: #FBBF24; margin-top: 4px; font-weight: 600;">
                    日本株平均利回り: {avg_dividend_rate:.2f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 日本株以外の保有・積立資産の設定・確認アコーディオン
    with st.expander("🌍 日本株以外の保有・積立資産（米国株・投資信託・DC年金など）の確認・編集"):
        st.markdown(
            """
            <div style="font-size: 0.86rem; color: #94A3B8; margin-bottom: 8px;">
                日本株以外の資産（米国株、積立投信、確定拠出年金など）の現在評価額です。金額を変更して「設定を保存」を押すと、AI診断や全体比率に即座に反映されます。
            </div>
            """,
            unsafe_allow_html=True
        )
        oa_col1, oa_col2, oa_col3, oa_col4 = st.columns(4)
        with oa_col1:
            in_us = st.number_input("🇺🇸 米国株式 (円)", value=int(us_stocks_val), step=100000, key="in_oa_us")
        with oa_col2:
            in_mf = st.number_input("📈 投資信託・積立 (円)", value=int(mutual_funds_val), step=100000, key="in_oa_mf")
        with oa_col3:
            in_dc = st.number_input("🏛️ 確定拠出年金 DC (円)", value=int(dc_pension_val), step=100000, key="in_oa_dc")
        with oa_col4:
            in_bd = st.number_input("🏷️ 債券・その他 (円)", value=int(bonds_val), step=50000, key="in_oa_bd")
        
        if st.button("💾 日本株以外の資産設定を保存", key="btn_save_other_assets"):
            st.session_state["other_assets"] = {
                "us_stocks": in_us,
                "mutual_funds": in_mf,
                "dc_pension": in_dc,
                "bonds_other": in_bd,
                "memo": "米国株式、積立投資信託、確定拠出年金(DC:外国株・債券等)"
            }
            save_other_assets_config(st.session_state["other_assets"])
            st.success("日本株以外の資産情報を保存しました！")
            st.rerun()

    # 診断実行バー
    diag_col1, diag_col2 = st.columns([3.5, 1.5])
    with diag_col1:
        st.markdown(
            """
            <div style="font-size: 0.9rem; color: #94A3B8; margin-top: 10px;">
                <strong>日本株（約74%）と海外・積立資産（約26%）の全体バランス</strong>、および日本株内部のセクター偏り、ウォッチリスト（97銘柄）をAIが総合照合。<br>
                <strong>「資産全体の偏り・弱点」「特定セクターへの集中リスク」「リスクを中和するために今買うべきおすすめ候補」</strong>を客観診断します。
            </div>
            """,
            unsafe_allow_html=True
        )
    with diag_col2:
        st.write("")
        run_diag_btn = st.button("🩺 AIでポートフォリオを精密診断", key="btn_run_portfolio_diag", use_container_width=True)

    if st.session_state.get("portfolio_diagnosis_last_updated"):
        st.caption(f"最終診断日時: {st.session_state['portfolio_diagnosis_last_updated']}")

    # AI診断実行ロジック
    if run_diag_btn:
        if not client:
            st.error("APIキーが設定されていません。サイドバーから設定してくださいね。")
        else:
            with st.spinner("日本株30銘柄、海外・積立資産、ウォッチリスト全97銘柄を照合し、資産リスクと中和策を診断中..."):
                # 保有銘柄サマリー作成
                holdings_summary_lines = []
                for s in holdings_data:
                    c = s.get("code", "")
                    n = s.get("name", "")
                    cat = s.get("category", "")
                    cp = s.get("current_price", "")
                    sh = s.get("shares", "")
                    pr = s.get("profit_rate", "")
                    div = s.get("dividend_yield", "")
                    act = s.get("account_type", "")
                    holdings_summary_lines.append(f"- [{c}] {n} | 業種:{cat} | 評価株価:{cp}円×{sh}株 | 損益率:{pr} | 配当利回り:{div} | {act}")
                holdings_summary_text = "\n".join(holdings_summary_lines)

                # ウォッチリスト（購入検討銘柄）の代表抜粋
                watchlist_summary_lines = []
                for w in watchlist_data[:40]:  # 主要40銘柄を抜粋してトークン効率化
                    wc = w.get("code", "")
                    wn = w.get("name", "")
                    wcat = w.get("category", "")
                    wdiff = w.get("diff", "")
                    watchlist_summary_lines.append(f"- [{wc}] {wn} (カテゴリ:{wcat}, 目標乖離:{wdiff})")
                watchlist_summary_text = "\n".join(watchlist_summary_lines)

                prompt = f"""
あなたは世界最高峰のチーフポートフォリオマネージャーおよび資産運用ストラテジストです。
提供されたユーザーの「総資産配分（日本株＋米国株・積立投信・確定拠出年金DC）」、「日本株保有ポートフォリオ（30銘柄）」、および「購入検討銘柄リスト（ウォッチリスト）」を徹底的に分析し、客観的で具体的、かつ親身で実行可能なプロの資産診断レポートを作成してください。

【ユーザーの総資産ポートフォリオ構成（全体像）】
・総資産評価額: 約 {grand_total_val:,.0f} 円
  ├ 1. 日本株個別株（全30銘柄）: 約 {total_cur_val:,.0f} 円 ({japan_stock_ratio:.1f}%) ── 含み益: +¥{total_profit_val:,.0f} ({total_profit_rate:+.1f}%), 年間予想配当金: ¥{total_annual_div:,.0f} (利回り {avg_dividend_rate:.2f}%)
  └ 2. 海外・積立資産合計: 約 {total_other_val:,.0f} 円 ({other_assets_ratio:.1f}%)
      ├ 米国株式: 約 {us_stocks_val:,.0f} 円
      ├ 投資信託・積立: 約 {mutual_funds_val:,.0f} 円
      ├ 確定拠出年金（企業型DC/iDeCo: 外国株式インデックス・新興国債券・バランス型等）: 約 {dc_pension_val:,.0f} 円
      └ 債券・その他: 約 {bonds_val:,.0f} 円

【日本株保有銘柄一覧（全30銘柄）】
{holdings_summary_text}

【ユーザーが関心を持っている購入検討銘柄（ウォッチリスト抜粋）】
{watchlist_summary_text}

【重要指示・前提】
・ユーザーは日本株だけでなく、米国株式や投資信託、確定拠出年金（外国株・債券等）もしっかり積立・保有されています。そのため「海外資産がゼロである」といった誤った診断は絶対にしないでください。
・全体の約74%を占める日本株個別株のウエイトの適正度、および日本株内部のセクター偏り（外食チェーン4社の重なり、重工・製造業の景気循環リスク、特定銘柄への集中）を主眼として鋭く客観的に分析してください。
・リスクを中和・相殺するために、登録されているウォッチリスト（97銘柄）の中から最も効果的な補完銘柄を推薦してください。

【出力要件】
親身でわかりやすく、かつ鋭いプロの視点で、以下のMarkdownフォーマットに厳格に従って出力してください。
各見出し（### 1. ..., ### 2. ...）を明確に記載してください。

### 1. 🎯 総合診断スコア & ポートフォリオの強み
- **総合ヘルススコア**: ★★★★☆（5段階評価で星を記載）
- **現在のポートフォリオの優れた点・強み**:
  （総資産約5,100万円超で、米国株やDC積立も並行して行っている点、日本株で大きな含み益が出ている点、高配当銘柄の確保など具体的に解説）

### 2. ⚠️ 資産の偏り & 潜在リスク（弱点の客観分析）
- **全体アセット配分の視点**:
  （米国株や投信・DC積立を保有しているものの、全体資産の約74%が日本株個別株に集中しているため、日本市場全体の地合い・円高への感応度が高い点を指摘）
- **特定銘柄への過大集中リスク**:
  （三菱重工、NXHDなど上位銘柄だけで日本株の過半を占めている集中度リスクを指摘）
- **セクター・業種の偏りリスク**:
  （外食チェーンが4銘柄（マクドナルド、サイゼリヤ、王将、コメダ）と多めで原材料高や人件費高騰リスクが重なっている点、重工業・製造業比率の高さなど）

### 3. 🛡️ リスク中和のための具体的処方箋
- **どのようなアセット・セクターを買い増すべきか**:
  （現在の偏りを中和・相殺するために、今後優先的に組み入れるべき業種や資産クラスを2〜3点提示）

### 4. ⭐ ウォッチリストから厳選！ポートフォリオの穴を埋めるおすすめ候補
ユーザーが登録している「購入検討銘柄（ウォッチリスト）」の中から、**現在のポートフォリオのリスクを中和・補完するのに最も効果的な銘柄を2〜3銘柄厳選**して推薦してください。

#### おすすめ銘柄: [証券コード] [銘柄名]
- **カテゴリ**: [カテゴリ名]
- **この銘柄を選ぶ理由（中和・補完効果）**:
  （現在の保有株とどう相関が低く、どのリスクをヘッジ・補強できるのかを明確に解説）
- **投資判断の着眼点**:
  （目標株価との乖離やエントリーの考え方）

### 5. 🌐 今後の資産運用アドバイス（積立・リバランス戦略）
- （米国株や投信積立、確定拠出年金と日本株個別株を組み合わせた、今後の無理のない運用・リバランス方針のアドバイス）
"""
                try:
                    custom_instruction_text = get_custom_instructions()
                    config = types.GenerateContentConfig(
                        temperature=0.3,
                        tools=[{"google_search": {}}],
                        system_instruction=custom_instruction_text if custom_instruction_text else None,
                    )
                    
                    response = None
                    last_error = None
                    for attempt in range(3):
                        try:
                            response = client.models.generate_content(
                                model=MODEL_NAME,
                                contents=prompt,
                                config=config,
                            )
                            if response and response.text:
                                break
                        except Exception as e:
                            last_error = e
                            time.sleep(2)

                    if not response or not response.text:
                        raise last_error or Exception("ポートフォリオ診断に失敗しました。")

                    st.session_state["portfolio_diagnosis_results"] = response.text
                    st.session_state["portfolio_diagnosis_last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.rerun()
                except Exception as e:
                    st.error(f"診断中にエラーが発生しました: {str(e)}")

    # 診断結果の表示
    diag_res = st.session_state.get("portfolio_diagnosis_results")
    if diag_res:
        with st.container(border=True):
            st.markdown(diag_res)
    else:
        st.markdown(
            """
            <div style="background-color: #1E293B; border: 2px dashed #334155; border-radius: 14px; padding: 40px; text-align: center; color: #94A3B8; margin-top: 10px;">
                <div style="font-size: 2rem; margin-bottom: 10px;">💼</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #F1F5F9;">ポートフォリオ診断がまだ実行されていません</div>
                <div style="font-size: 0.9rem; margin-top: 6px;">上の「AIでポートフォリオを精密診断」ボタンを押すと、日本株と海外・積立資産の全体バランス、保有株の偏りやリスク、ウォッチリストからの推奨補完銘柄をプロ目線で分析します。</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# =============================================================================
# タブ5：思考整理・ブレスト（Brainstorm & Wall-hit）
# =============================================================================
with tab5:
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
                    custom_instruction_text = get_custom_instructions()
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.8,
                            system_instruction=custom_instruction_text if custom_instruction_text else None,
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
# タブ6：タスク・アドバイザー（Daily Task Advisor）
# =============================================================================
with tab6:
    # 常に最新の共有タスクデータを読み込み
    tasks, advice, last_updated = load_shared_tasks_data()
    st.session_state["tasks"] = tasks
    if advice is not None:
        st.session_state["task_advice"] = advice

    task_col_left, task_col_right = st.columns([1.1, 1.1], gap="large")

    # 左側：ToDoリスト管理
    with task_col_left:
        t_head1, t_head2 = st.columns([2.8, 1.4])
        with t_head1:
            st.markdown(
                """
                <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 2px;">
                    📋 今日のタスク一覧
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 8px;">
                    ☁️ 全端末リアルタイム同期（PC・タブレット・スマホ共通）
                </div>
                """,
                unsafe_allow_html=True,
            )
        with t_head2:
            if st.button("🔄 最新同期", key="btn_sync_tasks", help="他端末での更新内容を再読込して画面を最新化します", use_container_width=True):
                for k in list(st.session_state.keys()):
                    if k.startswith("task_check_"):
                        del st.session_state[k]
                st.rerun()

        # タスク追加フォーム
        with st.form(key="add_task_form", clear_on_submit=True):
            add_col1, add_col2 = st.columns([3.5, 1.2])
            with add_col1:
                new_task_text = st.text_input("タスク名", placeholder="新しいタスクを入力...", label_visibility="collapsed")
            with add_col2:
                submitted = st.form_submit_button("＋ 追加", use_container_width=True)
            if submitted and new_task_text.strip():
                tasks, advice, _ = load_shared_tasks_data()
                new_id = max([t["id"] for t in tasks], default=0) + 1
                tasks.append({"id": new_id, "text": new_task_text.strip(), "done": False})
                st.session_state[f"task_check_{new_id}"] = False
                save_shared_tasks_data(tasks, advice)
                st.rerun()

        # タスク一覧表示
        tasks, advice, last_updated = load_shared_tasks_data()
        if not tasks:
            st.info("登録されているタスクはありません。上のフォームから追加してください。")
        else:
            for task in tasks:
                t_col1, t_col2 = st.columns([4, 1])
                with t_col1:
                    if f"task_check_{task['id']}" not in st.session_state:
                        st.session_state[f"task_check_{task['id']}"] = task["done"]
                    is_done = st.checkbox(
                        task["text"],
                        key=f"task_check_{task['id']}",
                    )
                    if is_done != task["done"]:
                        task["done"] = is_done
                        save_shared_tasks_data(tasks, advice)
                        st.rerun()
                with t_col2:
                    if st.button("削除", key=f"del_task_{task['id']}", help="このタスクを削除"):
                        tasks = [t for t in tasks if t["id"] != task["id"]]
                        st.session_state.pop(f"task_check_{task['id']}", None)
                        save_shared_tasks_data(tasks, advice)
                        st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        t_btn_col1, t_btn_col2 = st.columns([2, 1])
        with t_btn_col1:
            get_advice = st.button("✨ AIアドバイスを生成", key="btn_get_task_advice", use_container_width=True)
        with t_btn_col2:
            if st.button("完了を一括消去", key="btn_clear_done", use_container_width=True):
                tasks, advice, _ = load_shared_tasks_data()
                for t in tasks:
                    if t["done"]:
                        st.session_state.pop(f"task_check_{t['id']}", None)
                tasks = [t for t in tasks if not t["done"]]
                save_shared_tasks_data(tasks, advice)
                st.rerun()

        if last_updated:
            st.markdown(
                f"<div style='font-size: 0.78rem; color: #64748B; margin-top: 8px; text-align: right;'>🕒 最終同期: {last_updated}</div>",
                unsafe_allow_html=True,
            )

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
            active_tasks = [t["text"] for t in tasks if not t["done"]]
            done_tasks = [t["text"] for t in tasks if t["done"]]

            if not active_tasks and not done_tasks:
                st.warning("分析するタスクがありません。先にタスクを登録してください。")
            elif not client:
                st.error("APIキーが設定されていません。サイドバーから設定してください。")
            else:
                with st.spinner("タスクの優先度と段取りを分析中..."):
                    task_summary_text = f"【未完了タスク】: {', '.join(active_tasks) if active_tasks else 'なし'}\n"
                    task_summary_text += f"【完了済みタスク】: {', '.join(done_tasks) if done_tasks else 'なし'}"

                    # 習慣トラッカー・個別タスクの今日の未完了状況もAIプロンプトに統合
                    today_str = datetime.date.today().strftime("%Y-%m-%d")
                    tk_data_current = load_taskkanri_data()
                    today_habits = tk_data_current.get("trackerData", {}).get(today_str, {})
                    incomplete_habits = [h for h in HABITS_LIST if not today_habits.get(h, False)]
                    incomplete_adhoc = [t.get("title") for t in tk_data_current.get("adhocTasks", []) if t.get("status") != "完了"]
                    if incomplete_habits:
                        task_summary_text += f"\n【本日の未完了日課（習慣・健康）】: {', '.join(incomplete_habits)}"
                    if incomplete_adhoc:
                        task_summary_text += f"\n【進行中の重要個別ToDo】: {', '.join(incomplete_adhoc[:5])}"

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
                    custom_instruction_text = get_custom_instructions()
                    try:
                        response = client.models.generate_content(
                            model=MODEL_NAME,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.7,
                                system_instruction=custom_instruction_text if custom_instruction_text else None,
                            ),
                        )
                        new_advice = json.loads(response.text)
                        st.session_state["task_advice"] = new_advice
                        save_shared_tasks_data(tasks, new_advice)
                        st.rerun()
                    except Exception as e:
                        st.error(f"アドバイス生成中にエラーが発生しました: {str(e)}")

        advice_to_show = st.session_state.get("task_advice") or advice
        if advice_to_show:
            st.markdown(
                f"""<div class="dashboard-card" style="border-left: 4px solid #6366F1;">
<div style="font-size: 0.95rem; font-weight: 700; color: #818CF8; margin-bottom: 6px;">🔥 最優先で終わらせるべきタスク</div>
<div style="font-size: 0.92rem; color: #F8FAFC; line-height: 1.5; margin-bottom: 14px;">{advice_to_show.get("priority_task", "")}</div>
<div style="font-size: 0.95rem; font-weight: 700; color: #34D399; margin-bottom: 6px;">⏱️ 進め方 & 段取りのコツ</div>
<div style="font-size: 0.92rem; color: #F8FAFC; line-height: 1.5; margin-bottom: 14px;">{advice_to_show.get("strategy", "")}</div>
<div style="font-size: 0.95rem; font-weight: 700; color: #F472B6; margin-bottom: 6px;">💬 モチベーションメッセージ</div>
<div style="font-size: 0.92rem; color: #FDE047; font-style: italic; line-height: 1.5;">"{advice_to_show.get("motivation", "")}"</div>
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

# =============================================================================
# タブ7：習慣・健康・ToDo（Habit & Health & Task Tracker）
# =============================================================================
with tab7:
    tk_data = load_taskkanri_data()
    tracker_data = tk_data.get("trackerData", {})
    adhoc_tasks = tk_data.get("adhocTasks", [])

    # ヘッダー
    t7_h1, t7_h2 = st.columns([3, 1.5])
    with t7_h1:
        st.markdown(
            """
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-bottom: 2px;">
                🏃 毎日の習慣・健康記録 & 個別タスク
            </div>
            <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 10px;">
                日課の達成記録・血圧・ゴルフ球数・個別ToDoを全端末で一元管理（過去データ完全保持）
            </div>
            """,
            unsafe_allow_html=True,
        )
    with t7_h2:
        if st.button("🔄 最新データを再読込", key="btn_sync_taskkanri", use_container_width=True):
            st.rerun()

    # データ移行・インポート / エクスポート用 Expander
    with st.expander("📥 過去データの移行（JSON貼り付け）/ 💾 バックアップ"):
        st.markdown(
            """
            <div style="font-size: 0.88rem; color: #CBD5E1; margin-bottom: 8px;">
                <b>過去の記録を引き継ぐ方法:</b><br>
                以前のタスク管理アプリ（<code>taskkanri</code>）で「💾 データをバックアップ」からダウンロードしたJSONファイルの内容、またはFirebase FirestoreからコピーしたJSONテキストを、下の枠にそのまま貼り付けて「インポート実行」ボタンを押してください。<br>
                過去の日課実績・血圧・メモ・タスクがすべて復元され、安全に保管されます。
            </div>
            """,
            unsafe_allow_html=True,
        )
        import_text = st.text_area("JSONデータを貼り付け", height=120, placeholder='{"trackerData": {...}, "adhocTasks": [...]} または Firestoreのデータ', key="ta_import_json")
        btn_col_imp1, btn_col_imp2 = st.columns([1.5, 2.5])
        with btn_col_imp1:
            if st.button("📥 インポート実行", key="btn_do_import", use_container_width=True):
                if import_text.strip():
                    try:
                        parsed = json.loads(import_text.strip())
                        imported_tracker = {}
                        imported_tasks = []

                        if isinstance(parsed, dict):
                            if "trackerData" in parsed and isinstance(parsed["trackerData"], dict):
                                imported_tracker = parsed["trackerData"]
                            else:
                                if any(isinstance(v, (dict, bool)) for v in parsed.values()):
                                    imported_tracker = parsed

                            if "adhocTasks" in parsed and isinstance(parsed["adhocTasks"], list):
                                imported_tasks = parsed["adhocTasks"]
                        
                        merged_tracker = {**tracker_data, **imported_tracker}
                        existing_ids = {t.get("id") for t in adhoc_tasks}
                        merged_tasks = list(adhoc_tasks)
                        for t in imported_tasks:
                            if t.get("id") not in existing_ids:
                                merged_tasks.append(t)
                                existing_ids.add(t.get("id"))
                            else:
                                for idx, et in enumerate(merged_tasks):
                                    if et.get("id") == t.get("id"):
                                        merged_tasks[idx] = t

                        tk_data["trackerData"] = merged_tracker
                        tk_data["adhocTasks"] = merged_tasks
                        save_taskkanri_data(tk_data)
                        st.success(f"✅ インポート成功！日課記録 {len(merged_tracker)} 日分、個別タスク {len(merged_tasks)} 件を保存・復元しました。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"JSONの解析に失敗しました: {e}")
                else:
                    st.warning("JSONテキストを入力してください。")
        with btn_col_imp2:
            current_json_str = json.dumps(tk_data, ensure_ascii=False, indent=2)
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            st.download_button(
                label="💾 現在の全データをJSONダウンロード（バックアップ）",
                data=current_json_str,
                file_name=f"habit-tracker-backup-{today_str}.json",
                mime="application/json",
                use_container_width=True,
                key="btn_dl_backup"
            )

    # -------------------------------------------------------------------------
    # 1. 月間カレンダー & 頑張りサマリー
    # -------------------------------------------------------------------------
    today = datetime.date.today()
    if "in_habit_date" not in st.session_state:
        st.session_state["in_habit_date"] = today
    if "cal_view_year" not in st.session_state:
        st.session_state["cal_view_year"] = today.year
    if "cal_view_month" not in st.session_state:
        st.session_state["cal_view_month"] = today.month

    cal_year = st.session_state["cal_view_year"]
    cal_month = st.session_state["cal_view_month"]

    # 年月切り替えバー
    cal_nav1, cal_nav2, cal_nav3, cal_nav4 = st.columns([1.2, 2.5, 1.2, 1.5])
    with cal_nav1:
        if st.button("◀ 前月", key="btn_cal_prev_month", use_container_width=True):
            if cal_month == 1:
                st.session_state["cal_view_year"] -= 1
                st.session_state["cal_view_month"] = 12
            else:
                st.session_state["cal_view_month"] -= 1
            st.rerun()
    with cal_nav2:
        is_this_month = (cal_year == today.year and cal_month == today.month)
        st.markdown(
            f"""
            <div style="text-align: center; font-size: 1.15rem; font-weight: 700; color: #F8FAFC; padding-top: 4px;">
                📅 {cal_year}年 {cal_month}月 の実績カレンダー
                {"<span style='background: #3B82F6; color: white; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; margin-left: 6px;'>当月</span>" if is_this_month else ""}
            </div>
            """,
            unsafe_allow_html=True
        )
    with cal_nav3:
        if st.button("翌月 ▶", key="btn_cal_next_month", use_container_width=True):
            if cal_month == 12:
                st.session_state["cal_view_year"] += 1
                st.session_state["cal_view_month"] = 1
            else:
                st.session_state["cal_view_month"] += 1
            st.rerun()
    with cal_nav4:
        if st.button("今月に戻る", key="btn_cal_reset_month", use_container_width=True):
            st.session_state["cal_view_year"] = today.year
            st.session_state["cal_view_month"] = today.month
            st.rerun()

    # 今月の頑張りサマリーカード
    m_summary = get_monthly_habit_summary(tracker_data, cal_year, cal_month)
    bp_text = f"{m_summary['avg_sys']}/{m_summary['avg_dia']} mmHg" if m_summary['avg_sys'] else "未記録"
    golf_text = f"{m_summary['golf_days']}回 ({m_summary['golf_balls']}球)" if m_summary['golf_days'] > 0 else "なし"

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%); border: 1px solid #4338CA; border-radius: 12px; padding: 14px 18px; margin-bottom: 14px; box-shadow: 0 4px 15px rgba(67, 56, 202, 0.25);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 1.05rem; font-weight: 700; color: #E0E7FF; display: flex; align-items: center; gap: 8px;">
                    <span>🏆 {cal_year}年{cal_month}月 の頑張りサマリー</span>
                </div>
                <div style="font-size: 0.8rem; color: #A5B4FC; font-weight: 600;">
                    記録日数: <b style="color: #F8FAFC; font-size: 0.95rem;">{m_summary['days_recorded']}</b> / {m_summary['last_day']} 日
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 10px; background: rgba(0,0,0,0.25); padding: 10px 14px; border-radius: 8px;">
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">日課クリア総数</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: #34D399;">{m_summary['total_clears']} <span style="font-size: 0.8rem; font-weight: 400; color: #CBD5E1;">回</span></div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">パーフェクト達成 (8/8)</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: #FBBF24;">👑 {m_summary['perfect_days']} <span style="font-size: 0.8rem; font-weight: 400; color: #CBD5E1;">日</span></div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">血圧測定 & 平均値</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: #F87171; margin-top: 2px;">{bp_text} <span style="font-size: 0.75rem; font-weight: 400; color: #94A3B8;">({m_summary['bp_count']}日)</span></div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">ゴルフ打ちっぱなし</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: #C4B5FD; margin-top: 2px;">🏌️ {golf_text}</div>
                </div>
            </div>
            <div style="font-size: 0.85rem; color: #FDE047; line-height: 1.4; display: flex; align-items: center; gap: 6px;">
                <span>💬 <b>{m_summary['message']}</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # カレンダーの描画（現在選択中の編集日 sel_date を渡す）
    cur_target_date = st.session_state["in_habit_date"]
    cal_html = render_monthly_calendar_html(tracker_data, cal_year, cal_month, cur_target_date, today)
    st.markdown(cal_html, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 2. 実績の入力・確認（日付ナビゲーション & チェックリスト）
    # -------------------------------------------------------------------------
    st.markdown("<div style='margin-top: 14px; margin-bottom: 8px; font-weight: 700; font-size: 1.05rem; color: #EEF2FF;'>📝 実績の入力・記録</div>", unsafe_allow_html=True)

    d_col1, d_col2, d_col3, d_col4 = st.columns([1, 1, 1.8, 2.5])
    with d_col1:
        if st.button("◀ 前日", key="btn_prev_date", use_container_width=True):
            st.session_state["in_habit_date"] -= datetime.timedelta(days=1)
            # 月が変わればカレンダーの表示月も連動
            st.session_state["cal_view_year"] = st.session_state["in_habit_date"].year
            st.session_state["cal_view_month"] = st.session_state["in_habit_date"].month
            st.rerun()
    with d_col2:
        if st.button("翌日 ▶", key="btn_next_date", use_container_width=True):
            st.session_state["in_habit_date"] += datetime.timedelta(days=1)
            # 月が変わればカレンダーの表示月も連動
            st.session_state["cal_view_year"] = st.session_state["in_habit_date"].year
            st.session_state["cal_view_month"] = st.session_state["in_habit_date"].month
            st.rerun()
    with d_col3:
        if st.button("📅 今日に戻る", key="btn_today_date", use_container_width=True):
            st.session_state["in_habit_date"] = today
            st.session_state["cal_view_year"] = today.year
            st.session_state["cal_view_month"] = today.month
            st.rerun()
    with d_col4:
        new_d = st.date_input(
            "対象日を選択",
            key="in_habit_date",
            label_visibility="collapsed"
        )
        if new_d.year != st.session_state.get("cal_view_year") or new_d.month != st.session_state.get("cal_view_month"):
            st.session_state["cal_view_year"] = new_d.year
            st.session_state["cal_view_month"] = new_d.month
            st.rerun()

    sel_date = st.session_state["in_habit_date"]
    sel_date_str = sel_date.strftime("%Y-%m-%d")
    is_today = (sel_date == today)

    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_label = weekday_names[sel_date.weekday()]

    day_record = tracker_data.get(sel_date_str, {})
    if not isinstance(day_record, dict):
        day_record = {}

    st.markdown(
        f"""
        <div style="font-size: 1.1rem; font-weight: 700; color: #EEF2FF; margin-top: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            <span>📅 {sel_date.strftime('%Y年%m月%d日')} ({weekday_label}) の実績</span>
            {"<span class='category-badge badge-neutral' style='background: #4338CA; color: white;'>TODAY</span>" if is_today else "<span class='category-badge badge-neutral' style='background: #475569; color: #CBD5E1;'>過去記録</span>"}
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_habits, col_adhoc = st.columns([1.15, 1.1], gap="large")

    # 左カラム：日課の達成チェック & 血圧 & ゴルフ & 備考
    with col_habits:
        st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #F1F5F9; margin-bottom: 8px;'>✅ 定常日課チェックリスト</div>", unsafe_allow_html=True)

        done_count = sum(1 for h in HABITS_LIST if day_record.get(h, False))
        total_habits = len(HABITS_LIST)
        progress_rate = done_count / total_habits if total_habits > 0 else 0
        st.progress(progress_rate, text=f"達成度: {done_count} / {total_habits} 項目 ({int(progress_rate * 100)}%)")

        with st.form(key=f"form_habits_{sel_date_str}"):
            updated_day = dict(day_record)

            st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #38BDF8; margin-top: 12px; margin-bottom: 6px;'>🏃 運動・健康カテゴリ</div>", unsafe_allow_html=True)
            for habit in HABIT_CATEGORIES["運動・健康"]:
                val = day_record.get(habit, False)
                checked = st.checkbox(habit, value=bool(val), key=f"chk_{sel_date_str}_{habit}")
                updated_day[habit] = checked

                if habit == "血圧測定":
                    if checked:
                        bp_cols = st.columns([2, 2, 2])
                        with bp_cols[0]:
                            cur_sys = day_record.get("bpSys", "")
                            new_sys = st.number_input("最高血圧(上)", min_value=0, max_value=300, value=int(cur_sys) if cur_sys else 0, step=1, key=f"sys_{sel_date_str}", help="最高血圧（収縮期）")
                            if new_sys > 0:
                                updated_day["bpSys"] = int(new_sys)
                            else:
                                updated_day.pop("bpSys", None)
                        with bp_cols[1]:
                            cur_dia = day_record.get("bpDia", "")
                            new_dia = st.number_input("最低血圧(下)", min_value=0, max_value=200, value=int(cur_dia) if cur_dia else 0, step=1, key=f"dia_{sel_date_str}", help="最低血圧（拡張期）")
                            if new_dia > 0:
                                updated_day["bpDia"] = int(new_dia)
                            else:
                                updated_day.pop("bpDia", None)
                        with bp_cols[2]:
                            st.markdown("<div style='margin-top: 32px; font-size: 0.9rem; color: #94A3B8;'>mmHg</div>", unsafe_allow_html=True)
                    else:
                        updated_day.pop("bpSys", None)
                        updated_day.pop("bpDia", None)

            st.markdown("<div style='margin-top: 14px; font-size: 0.95rem; font-weight: 700; color: #F59E0B; margin-bottom: 6px;'>📝 記録・管理カテゴリ</div>", unsafe_allow_html=True)
            for habit in HABIT_CATEGORIES["記録・管理"]:
                val = day_record.get(habit, False)
                checked = st.checkbox(habit, value=bool(val), key=f"chk_{sel_date_str}_{habit}")
                updated_day[habit] = checked

            st.markdown("<div style='margin-top: 14px; padding-top: 10px; border-top: 1px dashed #334155;'></div>", unsafe_allow_html=True)
            golf_info = day_record.get("golf", {})
            if not isinstance(golf_info, dict):
                golf_info = {}
            golf_checked = st.checkbox("🏌️ ゴルフの打ちっぱなしに行った", value=bool(golf_info.get("practiced", False)), key=f"chk_golf_{sel_date_str}")
            if golf_checked:
                cur_balls = golf_info.get("balls", 0)
                new_balls = st.number_input("打った球数（球）", min_value=0, max_value=999, value=int(cur_balls) if cur_balls else 50, step=10, key=f"num_golf_balls_{sel_date_str}")
                updated_day["golf"] = {"practiced": True, "balls": int(new_balls)}
            else:
                updated_day["golf"] = {"practiced": False, "balls": 0}

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            cur_note = day_record.get("note", "")
            new_note = st.text_input("📝 備考 (未消化の理由など・最大20文字)", value=str(cur_note) if cur_note else "", max_chars=20, key=f"txt_note_{sel_date_str}", placeholder="例: 疲労のためスクワット休み")
            updated_day["note"] = new_note.strip()

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            save_habit_btn = st.form_submit_button("💾 実績を保存する", use_container_width=True)

            if save_habit_btn:
                tracker_data[sel_date_str] = updated_day
                tk_data["trackerData"] = tracker_data
                save_taskkanri_data(tk_data)
                st.success(f"{sel_date_str} の実績を保存しました！")
                st.rerun()

    # 右カラム：個別タスク（ToDo）& 習慣ストリーク
    with col_adhoc:
        sub_tab_adhoc, sub_tab_stats = st.tabs(["📋 個別タスク（ToDo）", "🔥 習慣ストリーク統計"])

        with sub_tab_adhoc:
            st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #F1F5F9; margin-bottom: 8px;'>📋 個別タスク（Adhoc Tasks）</div>", unsafe_allow_html=True)

            with st.expander("＋ 新規個別タスクを追加", expanded=False):
                with st.form(key="form_add_adhoc_task", clear_on_submit=True):
                    task_title = st.text_input("タスク名*", placeholder="例: 来週の発表に向けた資料作成")
                    add_col_s1, add_col_s2 = st.columns([1, 1])
                    with add_col_s1:
                        task_status = st.selectbox("ステータス", ["起票", "対応中", "完了"], index=0)
                    with add_col_s2:
                        task_due = st.date_input("期限日（任意）", value=None)
                    task_note = st.text_area("詳細・備考", placeholder="補足事項や進捗メモなど...", height=70)
                    submit_adhoc = st.form_submit_button("＋ タスクを登録", use_container_width=True)

                    if submit_adhoc and task_title.strip():
                        new_t = {
                            "id": str(int(time.time() * 1000)),
                            "createdDate": sel_date_str,
                            "title": task_title.strip(),
                            "status": task_status,
                            "dueDate": task_due.strftime("%Y-%m-%d") if task_due else "",
                            "note": task_note.strip(),
                            "createdAt": datetime.datetime.now().isoformat()
                        }
                        adhoc_tasks.append(new_t)
                        tk_data["adhocTasks"] = adhoc_tasks
                        save_taskkanri_data(tk_data)
                        st.success(f"タスク「{task_title.strip()}」を登録しました！")
                        st.rerun()

            active_adhoc = [t for t in adhoc_tasks if t.get("status") != "完了"]
            completed_adhoc = [t for t in adhoc_tasks if t.get("status") == "完了"]
            active_adhoc.sort(key=lambda x: (x.get("dueDate") == "", x.get("dueDate", "")))

            st.markdown(f"<div style='font-size: 0.95rem; font-weight: 700; color: #818CF8; margin-top: 10px; margin-bottom: 6px;'>進行中のタスク ({len(active_adhoc)}件)</div>", unsafe_allow_html=True)
            if not active_adhoc:
                st.caption("現在進行中のタスクはありません。")
            else:
                for t in active_adhoc:
                    t_id = t.get("id")
                    status_colors = {"起票": "#38BDF8", "対応中": "#F59E0B", "完了": "#10B981"}
                    due_badge = f"<span style='color: #F87171; font-size: 0.8rem; font-weight: 600; margin-left: 6px;'>📅 期限: {t.get('dueDate')}</span>" if t.get("dueDate") else ""
                    
                    st.markdown(
                        f"""
                        <div style="background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-weight: 600; color: #F8FAFC; font-size: 0.95rem;">{t.get('title')}</span>
                                <span style="background-color: {status_colors.get(t.get('status'), '#6366F1')}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">{t.get('status')}</span>
                            </div>
                            <div style="font-size: 0.8rem; color: #94A3B8;">起票: {t.get('createdDate', '')} {due_badge}</div>
                            {f"<div style='font-size: 0.85rem; color: #CBD5E1; margin-top: 4px; background: rgba(0,0,0,0.2); padding: 4px 8px; border-radius: 4px;'>{t.get('note')}</div>" if t.get('note') else ''}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    act_cols = st.columns([2, 1, 1])
                    with act_cols[0]:
                        cur_stat = t.get("status", "起票")
                        new_stat = st.selectbox(
                            "ステータス変更",
                            ["起票", "対応中", "完了"],
                            index=["起票", "対応中", "完了"].index(cur_stat) if cur_stat in ["起票", "対応中", "完了"] else 0,
                            key=f"sel_stat_{t_id}",
                            label_visibility="collapsed"
                        )
                        if new_stat != cur_stat:
                            t["status"] = new_stat
                            tk_data["adhocTasks"] = adhoc_tasks
                            save_taskkanri_data(tk_data)
                            st.rerun()
                    with act_cols[1]:
                        if st.button("完了", key=f"btn_complete_{t_id}", use_container_width=True):
                            t["status"] = "完了"
                            tk_data["adhocTasks"] = adhoc_tasks
                            save_taskkanri_data(tk_data)
                            st.rerun()
                    with act_cols[2]:
                        if st.button("削除", key=f"btn_del_adhoc_{t_id}", use_container_width=True):
                            tk_data["adhocTasks"] = [item for item in adhoc_tasks if item.get("id") != t_id]
                            save_taskkanri_data(tk_data)
                            st.rerun()

            if completed_adhoc:
                with st.expander(f"✅ 完了済みタスク ({len(completed_adhoc)}件)"):
                    for t in completed_adhoc:
                        st.markdown(
                            f"""
                            <div style="font-size: 0.9rem; color: #94A3B8; text-decoration: line-through; margin-bottom: 6px;">
                                • {t.get('title')} <span style="font-size: 0.75rem; text-decoration: none;">(起票: {t.get('createdDate')})</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        with sub_tab_stats:
            st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #F1F5F9; margin-bottom: 8px;'>🔥 習慣ストリーク & 達成統計</div>", unsafe_allow_html=True)
            
            today = datetime.date.today()
            start_of_week = today - datetime.timedelta(days=today.weekday())
            weekly_golf_count = 0
            weekly_golf_balls = 0
            for w in range(7):
                w_day_str = (start_of_week + datetime.timedelta(days=w)).strftime("%Y-%m-%d")
                w_rec = tracker_data.get(w_day_str, {})
                if isinstance(w_rec, dict) and w_rec.get("golf", {}).get("practiced", False):
                    weekly_golf_count += 1
                    weekly_golf_balls += w_rec.get("golf", {}).get("balls", 0)

            st.markdown(
                f"""
                <div class="dashboard-card" style="border-left: 4px solid #8B5CF6; margin-bottom: 14px; padding: 12px 16px;">
                    <div style="font-weight: 700; color: #C4B5FD; font-size: 0.95rem; margin-bottom: 6px;">🏌️ ゴルフ打ちっぱなし実績 (今週)</div>
                    <div style="display: flex; gap: 24px;">
                        <div><span style="font-size: 1.4rem; font-weight: 700; color: #F8FAFC;">{weekly_golf_count}</span> <span style="font-size: 0.85rem; color: #94A3B8;">回</span></div>
                        <div><span style="font-size: 1.4rem; font-weight: 700; color: #F8FAFC;">{weekly_golf_balls}</span> <span style="font-size: 0.85rem; color: #94A3B8;">球</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            for habit in HABITS_LIST:
                streak = calculate_habit_streak(tracker_data, habit)
                month_days, total_days = calculate_habit_stats(tracker_data, habit)
                streak_icon = "🔥" if streak >= 3 else "⚡"
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 8px 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 600; color: #F8FAFC; font-size: 0.9rem;">{habit}</span>
                            <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 2px;">
                                今月: <b style="color: #60A5FA;">{month_days}日</b> | 累計: <b style="color: #CBD5E1;">{total_days}日</b>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 1.1rem; font-weight: 700; color: {'#F59E0B' if streak >= 3 else '#CBD5E1'};">{streak_icon} {streak}</span>
                            <span style="font-size: 0.75rem; color: #94A3B8;">日連続</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
