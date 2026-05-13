# Quick Memo App

すぐにメモを残し、リマインダー日時・カテゴリ・優先度・ステータスで整理できるDjangoアプリケーションです。

## 機能

- ✅ メモの作成・編集・削除
- ⏰ リマインダー日時の登録
- ✅ メモの完了管理
- 📁 7つのカテゴリで分類
  - やること
  - 買うもの
  - 調べる
  - 連絡
  - アイデア
  - 不安
  - その他
- ⭐ 優先度管理（高・中・低・未設定）
- 📊 ステータス管理
  - 未整理
  - 今日やる
  - 今週やる
  - いつか
  - 完了
  - 捨てる

## セットアップ

### 必要な環境
- Python 3.8以上
- Django 4.0以上

### インストール手順

1. **リポジトリをクローン**
```bash
git clone <repository-url>
cd quick_memo_app
```

2. **仮想環境を作成・有効化**
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows
```

3. **依存パッケージをインストール**
```bash
pip install -r requirements.txt
```

4. **データベースをマイグレーション**
```bash
python manage.py migrate
```

5. **開発サーバーを起動**
```bash
python manage.py runserver
```

ブラウザで `http://localhost:8000` にアクセスしてください。

標準ではSQLiteを使用します。PostgreSQLを使う場合は、以下の環境変数を設定してください。

```bash
export DB_ENGINE=postgres
export DB_NAME=quick_memo_app_development
export DB_USER=quick_memo_user
export DB_PASSWORD=password
export DB_HOST=localhost
export DB_PORT=5432
```

## テスト

```bash
python manage.py test
```

## プロジェクト構造

```
quick_memo_app/
├── manage.py              # Django管理ファイル
├── README.md             # このファイル
├── .gitignore            # Git追跡除外設定
├── requirements.txt      # 依存パッケージ一覧
├── config/               # プロジェクト設定
│   ├── settings.py       # Django設定
│   ├── urls.py          # URL設定
│   ├── asgi.py
│   └── wsgi.py
└── memos/               # メモアプリケーション
    ├── models.py        # データモデル
    ├── forms.py         # 入力フォーム
    ├── urls.py          # メモ機能のURL設定
    ├── views.py         # ビュー
    ├── templates/       # HTMLテンプレート
    ├── static/          # CSS
    ├── admin.py         # Django Admin設定
    └── migrations/      # マイグレーションファイル
```

## 今後のiPhoneアプリ化メモ

- まずはDjango側にJSON APIを追加する
- iPhoneアプリはSwiftUIで、メモ一覧・作成・完了・リマインダー通知を実装する
- ユーザー認証を追加して、端末間同期できるようにする

## 使用技術

- Django
- Python

## ライセンス

MIT License
