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

各関数は成功時に (レスポンスに入れるdict, HTTPステータスコード) のタプルを返す。
検証に失敗した場合は ApiError を raise し、errors.py のハンドラが JSON に変換する。
Flaskのrequest/responseオブジェクトには一切触れず、Viewから渡された
素のデータ（dict・文字列など）だけを扱う。
===================================================================
"""

from datetime import date

from body_parts import BODY_PARTS, merge_body_parts
from errors import ApiError
from extensions import db
from models import CustomExercise, DayExercise, ExerciseNote, ExerciseTimer, TrainingSet

# レストタイマーで選べるレスト秒数（分 1〜5 × 秒 0/10/20/30/40/50 の組み合わせ）。
# restSeconds 0 は「不使用」を表す（分は1以上なので選択値と衝突しない）。
ALLOWED_REST_SECONDS = frozenset(
    minutes * 60 + seconds
    for minutes in range(1, 6)
    for seconds in (0, 10, 20, 30, 40, 50)
)


def _require_date(date_str):
    """YYYY-MM-DD形式の文字列をdateに変換する。不正な場合はApiErrorを送出する。"""
    try:
        return date.fromisoformat(date_str)
    except (TypeError, ValueError):
        raise ApiError("dateはYYYY-MM-DD形式で指定してください", 400)


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


def _require_custom_exercise(part, exercise):
    """部位が正しく、かつ指定種目がユーザー追加種目であることを検証する（不正ならApiError）。"""
    if part not in BODY_PARTS:
        raise ApiError("指定された部位が正しくありません", 400)
    if not CustomExercise.exists(part, exercise):
        raise ApiError("その種目は編集・削除できません（初期種目は変更できません）", 400)


def _reject_duplicate_name(part, name):
    """指定した種目名がその部位に既に存在すれば重複エラー（初期・ユーザー追加のどちらも対象）。"""
    if name in _effective_body_parts()[part]:
        raise ApiError("その種目はすでに存在します", 409)


# ---------------- 部位・種目 ----------------

def get_body_parts():
    return _effective_body_parts(), 200


def get_custom_exercises():
    return CustomExercise.all_grouped_by_part(), 200


def add_exercise(payload):
    part = payload.get("part")
    exercise = payload.get("exercise")

    if not part or not exercise:
        raise ApiError("part, exercise は必須です", 400)

    exercise = exercise.strip()
    if not exercise:
        raise ApiError("種目名を入力してください", 400)

    if part not in BODY_PARTS:
        raise ApiError("指定された部位が正しくありません", 400)

    _reject_duplicate_name(part, exercise)

    CustomExercise.create(part, exercise)
    db.session.commit()

    return _exercise_lists_payload(part=part, exercise=exercise), 201


def rename_exercise(part, old_name, payload):
    new_name = (payload.get("newName") or "").strip()
    if not new_name:
        raise ApiError("種目名を入力してください", 400)

    _require_custom_exercise(part, old_name)

    if new_name == old_name:
        return _exercise_lists_payload(part=part, exercise=new_name), 200

    _reject_duplicate_name(part, new_name)

    CustomExercise.rename(part, old_name, new_name)
    # 履歴・記録・メモ・タイマーに残る参照名も合わせて更新し、リネーム後も設定が引き継がれるようにする
    DayExercise.rename_exercise_in_part(part, old_name, new_name)
    TrainingSet.rename_exercise(old_name, new_name)
    ExerciseNote.rename_exercise(old_name, new_name)
    ExerciseTimer.rename_exercise(old_name, new_name)
    db.session.commit()

    return _exercise_lists_payload(part=part, exercise=new_name), 200


def delete_exercise(part, exercise):
    _require_custom_exercise(part, exercise)

    CustomExercise.delete(part, exercise)
    # この種目に紐づく履歴・記録・メモ・タイマーもすべて削除する
    DayExercise.delete_all_for_exercise(part, exercise)
    TrainingSet.delete_by_exercise(exercise)
    ExerciseNote.delete_by_exercise(exercise)
    ExerciseTimer.delete_by_exercise(exercise)
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
        raise ApiError("exercise, weight, reps は必須です", 400)

    try:
        weight = float(weight)
        reps = int(reps)
        if reps <= 0 or weight < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ApiError("weightは数値、repsは1以上の整数で指定してください", 400)

    set_date = _require_date(set_date) if set_date else date.today()

    TrainingSet.create(exercise, weight, reps, set_date)
    db.session.commit()

    sets = TrainingSet.for_exercise(exercise)
    return {"exercise": exercise, "sets": [s.to_dict() for s in sets]}, 201


def delete_set(exercise, index):
    sets = TrainingSet.for_exercise(exercise)

    if not (0 <= index < len(sets)):
        raise ApiError("指定されたセットが見つかりません", 404)

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
        raise ApiError("date, part, exercise は必須です", 400)

    day_value = _require_date(day)

    effective = _effective_body_parts()
    if part not in effective or exercise not in effective[part]:
        raise ApiError("指定された部位・種目の組み合わせが正しくありません", 400)

    if not DayExercise.exists(day_value, part, exercise):
        DayExercise.create(day_value, part, exercise)
        db.session.commit()

    day_list = DayExercise.for_day(day_value)
    return {"date": day, "list": [e.to_dict() for e in day_list]}, 201


def delete_day_exercise(day, part, exercise):
    day_value = _require_date(day)

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
        raise ApiError("exercise は必須です", 400)

    if note:
        ExerciseNote.upsert(exercise, note)
    else:
        ExerciseNote.delete(exercise)
    db.session.commit()

    saved = ExerciseNote.get(exercise)
    return {"exercise": exercise, "note": saved.note if saved else ""}, 200


# ---------------- レストタイマー ----------------

def get_exercise_timers():
    return ExerciseTimer.all_as_dict(), 200


def save_exercise_timer(payload):
    exercise = payload.get("exercise")
    rest_seconds = payload.get("restSeconds")

    if not exercise:
        raise ApiError("exercise は必須です", 400)

    try:
        rest_seconds = int(rest_seconds)
    except (TypeError, ValueError):
        raise ApiError("restSeconds は整数で指定してください", 400)

    if rest_seconds <= 0:
        # 0以下は「不使用」。設定があれば削除する。
        ExerciseTimer.delete(exercise)
        db.session.commit()
        return {"exercise": exercise, "restSeconds": 0}, 200

    if rest_seconds not in ALLOWED_REST_SECONDS:
        raise ApiError("指定できないレスト時間です（分1〜5・秒10〜50から選択してください）", 400)

    ExerciseTimer.upsert(exercise, rest_seconds)
    db.session.commit()
    return {"exercise": exercise, "restSeconds": rest_seconds}, 200
