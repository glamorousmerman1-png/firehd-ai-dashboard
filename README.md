# ⚡ Fire HD常駐型「AIインテリジェンス・ダッシュボード」

Fire HDなどのタブレット横画面（1280×800 程度）で全画面表示し、PCの電源がオフでも単体で常駐できるパーソナルAIダッシュボードです。  
Streamlit Community Cloud にデプロイされており、**完全無料**で24時間いつでもアクセスできます。

---

## 🌐 アプリURL

- **通常アクセス用**:  
  👉 **[https://ngrwi3j3aajjq2qjkugxsh.streamlit.app/](https://ngrwi3j3aajjq2qjkugxsh.streamlit.app/)**
- **Fire HD / タブレット常駐用（ヘッダー最小化・全画面モード）**:  
  👉 **[https://ngrwi3j3aajjq2qjkugxsh.streamlit.app/?embed=true](https://ngrwi3j3aajjq2qjkugxsh.streamlit.app/?embed=true)**

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
4. **🔐 パスワード（合言葉）ロック機能**
   - 不特定多数からのアクセスを防ぎ、自分専用として安全に運用するためのロック画面を搭載
   - クラウドのSecretsにパスワードを設定することで、合言葉を入力したユーザーのみがアクセス可能

---

## 🛠️ 技術スタック
- **言語 / FW**: Python 3.10+ / [Streamlit](https://streamlit.io/)
- **AI SDK**: `google-genai`（Google公式 最新SDK）
- **AIモデル**: `gemini-2.5-flash`（無料枠対応、超低遅延・高精度）
- **デザイン**: 1280×800 タブレット横置き最適化ダークテーマ（タッチフレンドリーな大型UI）
- **ホスティング**: Streamlit Community Cloud（24時間無料稼働）

---

## 📱 Fire HD（Silkブラウザ）での常駐設定のコツ

Fire HD（7 / 8 / 10 等）をスマートディスプレイ化して快適に常駐運用するための設定テクニックです。

### ① 全画面・ツールバー非表示で開く
上記記載の常駐用URL（末尾に `?embed=true` を付けたURL）で開くと、上部のStreamlitヘッダーなどが最小化され、タブレット画面いっぱいに表示されます。
```text
https://ngrwi3j3aajjq2qjkugxsh.streamlit.app/?embed=true
```

### ② ホーム画面にブックマーク（アプリ化）
1. Fire HD標準の **Silkブラウザ** で上記URLを開きます。
2. 画面右上のメニューアイコン（3点リーダー）をタップします。
3. **「ホーム画面に追加」**（または「ページを固定」）を選択します。
4. ホーム画面に専用アイコンが生成され、次回から1タップですぐにダッシュボードを全画面風に起動できます。

### ③ 常駐時の画面スリープ防止（常時オンにする）
デスク脇で時計やダッシュボードとして常時点灯させる場合の設定です：
- **設定アプリ** > **端末オプション** > **シリアル番号** を7回タップして「開発者向けオプション」を有効化します。
- **設定アプリ** > **端末オプション** > **開発者向けオプション** を開き、**「スリープモードにしない（充電中は画面をスリープ状態にしない）」** をONにします。
- 充電スタンドやUSBケーブルを接続しておけば、PCの電源がオフでもFire HD単体で24時間ダッシュボードが表示され続けます。

---

## 🚀 ローカルPCでのテスト実行手順

```bash
# プロジェクトフォルダに移動
cd "g:\マイドライブ\Antiglavity\.agent\firehd-ai-dashboard"

# 仮想環境の作成 (任意)
python -m venv venv
venv\Scripts\activate

# 依存ライブラリのインストール
pip install -r requirements.txt

# アプリ起動
python -m streamlit run app.py
```

ブラウザで `http://localhost:8501` を開きます。

---

## 📁 ディレクトリ構成

```
firehd-ai-dashboard/
├── .streamlit/
│   ├── config.toml       # ダークテーマとUIスタイル設定
│   └── secrets.toml      # (非公開・Git除外) ローカル用APIキー設定
├── .gitignore            # secrets.toml等をGitから除外する設定
├── app.py                # メインアプリケーション（パスワード認証付き）
├── requirements.txt      # 依存ライブラリ一覧
└── README.md             # 本手順書
```
