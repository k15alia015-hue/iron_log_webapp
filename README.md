# IRON LOG — 筋トレ記録Webアプリ

日々のトレーニング（部位・種目・重量・回数）をカレンダーで記録・振り返りできる、個人用の筋トレ記録Webアプリです。Flask + MySQL で動作し、フロントエンド・バックエンドともに **Model / View / Presenter (MVP)** パターンで構成しています。

---

## 主な機能

- 📅 **カレンダー**：日付ごとにトレーニングした部位を色分け表示
- 🏋️ **記録**：部位 → 種目を選んで、重量 × 回数のセットを記録
- 📈 **自己ベスト**：種目ごとに MAX 重量・MAX 回数を自動表示
- 📝 **メモ**：種目ごとにメモを保存（前回の内容が残る）
- ⏱ **レストタイマー**：種目ごとにレスト時間を設定し、カウントダウン＆終了通知
- ➕ **種目の追加**：初期種目に加え、ユーザーが独自の種目を追加できる
- ✏️ **種目の編集・削除**：自分で追加した種目は名前変更・削除が可能（削除は確認ダイアログ付き）
- 🔒 **Basic認証**：アプリ全体をパスワードで保護

---

## 技術スタック

| 区分 | 使用技術 |
|------|----------|
| バックエンド | Python 3.12 / Flask / Flask-SQLAlchemy / Flask-Migrate (Alembic) |
| データベース | MySQL 8 |
| フロントエンド | 素の HTML / CSS / JavaScript（フレームワークなし） |
| テスト | pytest（Flask test client + インメモリSQLite） |

---

## ディレクトリ構成

```
iron_log_webapp/
├── backend/                     # バックエンド（Flask）
│   ├── app.py                   # アプリケーションファクトリ（起動の入口）
│   ├── config.py                # 設定（Config / Development / Production / Test）
│   ├── extensions.py            # SQLAlchemy・Migrate のインスタンス
│   ├── models.py                # Model：テーブル定義とクエリ
│   ├── presenters.py            # Presenter：入力検証・業務ロジック
│   ├── views.py                 # View：HTTPルーティング
│   ├── auth.py                  # Basic認証
│   ├── errors.py                # エラー処理の一元化（ApiError）
│   ├── cli.py                   # Flask CLIコマンド（init-db / migrate-json）
│   ├── body_parts.py            # 部位ごとの種目マスタデータ
│   ├── migrations/              # Flask-Migrate（Alembic）のマイグレーション
│   └── tests/                   # pytest テスト
├── frontend/                    # フロントエンド
│   ├── static/                  # app.js / model.js / view.js / presenter.js / style.css
│   └── templates/               # index.html
├── requirements.txt
├── start.bat                    # Windows用の起動スクリプト
└── .env.example                 # 環境変数のテンプレート
```

### アーキテクチャ（MVP）

- **バックエンド**：`models.py`（DB操作）→ `presenters.py`（検証・業務ロジック）→ `views.py`（ルーティング）と責務を分離。
- **フロントエンド**：`model.js`（API通信・データ保持）→ `presenter.js`（画面遷移・操作ロジック）→ `view.js`（DOM描画）で同じ考え方に揃えています。

---

## セットアップ

### 1. 前提

- Python 3.12 以上
- MySQL 8 以上

### 2. データベースの準備

MySQL にログインし、DB とユーザーを作成します。

```sql
CREATE DATABASE iron_log CHARACTER SET utf8mb4;
CREATE USER 'iron_log_user'@'localhost' IDENTIFIED BY '任意のパスワード';
GRANT ALL PRIVILEGES ON iron_log.* TO 'iron_log_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、値を自分の環境に合わせて編集します。
（`.env` は Git 管理対象外です）

```bash
cp .env.example .env
```

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_NAME=iron_log
DB_USER=iron_log_user
DB_PASSWORD=あなたのDBパスワード

IRON_LOG_USERNAME=ログイン用のユーザー名
IRON_LOG_PASSWORD=ログイン用のパスワード
```

### 5. テーブルの作成（マイグレーション）

```bash
cd backend
flask db upgrade
```

### 6. 起動

```bash
cd backend
python app.py
```

ブラウザで <http://127.0.0.1:5000> を開き、`.env` に設定したユーザー名・パスワードでログインします。

> Windows では、リポジトリ直下の `start.bat` をダブルクリックしても起動できます。

---

## 使い方

ログイン後、以下の流れでトレーニングを記録します。画面は「カレンダー → 履歴 → 部位 → 種目」の順に進みます。

### 1. 日付を選ぶ

- トップのカレンダーで記録したい日付をクリックします（「今日を選ぶ」ボタンで当日へ）。
- 各日付には、その日に鍛えた部位が色分けのドットで表示されます。凡例（下部）で部位と色を確認できます。
- 前月・翌月は `‹` `›` で移動します。

### 2. 種目を追加する

1. 日付を選ぶとその日の**履歴画面**が開きます。「**＋ 種目を追加**」を押します。
2. **部位**（胸・背中・脚・肩・腕・腹）を選びます。
3. 種目の一覧から記録したい**種目**を選ぶと、その日の履歴に種目カードが追加されます。

### 3. セット（重量 × 回数）を記録する

- 種目カードの「**セットの追加**」を押すと入力欄が開きます。**重量(kg)** と **回数** を入力し、右のチェックを入れると保存されます。
- 保存したセットは「◯kg × ◯回」で一覧表示され、各行のチェックを外すとそのセットを削除できます。
- カード右上には、その種目の **MAX重量 / MAX回数**（自己ベスト）が自動表示されます。
- 「**セットの編集 / 完了**」で、削除・追加ボタンの表示を切り替えられます。

### 4. メモを残す

- 種目カードのメモ欄に入力し、欄の外をクリック（フォーカスを外す）すると保存されます。前回の内容が残るので、フォームの設定などを引き継げます。

### 5. レストタイマーを使う

- 種目名の右（MAX表示の左）にある「**タイマー**」の `⏱` ラベルを押すと、設定ポップアップが開きます。
- **分（1〜5）** と **秒（0・10・20・30・40・50）** をボタンで選び、「**設定**」を押します（例：1分30秒）。タイマーを使わない場合は「**不使用**」を選びます。
- 設定すると `▶` ボタンが表示されます。押すとカウントダウンが始まり、**0 になると音（ビープ）で通知**します。`■` で途中停止できます。
- レスト時間は**種目ごとに保存**され、リロードや別端末でも保持されます（カウントダウンの進行状況はその端末の表示中のみ）。

### 6. 種目を編集・削除する（自分で追加した種目のみ）

1. 部位から種目を選ぶ画面の一番下、「**✎ 種目の編集**」を押します。
2. 自分で追加した種目には「**名前の変更**」「**種目の削除**」が表示されます（初期からある種目は変更できません）。
3. 「名前の変更」で種目名を変更できます。過去の記録・メモ・タイマー設定も新しい名前に引き継がれます。
4. 「種目の削除」を押すと確認ダイアログが出ます。「はい」で、その種目と紐づく記録・メモ・タイマーがすべて削除されます。

### 7. すべての記録を見る

- 画面右下の「**全記録**」ボタンで、種目ごとの全セット履歴を一覧表示できます。

---

## Flask CLI コマンド

`backend/` ディレクトリで実行します。

| コマンド | 内容 |
|----------|------|
| `flask db upgrade` | マイグレーションを適用してテーブルを最新化 |
| `flask db migrate -m "説明"` | モデル変更からマイグレーションを自動生成 |
| `flask init-db` | 全テーブルを作成（マイグレーション未使用時のフォールバック） |
| `flask migrate-json` | 旧JSONファイル（`training_data.json` 等）からデータを移行 |

---

## テスト

インメモリSQLiteを使うため、本番のMySQLを汚さずに実行できます。

```bash
cd backend
pytest
```

---

## API 一覧

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/body-parts` | 部位と種目の一覧 |
| GET | `/api/custom-exercises` | ユーザーが追加した種目の一覧 |
| POST | `/api/exercises` | 種目を追加 `{ part, exercise }` |
| PATCH | `/api/exercises/<part>/<exercise>` | 種目名を変更 `{ newName }` |
| DELETE | `/api/exercises/<part>/<exercise>` | 種目を削除（紐づく記録も削除） |
| GET | `/api/sets` | 記録済みの全セット |
| POST | `/api/sets` | セットを追加 `{ exercise, weight, reps, date? }` |
| DELETE | `/api/sets/<exercise>/<index>` | セットを1件削除 |
| GET | `/api/day-exercises` | 日付ごとに追加した種目 |
| POST | `/api/day-exercises` | その日に種目を追加 `{ date, part, exercise }` |
| DELETE | `/api/day-exercises/<date>/<part>/<exercise>` | その日の種目を削除 |
| GET | `/api/exercise-notes` | 種目ごとのメモ一覧 |
| POST | `/api/exercise-notes` | 種目のメモを保存 `{ exercise, note }` |
| GET | `/api/exercise-timers` | 種目ごとのレストタイマー設定 |
| POST | `/api/exercise-timers` | タイマーを保存 `{ exercise, restSeconds }`（0で不使用） |

---

## 補足

- 認証情報・DB接続情報は `.env` にのみ保存し、リポジトリには含めていません。
- データは MySQL に保存され、サーバーを再起動しても記録は保持されます。
- インターネットに公開する場合は、`.env` の認証情報を必ず自分だけが知る値に設定し、開発用サーバー（`app.run`）ではなく本番用 WSGI サーバーを利用してください。
