#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
VIEW
===================================================================
役割:
  - HTTPリクエストの受け取り、Presenterへの引き渡し
  - Presenterが返したデータをHTTPレスポンス（JSON / HTML）として返す

ここには入力値の検証や業務ルール、DB操作を一切書かない。
「どのURLにアクセスされたら、どのPresenter関数を呼ぶか」だけを担当する。

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
===================================================================
"""

from flask import Blueprint, jsonify, render_template, request

import presenters

bp = Blueprint("views", __name__)


def _respond(result):
    """Presenter関数の戻り値 (data, status) をJSONレスポンスに変換する共通処理。"""
    data, status = result
    return jsonify(data), status


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/body-parts", methods=["GET"])
def body_parts():
    return _respond(presenters.get_body_parts())


@bp.route("/api/sets", methods=["GET"])
def list_sets():
    return _respond(presenters.get_sets())


@bp.route("/api/sets", methods=["POST"])
def create_set():
    payload = request.get_json(silent=True) or {}
    return _respond(presenters.add_set(payload))


@bp.route("/api/sets/<exercise>/<int:index>", methods=["DELETE"])
def remove_set(exercise, index):
    return _respond(presenters.delete_set(exercise, index))


@bp.route("/api/day-exercises", methods=["GET"])
def list_day_exercises():
    return _respond(presenters.get_day_exercises())


@bp.route("/api/day-exercises", methods=["POST"])
def create_day_exercise():
    payload = request.get_json(silent=True) or {}
    return _respond(presenters.add_day_exercise(payload))


@bp.route("/api/day-exercises/<day>/<part>/<exercise>", methods=["DELETE"])
def remove_day_exercise(day, part, exercise):
    return _respond(presenters.delete_day_exercise(day, part, exercise))


@bp.route("/api/exercise-notes", methods=["GET"])
def list_exercise_notes():
    return _respond(presenters.get_exercise_notes())


@bp.route("/api/exercise-notes", methods=["POST"])
def create_exercise_note():
    payload = request.get_json(silent=True) or {}
    return _respond(presenters.save_exercise_note(payload))
