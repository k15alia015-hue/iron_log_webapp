#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
MODEL
===================================================================
役割:
  - データベースのテーブル定義（スキーマ）
  - データそのものに対する読み書き（クエリ）

Presenterからはこのモジュールの関数・メソッドを呼ぶだけでデータの
取得・更新ができる。HTTPリクエストやレスポンス整形の知識はここには持たせない。
===================================================================
"""

from extensions import db


class _GroupedQueryMixin:
    """追加順の全件取得を、指定したキーでグルーピングして返す共通処理。"""

    @classmethod
    def _all_grouped_by(cls, key_func):
        data = {}
        for row in cls.query.order_by(cls.id).all():
            data.setdefault(key_func(row), []).append(row.to_dict())
        return data


class TrainingSet(_GroupedQueryMixin, db.Model):
    __tablename__ = "training_sets"

    id = db.Column(db.Integer, primary_key=True)
    exercise = db.Column(db.String(255), nullable=False, index=True)
    weight = db.Column(db.Float, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    set_date = db.Column(db.Date, nullable=False)

    def to_dict(self):
        return {"weight": self.weight, "reps": self.reps, "date": self.set_date.isoformat()}

    # ---------------- クエリ ----------------

    @classmethod
    def all_grouped_by_exercise(cls):
        """種目名 -> セット一覧（追加順）の辞書を返す。"""
        return cls._all_grouped_by(lambda row: row.exercise)

    @classmethod
    def for_exercise(cls, exercise):
        """指定した種目のセット一覧を追加順で返す。"""
        return cls.query.filter_by(exercise=exercise).order_by(cls.id).all()

    @classmethod
    def create(cls, exercise, weight, reps, set_date):
        row = cls(exercise=exercise, weight=weight, reps=reps, set_date=set_date)
        db.session.add(row)
        return row

    @classmethod
    def delete_for_exercise_on_date(cls, exercise, set_date):
        cls.query.filter_by(exercise=exercise, set_date=set_date).delete()


class DayExercise(_GroupedQueryMixin, db.Model):
    __tablename__ = "day_exercises"
    __table_args__ = (db.UniqueConstraint("day", "part", "exercise", name="uq_day_part_exercise"),)

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Date, nullable=False, index=True)
    part = db.Column(db.String(50), nullable=False)
    exercise = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {"part": self.part, "exercise": self.exercise}

    # ---------------- クエリ ----------------

    @classmethod
    def all_grouped_by_day(cls):
        """日付(ISO文字列) -> 種目一覧（追加順）の辞書を返す。"""
        return cls._all_grouped_by(lambda row: row.day.isoformat())

    @classmethod
    def for_day(cls, day_value):
        """指定日に追加された種目一覧を追加順で返す。"""
        return cls.query.filter_by(day=day_value).order_by(cls.id).all()

    @classmethod
    def exists(cls, day_value, part, exercise):
        return cls.query.filter_by(day=day_value, part=part, exercise=exercise).first() is not None

    @classmethod
    def create(cls, day_value, part, exercise):
        row = cls(day=day_value, part=part, exercise=exercise)
        db.session.add(row)
        return row

    @classmethod
    def delete(cls, day_value, part, exercise):
        cls.query.filter_by(day=day_value, part=part, exercise=exercise).delete()


class ExerciseNote(db.Model):
    __tablename__ = "exercise_notes"

    exercise = db.Column(db.String(255), primary_key=True)
    note = db.Column(db.Text, nullable=False)

    # ---------------- クエリ ----------------

    @classmethod
    def all_as_dict(cls):
        """種目名 -> メモ の辞書を返す。"""
        return {row.exercise: row.note for row in cls.query.all()}

    @classmethod
    def get(cls, exercise):
        return cls.query.filter_by(exercise=exercise).first()

    @classmethod
    def upsert(cls, exercise, note):
        existing = cls.get(exercise)
        if existing:
            existing.note = note
        else:
            db.session.add(cls(exercise=exercise, note=note))

    @classmethod
    def delete(cls, exercise):
        existing = cls.get(exercise)
        if existing:
            db.session.delete(existing)
