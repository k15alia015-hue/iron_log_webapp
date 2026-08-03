#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
PRESENTER
===================================================================
役割:
  - Model（DB）とView（APIレスポンス）の橋渡し
  - 入力値の検証、業務ルールの適用、トランザクション（コミット）の制御

Modelはデータの保存方法だけを知り、Viewはリクエスト/レスポンスの
形式だけを知る。その間を取り持つのがPresenterの役割。

各関数は (レスポンスに入れるdict, HTTPステータスコード) のタプルを返す。
Flaskのrequest/responseオブジェクトには一切触れず、Viewから渡された
素のデータ（dict・文字列など）だけを扱う。
===================================================================
"""

from datetime import date

from config import BODY_PARTS
from extensions import db
from models import DayExercise, ExerciseNote, TrainingSet


def get_body_parts():
    return BODY_PARTS, 200


# ---------------- セット ----------------

def get_sets():
    return TrainingSet.all_grouped_by_exercise(), 200


def add_set(payload):
    exercise = payload.get("exercise")
    weight = payload.get("weight")
    reps = payload.get("reps")
    set_date = payload.get("date")

    if not exercise or weight is None or reps is None:
        return {"error": "exercise, weight, reps は必須です"}, 400

    try:
        weight = float(weight)
        reps = int(reps)
        if reps <= 0 or weight < 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"error": "weightは数値、repsは1以上の整数で指定してください"}, 400

    if set_date:
        try:
            set_date = date.fromisoformat(set_date)
        except ValueError:
            return {"error": "dateはYYYY-MM-DD形式で指定してください"}, 400
    else:
        set_date = date.today()

    TrainingSet.create(exercise, weight, reps, set_date)
    db.session.commit()

    sets = TrainingSet.for_exercise(exercise)
    return {"exercise": exercise, "sets": [s.to_dict() for s in sets]}, 201


def delete_set(exercise, index):
    sets = TrainingSet.for_exercise(exercise)

    if not (0 <= index < len(sets)):
        return {"error": "指定されたセットが見つかりません"}, 404

    removed = sets.pop(index)
    removed_dict = removed.to_dict()
    db.session.delete(removed)
    db.session.commit()

    return {"removed": removed_dict, "sets": [s.to_dict() for s in sets]}, 200


# ---------------- 日付ごとの種目 ----------------

def get_day_exercises():
    return DayExercise.all_grouped_by_day(), 200


def add_day_exercise(payload):
    day = payload.get("date")
    part = payload.get("part")
    exercise = payload.get("exercise")

    if not day or not part or not exercise:
        return {"error": "date, part, exercise は必須です"}, 400

    try:
        day_value = date.fromisoformat(day)
    except ValueError:
        return {"error": "dateはYYYY-MM-DD形式で指定してください"}, 400

    if part not in BODY_PARTS or exercise not in BODY_PARTS[part]:
        return {"error": "指定された部位・種目の組み合わせが正しくありません"}, 400

    if not DayExercise.exists(day_value, part, exercise):
        DayExercise.create(day_value, part, exercise)
        db.session.commit()

    day_list = DayExercise.for_day(day_value)
    return {"date": day, "list": [e.to_dict() for e in day_list]}, 201


def delete_day_exercise(day, part, exercise):
    try:
        day_value = date.fromisoformat(day)
    except ValueError:
        return {"error": "dateはYYYY-MM-DD形式で指定してください"}, 400

    DayExercise.delete(day_value, part, exercise)

    # その日に記録されたセットも合わせて削除し、履歴とセット記録の整合性を保つ
    TrainingSet.delete_for_exercise_on_date(exercise, day_value)
    db.session.commit()

    day_list = DayExercise.for_day(day_value)
    remaining_sets = TrainingSet.for_exercise(exercise)

    return {
        "date": day,
        "list": [e.to_dict() for e in day_list],
        "sets": [s.to_dict() for s in remaining_sets],
    }, 200


# ---------------- 種目メモ ----------------

def get_exercise_notes():
    return ExerciseNote.all_as_dict(), 200


def save_exercise_note(payload):
    exercise = payload.get("exercise")
    note = payload.get("note", "")

    if not exercise:
        return {"error": "exercise は必須です"}, 400

    if note:
        ExerciseNote.upsert(exercise, note)
    else:
        ExerciseNote.delete(exercise)
    db.session.commit()

    saved = ExerciseNote.get(exercise)
    return {"exercise": exercise, "note": saved.note if saved else ""}, 200
