#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存のJSONファイル(training_data.json / day_exercises.json / exercise_notes.json)を
MySQLデータベースへ一度だけ移行するスクリプト。

使い方:
    python migrate_json_to_mysql.py
"""

import json
import os
from datetime import date

from app import app
from extensions import db
from models import DayExercise, ExerciseNote, TrainingSet

# 移行元のJSONファイルはプロジェクトルート(backend/の一つ上)にある
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT_DIR, "training_data.json")
DAY_EXERCISES_FILE = os.path.join(ROOT_DIR, "day_exercises.json")
NOTES_FILE = os.path.join(ROOT_DIR, "exercise_notes.json")


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def migrate_sets():
    raw = load_json(DATA_FILE)
    count = 0
    for exercise, sets in raw.items():
        for s in sets:
            db.session.add(TrainingSet(
                exercise=exercise,
                weight=float(s["weight"]),
                reps=int(s["reps"]),
                set_date=date.fromisoformat(s["date"]),
            ))
            count += 1
    print(f"training_sets: {count}件を投入")


def migrate_day_exercises():
    raw = load_json(DAY_EXERCISES_FILE)
    count = 0
    for day, entries in raw.items():
        day_value = date.fromisoformat(day)
        for e in entries:
            db.session.add(DayExercise(day=day_value, part=e["part"], exercise=e["exercise"]))
            count += 1
    print(f"day_exercises: {count}件を投入")


def migrate_notes():
    raw = load_json(NOTES_FILE)
    count = 0
    for exercise, note in raw.items():
        db.session.add(ExerciseNote(exercise=exercise, note=note))
        count += 1
    print(f"exercise_notes: {count}件を投入")


def main():
    with app.app_context():
        db.create_all()

        existing = (
            TrainingSet.query.count()
            + DayExercise.query.count()
            + ExerciseNote.query.count()
        )
        if existing > 0:
            print(f"DBに既にデータが{existing}件あります。二重投入を避けるため中断しました。")
            return

        migrate_sets()
        migrate_day_exercises()
        migrate_notes()
        db.session.commit()
        print("移行が完了しました。")


if __name__ == "__main__":
    main()
