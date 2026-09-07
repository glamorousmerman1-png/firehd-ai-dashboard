# ⚡ Fire HD常駐型「AIインテリジェンス・ダッシュボード」

Fire HDなどのタブレット横画面（1280×800 程度）で全画面表示し、PCの電源がオフでも単体で常駐できるパーソナルAIダッシュボードです。  
Streamlit Community Cloud にデプロイすることで、**完全無料**で24時間いつでもアクセスできる環境を構築できます。

---

## 🌟 主な機能

1. **📊 情報ブリーフィング（Intelligence Briefing）**
   - 「国内・グローバル市況」「AI & テックトレンド」「ビジネストピック」の3カテゴリを最新動向から要約
   - 3行要点要約、注目インサイト、市況感バッジ（ポジティブ/中立/警戒）を3カラム並列カードでひと目で把握
2. **💡 思考整理・ブレスト（Brainstorm & Wall-hit）**
   - アイデアや課題を入力すると、Geminiが即座に多角的視点から壁打ち
   - 「共感・アイデア拡張」「批判的検証（悪魔の代弁者）」「ネクストアクション3選」の3枚のカードで出力
3. **📝 タスク・アドバイザー（Daily Task Advisor）**
   - タスクの追加・完了チェック・個別削除ができる軽量ToDoリスト
   - 「AIアドバイス生成」ボタンで、最優先タスクの選定・時間配分や段取りのコツ・モチベーションメッセージを常時掲示

---

## 🛠️ 技術スタック
- **言語 / FW**: Python 3.10+ / [Streamlit](https://streamlit.io/)
- **AI SDK**: `google-genai`（Google公式 最新SDK）
- **AIモデル**: `gemini-1.5-flash`（無料枠対応、低遅延・高精度）
- **デザイン**: 1280×800 タブレット横置き最適化ダークテーマ（タッチフレンドリーな大型UI）

---

## 🚀 1. ローカルPCでのテスト実行手順

### 手順 A: 仮想環境の作成とライブラリ導入
```bash
# プロジェクトフォルダに移動
cd /path/to/firehd-ai-dashboard

# 仮想環境の作成 (任意ですが推奨)
python -m venv venv
# Windowsの場合
venv\Scripts\activate
# Mac/Linuxの場合
source venv/bin/activate

# 依存ライブラリのインストール
pip install -r requirements.txt
```

### 手順 B: アプリの起動
```bash
# 環境変数でAPIキーを渡す場合
set GEMINI_API_KEY="あなたのAPIキー"   # Windows PowerShellなら $env:GEMINI_API_KEY="あなたのAPIキー"

# アプリ起動
streamlit run app.py
```
ブラウザが自動的に開き、`http://localhost:8501` でダッシュボードが立ち上がります。  
※APIキーを環境変数に設定していない場合でも、画面左のサイドバーから直接APIキーを入力できます。

---

## 🌐 2. GitHubリポジトリへのアップロード手順

Streamlit Community Cloudにデプロイするため、コードをGitHubにプッシュします。

```bash
# git初期化
git init

# リポジトリに追加
git add .
git commit -m "feat: Fire HD AI intelligence dashboard initial commit"

# GitHubで新規リポジトリ（例: firehd-ai-dashboard）を作成後、紐付けてプッシュ
git branch -M main
git remote add origin https://github.com/<あなたのユーザー名>/firehd-ai-dashboard.git
git push -u origin main
```

---

## ☁️ 3. Streamlit Community Cloud への無料デプロイ手順

1. [Streamlit Community Cloud](https://share.streamlit.io/) にアクセスし、GitHubアカウントでサインインします。
2. 右上の **「New app」** ボタンをクリックします。
3. デプロイ設定を入力します：
   - **Repository**: `<あなたのユーザー名>/firehd-ai-dashboard`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. **「Advanced settings...」** をクリックし、**Secrets** にGemini APIキーを登録します：
   ```toml
   GEMINI_API_KEY = "AIzaSy..."
   ```
   > ※Google AI Studio ( https://aistudio.google.com/ ) で無料取得したAPIキーを入力してください。
5. **「Deploy!」** をクリックします。数分で公開URL（例: `https://<アプリ名>.streamlit.app`）が発行されます。

---

## 📱 4. Fire HD（Silkブラウザ）での常駐設定のコツ

Fire HD（7 / 8 / 10 等）をスマートディスプレイ化して快適に常駐運用するための設定テクニックです。

### ① 全画面・ツールバー非表示で開くURLの工夫
StreamlitのURLの末尾に `?embed=true` を付けると、上部のStreamlitヘッダーなどが最小化され、タブレット画面をより広く活用できます。
```text
https://<あなたのアプリ名>.streamlit.app/?embed=true
```

### ② ホーム画面にブックマーク（アプリ化）
1. Fire HD標準の **Silkブラウザ** で上記URLを開きます。
2. 画面右上のメニューアイコン（3点リーダー）をタップします。
3. **「ホーム画面に追加」** または **「ページを固定」** を選択します。
4. ホーム画面に専用アイコンが生成され、次回から1タップですぐにダッシュボードを全画面風に起動できます。

### ③ 常駐時の画面スリープ防止（常時オンにする）
デスク脇で時計やダッシュボードとして常時点灯させる場合の設定です：
- **設定アプリ** > **端末オプション** > **シリアル番号** を7回タップして「開発者向けオプション」を有効化します。
- **設定アプリ** > **端末オプション** > **開発者向けオプション** を開き、**「スリープモードにしない（充電中は画面をスリープ状態にしない）」** をONにします。
- 充電スタンドやUSBケーブルを接続しておけば、PCの電源がオフでもFire HD単体で24時間ダッシュボードが表示され続けます。

---

## 📁 ディレクトリ構成

```
firehd-ai-dashboard/
├── .streamlit/
│   └── config.toml       # ダークテーマとUIスタイル設定
├── app.py                # メインアプリケーション
├── requirements.txt      # 依存ライブラリ一覧
└── README.md             # 本手順書
```
