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

from body_parts import merge_body_parts
from config import BODY_PARTS
from extensions import db
from models import CustomExercise, DayExercise, ExerciseNote, TrainingSet

DATE_FORMAT_ERROR = {"error": "dateはYYYY-MM-DD形式で指定してください"}, 400
NAME_REQUIRED_ERROR = {"error": "種目名を入力してください"}, 400


def _parse_date(date_str):
    """YYYY-MM-DD形式の文字列をdateに変換する。不正な場合はNoneを返す。"""
    try:
        return date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None


def _effective_body_parts():
    """初期マスタとユーザー追加種目を合成した、実際に使う部位・種目一覧。"""
    return merge_body_parts(BODY_PARTS, CustomExercise.all_grouped_by_part())


def _exercise_lists_payload(**extra):
    """種目一覧が変化する操作の共通レスポンス。最新の全体像を返す。

    bodyParts:       初期＋ユーザー追加を合成した全種目
    customExercises: ユーザー追加分だけ（編集・削除できる種目の判定に使う）
    """
    payload = {
        "bodyParts": _effective_body_parts(),
        "customExercises": CustomExercise.all_grouped_by_part(),
    }
    payload.update(extra)
    return payload


def _validate_custom_exercise(part, exercise):
    """部位が正しく、かつ指定種目がユーザー追加種目であることを検証する。

    問題なければNone、あればエラーレスポンス(dict, status)を返す。
    """
    if part not in BODY_PARTS:
        return {"error": "指定された部位が正しくありません"}, 400
    if not CustomExercise.exists(part, exercise):
        return {"error": "その種目は編集・削除できません（初期種目は変更できません）"}, 400
    return None


def _duplicate_name_error(part, name):
    """指定した種目名がその部位に既に存在すれば409エラー、なければNoneを返す。

    初期マスタ・ユーザー追加分のどちらかにあれば重複として扱う。
    """
    if name in _effective_body_parts()[part]:
        return {"error": "その種目はすでに存在します"}, 409
    return None


def get_body_parts():
    return _effective_body_parts(), 200


def get_custom_exercises():
    return CustomExercise.all_grouped_by_part(), 200


def add_exercise(payload):
    part = payload.get("part")
    exercise = payload.get("exercise")

    if not part or not exercise:
        return {"error": "part, exercise は必須です"}, 400

    exercise = exercise.strip()
    if not exercise:
        return NAME_REQUIRED_ERROR

    if part not in BODY_PARTS:
        return {"error": "指定された部位が正しくありません"}, 400

    duplicate = _duplicate_name_error(part, exercise)
    if duplicate:
        return duplicate

    CustomExercise.create(part, exercise)
    db.session.commit()

    return _exercise_lists_payload(part=part, exercise=exercise), 201


def rename_exercise(part, old_name, payload):
    new_name = (payload.get("newName") or "").strip()
    if not new_name:
        return NAME_REQUIRED_ERROR

    error = _validate_custom_exercise(part, old_name)
    if error:
        return error

    if new_name == old_name:
        return _exercise_lists_payload(part=part, exercise=new_name), 200

    duplicate = _duplicate_name_error(part, new_name)
    if duplicate:
        return duplicate

    CustomExercise.rename(part, old_name, new_name)
    # 履歴・記録・メモに残る参照名も合わせて更新し、リネーム後も記録が引き継がれるようにする
    DayExercise.rename_exercise_in_part(part, old_name, new_name)
    TrainingSet.rename_exercise(old_name, new_name)
    ExerciseNote.rename_exercise(old_name, new_name)
    db.session.commit()

    return _exercise_lists_payload(part=part, exercise=new_name), 200


def delete_exercise(part, exercise):
    error = _validate_custom_exercise(part, exercise)
    if error:
        return error

    CustomExercise.delete(part, exercise)
    # この種目に紐づく履歴・記録・メモもすべて削除する
    DayExercise.delete_all_for_exercise(part, exercise)
    TrainingSet.delete_by_exercise(exercise)
    ExerciseNote.delete_by_exercise(exercise)
    db.session.commit()

    return _exercise_lists_payload(part=part, exercise=exercise), 200


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
        set_date = _parse_date(set_date)
        if set_date is None:
            return DATE_FORMAT_ERROR
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

    day_value = _parse_date(day)
    if day_value is None:
        return DATE_FORMAT_ERROR

    effective = _effective_body_parts()
    if part not in effective or exercise not in effective[part]:
        return {"error": "指定された部位・種目の組み合わせが正しくありません"}, 400

    if not DayExercise.exists(day_value, part, exercise):
        DayExercise.create(day_value, part, exercise)
        db.session.commit()

    day_list = DayExercise.for_day(day_value)
    return {"date": day, "list": [e.to_dict() for e in day_list]}, 201


def delete_day_exercise(day, part, exercise):
    day_value = _parse_date(day)
    if day_value is None:
        return DATE_FORMAT_ERROR

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
