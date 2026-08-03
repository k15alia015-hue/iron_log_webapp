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
    def _all_grouped_by(cls, key_func, value_func=None):
        value_func = value_func or (lambda row: row.to_dict())
        data = {}
        for row in cls.query.order_by(cls.id).all():
            data.setdefault(key_func(row), []).append(value_func(row))
        return data


class _ExerciseRefMixin:
    """exercise列で種目を参照するテーブル共通の、種目名リネーム/一括削除。

    このアプリはセット記録・メモを「種目名」で識別するため、リネーム・削除は
    種目名単位で行う（day_exercisesのみ部位も持つので、そちらは別途部位で絞る）。
    """

    @classmethod
    def rename_exercise(cls, old_name, new_name):
        cls.query.filter_by(exercise=old_name).update({"exercise": new_name})

    @classmethod
    def delete_by_exercise(cls, exercise):
        cls.query.filter_by(exercise=exercise).delete()


class TrainingSet(_GroupedQueryMixin, _ExerciseRefMixin, db.Model):
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

    @classmethod
    def rename_exercise_in_part(cls, part, old_name, new_name):
        """指定部位の種目名を一括で変更する（他部位の同名種目には影響させない）。"""
        cls.query.filter_by(part=part, exercise=old_name).update({"exercise": new_name})

    @classmethod
    def delete_all_for_exercise(cls, part, exercise):
        """指定部位の指定種目の割り当てをすべて削除する。"""
        cls.query.filter_by(part=part, exercise=exercise).delete()


class CustomExercise(_GroupedQueryMixin, db.Model):
    """ユーザーが追加した種目。部位ごとの初期マスタ(body_parts.py)に対する追加分。"""

    __tablename__ = "custom_exercises"
    __table_args__ = (db.UniqueConstraint("part", "exercise", name="uq_part_exercise"),)

    id = db.Column(db.Integer, primary_key=True)
    part = db.Column(db.String(50), nullable=False, index=True)
    exercise = db.Column(db.String(255), nullable=False)

    @classmethod
    def all_grouped_by_part(cls):
        """部位 -> 種目名一覧（追加順）の辞書を返す。"""
        return cls._all_grouped_by(lambda row: row.part, lambda row: row.exercise)

    @classmethod
    def exists(cls, part, exercise):
        return cls.query.filter_by(part=part, exercise=exercise).first() is not None

    @classmethod
    def create(cls, part, exercise):
        row = cls(part=part, exercise=exercise)
        db.session.add(row)
        return row

    @classmethod
    def rename(cls, part, old_name, new_name):
        row = cls.query.filter_by(part=part, exercise=old_name).first()
        if row:
            row.exercise = new_name
        return row

    @classmethod
    def delete(cls, part, exercise):
        cls.query.filter_by(part=part, exercise=exercise).delete()


class _ExerciseKeyedValueMixin(_ExerciseRefMixin):
    """exercise をキーに単一の値を1つ持つテーブル共通のCRUD（メモ・タイマーなど）。

    値カラム名はサブクラスの _value_attr で指定する。
    _ExerciseRefMixin も継承するので、種目名のリネーム/一括削除にも対応する。
    """

    _value_attr = None  # サブクラスで "note" / "rest_seconds" などを指定する

    @classmethod
    def all_as_dict(cls):
        """種目名 -> 値 の辞書を返す。"""
        return {row.exercise: getattr(row, cls._value_attr) for row in cls.query.all()}

    @classmethod
    def get(cls, exercise):
        return cls.query.filter_by(exercise=exercise).first()

    @classmethod
    def upsert(cls, exercise, value):
        row = cls.get(exercise)
        if row:
            setattr(row, cls._value_attr, value)
        else:
            row = cls(exercise=exercise)
            setattr(row, cls._value_attr, value)
            db.session.add(row)
        return row

    @classmethod
    def delete(cls, exercise):
        row = cls.get(exercise)
        if row:
            db.session.delete(row)


class ExerciseNote(_ExerciseKeyedValueMixin, db.Model):
    __tablename__ = "exercise_notes"
    _value_attr = "note"

    exercise = db.Column(db.String(255), primary_key=True)
    note = db.Column(db.Text, nullable=False)


class ExerciseTimer(_ExerciseKeyedValueMixin, db.Model):
    """種目ごとのレストタイマー設定（rest_seconds 秒）。行が無い＝不使用。"""

    __tablename__ = "exercise_timers"
    _value_attr = "rest_seconds"

    exercise = db.Column(db.String(255), primary_key=True)
    rest_seconds = db.Column(db.Integer, nullable=False)
