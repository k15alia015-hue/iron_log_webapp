#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flaskのカスタムコマンド。app_context付きで実行される。

  flask init-db       … 全テーブルを作成（マイグレーション未使用時のフォールバック）
  flask migrate-json  … 旧JSONファイル(training_data.json等)をDBへ移行
"""

import json
import os
from datetime import date

import click
from flask.cli import with_appcontext

from extensions import db
from models import DayExercise, ExerciseNote, TrainingSet

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(filename):
    path = os.path.join(ROOT_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _import_json_files():
    """プロジェクトルートのJSONファイルからDBへ一括投入する（DBが空のときだけ）。"""
    existing = (
        TrainingSet.query.count()
        + DayExercise.query.count()
        + ExerciseNote.query.count()
    )
    if existing > 0:
        click.echo(f"DBに既にデータが{existing}件あります。二重投入を避けるため中断しました。")
        return

    n_sets = 0
    for exercise, rows in _load_json("training_data.json").items():
        for s in rows:
            db.session.add(TrainingSet(
                exercise=exercise,
                weight=float(s["weight"]),
                reps=int(s["reps"]),
                set_date=date.fromisoformat(s["date"]),
            ))
            n_sets += 1

    n_days = 0
    for day, entries in _load_json("day_exercises.json").items():
        day_value = date.fromisoformat(day)
        for e in entries:
            db.session.add(DayExercise(day=day_value, part=e["part"], exercise=e["exercise"]))
            n_days += 1

    n_notes = 0
    for exercise, note in _load_json("exercise_notes.json").items():
        db.session.add(ExerciseNote(exercise=exercise, note=note))
        n_notes += 1

    db.session.commit()
    click.echo(f"移行が完了しました: sets {n_sets}件 / day_exercises {n_days}件 / notes {n_notes}件")


def register_cli(app):
    @app.cli.command("init-db")
    @with_appcontext
    def init_db():
        """全テーブルを作成する（マイグレーション未使用時のフォールバック）。"""
        db.create_all()
        click.echo("テーブルを作成しました。")

    @app.cli.command("migrate-json")
    @with_appcontext
    def migrate_json():
        """既存のJSONファイル(training_data.json等)をDBへ移行する。"""
        _import_json_files()
