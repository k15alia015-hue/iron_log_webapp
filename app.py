
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筋トレ記録アプリ（Web版）

Flaskで以下のAPIを提供する:
  GET    /api/body-parts        部位と種目の一覧を返す
  GET    /api/sets              記録済みの全セットを返す
  POST   /api/sets              セットを追加する { exercise, weight, reps, date(任意) }
  DELETE /api/sets/<exercise>/<index>  指定した種目のセットを1件削除する
  GET    /api/day-exercises      日付ごとに「追加した種目」一覧を返す
  POST   /api/day-exercises      その日・その部位に種目を追加する { date, part, exercise }
  DELETE /api/day-exercises/<date>/<part>/<exercise>
                                  その日の種目を削除する（紐づくセットも削除）
  GET    /api/exercise-notes    種目ごとのメモ一覧を返す
  POST   /api/exercise-notes    種目のメモを保存する { exercise, note }

データはMySQLデータベースに保存される（接続情報は.envで管理）。

パスワード保護:
  アプリ全体にBasic認証がかかっている。ユーザー名・パスワードは環境変数
  IRON_LOG_USERNAME / IRON_LOG_PASSWORD で上書きできる（未設定の場合は下記の初期値を使用）。
  インターネットに公開する前に、必ずこの初期値を変更すること。
"""

import os
from datetime import date
from urllib.parse import quote_plus

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, Response
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "iron_log")
DB_USER = os.environ.get("DB_USER", "iron_log_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class TrainingSet(db.Model):
    __tablename__ = "training_sets"

    id = db.Column(db.Integer, primary_key=True)
    exercise = db.Column(db.String(255), nullable=False, index=True)
    weight = db.Column(db.Float, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    set_date = db.Column(db.Date, nullable=False)

    def to_dict(self):
        return {"weight": self.weight, "reps": self.reps, "date": self.set_date.isoformat()}


class DayExercise(db.Model):
    __tablename__ = "day_exercises"
    __table_args__ = (db.UniqueConstraint("day", "part", "exercise", name="uq_day_part_exercise"),)

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Date, nullable=False, index=True)
    part = db.Column(db.String(50), nullable=False)
    exercise = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {"part": self.part, "exercise": self.exercise}


class ExerciseNote(db.Model):
    __tablename__ = "exercise_notes"

    exercise = db.Column(db.String(255), primary_key=True)
    note = db.Column(db.Text, nullable=False)


# ==== パスワード保護の設定 ====
# ユーザー名・パスワードは必ず.env(IRON_LOG_USERNAME / IRON_LOG_PASSWORD)で設定すること。
AUTH_USERNAME = os.environ.get("IRON_LOG_USERNAME", "change_me")
AUTH_PASSWORD = os.environ.get("IRON_LOG_PASSWORD", "change_me")


def check_auth(username, password):
    """入力されたユーザー名・パスワードが正しいか確認する。"""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


def authenticate():
    """認証を促すレスポンスを返す。"""
    return Response(
        "この画面を見るにはログインが必要です。",
        401,
        {"WWW-Authenticate": 'Basic realm="IRON LOG"'},
    )


@app.before_request
def require_login():
    """静的ファイルを含む、アプリ全体にBasic認証をかける。"""
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

# 部位ごとの種目一覧（初期セット。増やしたい場合はここに追記する）
BODY_PARTS = {
    "胸": [
        "ベンチプレス",
        "インクラインベンチプレス",
        "ダンベルフライ",
        "スミスマシンベンチプレス",
        "スミスマシンインクラインベンチプレス",
        "ダンベルベンチプレス",
        "インクラインダンベルベンチプレス",
        "インクラインダンベルフライ",
        "ディップス",
        "シーテッドディップスマシン",
        "チェストプレスマシン",
        "インクラインチェストプレスマシン",
        "ペックフライ",
        "ケーブルクロスオーバー上部",
        "ケーブルクロスオーバー中部",
        "ケーブルクロスオーバー下部",
        "デクラインチェストプレスマシン",
    ],
    "背中": [
        "デッドリフト",
        "懸垂",
        "ラットプルダウン",
        "シーテッドケーブルロウ",
        "バーベルベントオーバーロウ",
        "ワンハンドダンベルロウ",
        "ローローマシン",
        "Tバーロウマシン",
        "パラレルグリップラットプルダウン",
        "ストレートアームプルダウン",
        "ダンベルシュラッグ",
        "バーベルシュラッグ",
        "ラットプルマシン",
    ],
    "脚": [
        "バーベルスクワット",
        "レッグプレス",
        "レッグカール",
        "スミスマシンスクワット",
        "フロントスクワット",
        "ハックスクワット",
        "レッグエクステンション",
        "バーベルブルガリアンスクワット",
        "ダンベルブルガリアンスクワット",
        "バーベルカーフレイズ",
        "ヒップスラスト",
        "ヒップアブダクション",
        "ヒップアダクション",
        "ダンベルルーマニアンデッドリフト",
    ],
    "肩": [
        "ダンベルショルダープレス",
        "サイドレイズ",
        "スミスマシンオーバーヘッドプレス",
        "アーノルドプレス",
        "ショルダープレスマシン",
        "フロントレイズ",
        "リアレイズ",
        "ケーブルフェイスプル",
        "ケーブルリバースフライ",
        "バーベルアップライトロウ",
        "EZバーアップライトロウ",
        "リアデルトフライマシン",
        "サイドレイズマシン",
        "ケーブルフロントレイズ",
        "ケーブルサイドレイズ",
        "ケーブルリアレイズ",
        "シーテッドリアレイズ",
        "シーテッドサイドレイズ",
        "ケーブルアップライトロウ",
        "バーベルミリタリープレス",
        "スミスマシンバックプレス",
    ],
    "腕": [
        "バーベルカール",
        "EZバーカル",
        "EZバープリチャーカール",
        "ダンベルプリチャーカール",
        "ダンベルカール",
        "ダンベルワンハンドカール",
        "ダンベルハンマーカール",
        "インクラインダンベルカール",
        "インクラインハンマーカール",
        "ケーブルカール",
        "ケーブルハンマーカール",
        "アームカールマシン",
        "EZバーリバースカール",
        "ダンベルリバースカール",
        "ナローベンチプレス",
        "スミスマシンナローベンチプレス",
        "ダンベルフレンチプレス",
        "シーテッドダンベルフレンチプレス",
        "シーテッドトライセプスエクステンション",
        "スカルクラッシャー",
        "ケーブルトライセプスエクステンション",
        "ケーブルプレスダウン",
        "ケーブルオーバーヘッドエクステンション",
        "ディップス",
        "ディップスマシン",
        "ベンチディップス",
        "ダンベルキックバック",
        "ダンベルリストカール",
        "EZバーリストカール",
        "ダンベルリバースリストカール",
    ],
    "腹": ["クランチ", "レッグレイズ", "デクラインクランチ", "アブローラー", "アブドミナルクランチ", "ドラゴンフラッグ"],
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/body-parts", methods=["GET"])
def get_body_parts():
    return jsonify(BODY_PARTS)


@app.route("/api/sets", methods=["GET"])
def get_sets():
    data = {}
    for row in TrainingSet.query.order_by(TrainingSet.id).all():
        data.setdefault(row.exercise, []).append(row.to_dict())
    return jsonify(data)


@app.route("/api/sets", methods=["POST"])
def add_set():
    payload = request.get_json(silent=True) or {}
    exercise = payload.get("exercise")
    weight = payload.get("weight")
    reps = payload.get("reps")
    set_date = payload.get("date")

    if not exercise or weight is None or reps is None:
        return jsonify({"error": "exercise, weight, reps は必須です"}), 400

    try:
        weight = float(weight)
        reps = int(reps)
        if reps <= 0 or weight < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "weightは数値、repsは1以上の整数で指定してください"}), 400

    if set_date:
        try:
            set_date = date.fromisoformat(set_date)
        except ValueError:
            return jsonify({"error": "dateはYYYY-MM-DD形式で指定してください"}), 400
    else:
        set_date = date.today()

    new_set = TrainingSet(exercise=exercise, weight=weight, reps=reps, set_date=set_date)
    db.session.add(new_set)
    db.session.commit()

    sets = TrainingSet.query.filter_by(exercise=exercise).order_by(TrainingSet.id).all()
    return jsonify({"exercise": exercise, "sets": [s.to_dict() for s in sets]}), 201


@app.route("/api/sets/<exercise>/<int:index>", methods=["DELETE"])
def delete_set(exercise, index):
    sets = TrainingSet.query.filter_by(exercise=exercise).order_by(TrainingSet.id).all()

    if not (0 <= index < len(sets)):
        return jsonify({"error": "指定されたセットが見つかりません"}), 404

    removed = sets.pop(index)
    removed_dict = removed.to_dict()
    db.session.delete(removed)
    db.session.commit()

    return jsonify({"removed": removed_dict, "sets": [s.to_dict() for s in sets]})


@app.route("/api/day-exercises", methods=["GET"])
def get_day_exercises():
    data = {}
    for row in DayExercise.query.order_by(DayExercise.id).all():
        data.setdefault(row.day.isoformat(), []).append(row.to_dict())
    return jsonify(data)


@app.route("/api/day-exercises", methods=["POST"])
def add_day_exercise():
    payload = request.get_json(silent=True) or {}
    day = payload.get("date")
    part = payload.get("part")
    exercise = payload.get("exercise")

    if not day or not part or not exercise:
        return jsonify({"error": "date, part, exercise は必須です"}), 400

    try:
        day_value = date.fromisoformat(day)
    except ValueError:
        return jsonify({"error": "dateはYYYY-MM-DD形式で指定してください"}), 400

    if part not in BODY_PARTS or exercise not in BODY_PARTS[part]:
        return jsonify({"error": "指定された部位・種目の組み合わせが正しくありません"}), 400

    already = DayExercise.query.filter_by(day=day_value, part=part, exercise=exercise).first()
    if not already:
        db.session.add(DayExercise(day=day_value, part=part, exercise=exercise))
        db.session.commit()

    day_list = DayExercise.query.filter_by(day=day_value).order_by(DayExercise.id).all()
    return jsonify({"date": day, "list": [e.to_dict() for e in day_list]}), 201


@app.route("/api/day-exercises/<day>/<part>/<exercise>", methods=["DELETE"])
def delete_day_exercise(day, part, exercise):
    try:
        day_value = date.fromisoformat(day)
    except ValueError:
        return jsonify({"error": "dateはYYYY-MM-DD形式で指定してください"}), 400

    DayExercise.query.filter_by(day=day_value, part=part, exercise=exercise).delete()

    # その日に記録されたセットも合わせて削除し、履歴とセット記録の整合性を保つ
    TrainingSet.query.filter_by(exercise=exercise, set_date=day_value).delete()
    db.session.commit()

    day_list = DayExercise.query.filter_by(day=day_value).order_by(DayExercise.id).all()
    remaining_sets = TrainingSet.query.filter_by(exercise=exercise).order_by(TrainingSet.id).all()

    return jsonify({
        "date": day,
        "list": [e.to_dict() for e in day_list],
        "sets": [s.to_dict() for s in remaining_sets],
    })


@app.route("/api/exercise-notes", methods=["GET"])
def get_exercise_notes():
    notes = {row.exercise: row.note for row in ExerciseNote.query.all()}
    return jsonify(notes)


@app.route("/api/exercise-notes", methods=["POST"])
def save_exercise_note():
    payload = request.get_json(silent=True) or {}
    exercise = payload.get("exercise")
    note = payload.get("note", "")

    if not exercise:
        return jsonify({"error": "exercise は必須です"}), 400

    existing = ExerciseNote.query.filter_by(exercise=exercise).first()
    if note:
        if existing:
            existing.note = note
        else:
            db.session.add(ExerciseNote(exercise=exercise, note=note))
    elif existing:
        db.session.delete(existing)
    db.session.commit()

    saved = ExerciseNote.query.filter_by(exercise=exercise).first()
    return jsonify({"exercise": exercise, "note": saved.note if saved else ""})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="127.0.0.1", port=5000)
