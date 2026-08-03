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


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/body-parts", methods=["GET"])
def body_parts():
    data, status = presenters.get_body_parts()
    return jsonify(data), status


@bp.route("/api/sets", methods=["GET"])
def list_sets():
    data, status = presenters.get_sets()
    return jsonify(data), status


@bp.route("/api/sets", methods=["POST"])
def create_set():
    payload = request.get_json(silent=True) or {}
    data, status = presenters.add_set(payload)
    return jsonify(data), status


@bp.route("/api/sets/<exercise>/<int:index>", methods=["DELETE"])
def remove_set(exercise, index):
    data, status = presenters.delete_set(exercise, index)
    return jsonify(data), status


@bp.route("/api/day-exercises", methods=["GET"])
def list_day_exercises():
    data, status = presenters.get_day_exercises()
    return jsonify(data), status


@bp.route("/api/day-exercises", methods=["POST"])
def create_day_exercise():
    payload = request.get_json(silent=True) or {}
    data, status = presenters.add_day_exercise(payload)
    return jsonify(data), status


@bp.route("/api/day-exercises/<day>/<part>/<exercise>", methods=["DELETE"])
def remove_day_exercise(day, part, exercise):
    data, status = presenters.delete_day_exercise(day, part, exercise)
    return jsonify(data), status


@bp.route("/api/exercise-notes", methods=["GET"])
def list_exercise_notes():
    data, status = presenters.get_exercise_notes()
    return jsonify(data), status


@bp.route("/api/exercise-notes", methods=["POST"])
def create_exercise_note():
    payload = request.get_json(silent=True) or {}
    data, status = presenters.save_exercise_note(payload)
    return jsonify(data), status
