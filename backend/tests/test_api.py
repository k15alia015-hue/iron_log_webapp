#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIの振る舞いを検証する自動テスト。
認証はTestConfigで無効化しているので、認証ヘッダなしで叩ける。
"""


# ---------------- 参照系 ----------------

def test_body_parts(client):
    res = client.get("/api/body-parts")
    assert res.status_code == 200
    data = res.get_json()
    assert "胸" in data
    assert "ベンチプレス" in data["胸"]


def test_sets_empty_initially(client):
    res = client.get("/api/sets")
    assert res.status_code == 200
    assert res.get_json() == {}


# ---------------- セット ----------------

def test_add_and_get_set(client):
    res = client.post("/api/sets", json={"exercise": "ベンチプレス", "weight": 60, "reps": 10, "date": "2026-08-03"})
    assert res.status_code == 201
    sets = client.get("/api/sets").get_json()
    assert sets["ベンチプレス"][0] == {"weight": 60.0, "reps": 10, "date": "2026-08-03"}


def test_add_set_missing_fields(client):
    res = client.post("/api/sets", json={"exercise": "ベンチプレス"})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_add_set_bad_date(client):
    res = client.post("/api/sets", json={"exercise": "X", "weight": 1, "reps": 1, "date": "bad"})
    assert res.status_code == 400


def test_add_set_invalid_reps(client):
    res = client.post("/api/sets", json={"exercise": "X", "weight": 1, "reps": 0})
    assert res.status_code == 400


def test_delete_set(client):
    client.post("/api/sets", json={"exercise": "ベンチプレス", "weight": 60, "reps": 10, "date": "2026-08-03"})
    res = client.delete("/api/sets/ベンチプレス/0")
    assert res.status_code == 200
    assert res.get_json()["sets"] == []


def test_delete_set_out_of_range(client):
    res = client.delete("/api/sets/ベンチプレス/0")
    assert res.status_code == 404


# ---------------- 種目メモ ----------------

def test_notes_upsert_and_clear(client):
    res = client.post("/api/exercise-notes", json={"exercise": "ベンチプレス", "note": "メモ"})
    assert res.status_code == 200
    assert client.get("/api/exercise-notes").get_json()["ベンチプレス"] == "メモ"
    # 空noteで削除
    client.post("/api/exercise-notes", json={"exercise": "ベンチプレス", "note": ""})
    assert "ベンチプレス" not in client.get("/api/exercise-notes").get_json()


# ---------------- 日付ごとの種目 ----------------

def test_day_exercise_add_and_reject_unknown(client):
    res = client.post("/api/day-exercises", json={"date": "2026-08-03", "part": "胸", "exercise": "ベンチプレス"})
    assert res.status_code == 201
    # マスタにない組み合わせは拒否
    res = client.post("/api/day-exercises", json={"date": "2026-08-03", "part": "胸", "exercise": "存在しない種目"})
    assert res.status_code == 400


# ---------------- ユーザー追加種目（追加・編集・削除） ----------------

def test_add_custom_exercise(client):
    res = client.post("/api/exercises", json={"part": "胸", "exercise": "自作種目"})
    assert res.status_code == 201
    body = res.get_json()
    assert "自作種目" in body["customExercises"]["胸"]
    assert "自作種目" in body["bodyParts"]["胸"]


def test_add_custom_exercise_duplicate(client):
    client.post("/api/exercises", json={"part": "胸", "exercise": "自作種目"})
    # ユーザー追加分と重複
    assert client.post("/api/exercises", json={"part": "胸", "exercise": "自作種目"}).status_code == 409
    # 初期マスタと重複
    assert client.post("/api/exercises", json={"part": "胸", "exercise": "ベンチプレス"}).status_code == 409


def test_add_custom_exercise_empty_name(client):
    res = client.post("/api/exercises", json={"part": "胸", "exercise": "   "})
    assert res.status_code == 400


def test_rename_custom_exercise_carries_records(client):
    client.post("/api/exercises", json={"part": "肩", "exercise": "カスタム肩"})
    client.post("/api/day-exercises", json={"date": "2026-08-03", "part": "肩", "exercise": "カスタム肩"})
    client.post("/api/sets", json={"exercise": "カスタム肩", "weight": 40, "reps": 8, "date": "2026-08-03"})
    client.post("/api/exercise-notes", json={"exercise": "カスタム肩", "note": "メモ"})

    res = client.patch("/api/exercises/肩/カスタム肩", json={"newName": "カスタム肩2"})
    assert res.status_code == 200

    sets = client.get("/api/sets").get_json()
    assert "カスタム肩2" in sets and "カスタム肩" not in sets
    notes = client.get("/api/exercise-notes").get_json()
    assert notes.get("カスタム肩2") == "メモ"


def test_rename_master_exercise_blocked(client):
    res = client.patch("/api/exercises/胸/ベンチプレス", json={"newName": "改名"})
    assert res.status_code == 400


def test_rename_to_existing_name_blocked(client):
    client.post("/api/exercises", json={"part": "胸", "exercise": "自作種目"})
    res = client.patch("/api/exercises/胸/自作種目", json={"newName": "ベンチプレス"})
    assert res.status_code == 409


def test_delete_custom_exercise_purges_records(client):
    client.post("/api/exercises", json={"part": "腕", "exercise": "消す種目"})
    client.post("/api/sets", json={"exercise": "消す種目", "weight": 10, "reps": 5, "date": "2026-08-03"})

    res = client.delete("/api/exercises/腕/消す種目")
    assert res.status_code == 200

    sets = client.get("/api/sets").get_json()
    assert "消す種目" not in sets
    assert "消す種目" not in client.get("/api/custom-exercises").get_json().get("腕", [])


def test_delete_master_exercise_blocked(client):
    res = client.delete("/api/exercises/胸/ベンチプレス")
    assert res.status_code == 400


# ---------------- レストタイマー ----------------

def test_timer_save_and_get(client):
    res = client.post("/api/exercise-timers", json={"exercise": "ベンチプレス", "restSeconds": 150})
    assert res.status_code == 200
    assert res.get_json()["restSeconds"] == 150
    assert client.get("/api/exercise-timers").get_json()["ベンチプレス"] == 150


def test_timer_disable_removes_setting(client):
    client.post("/api/exercise-timers", json={"exercise": "ベンチプレス", "restSeconds": 90})
    res = client.post("/api/exercise-timers", json={"exercise": "ベンチプレス", "restSeconds": 0})
    assert res.status_code == 200
    assert res.get_json()["restSeconds"] == 0
    assert "ベンチプレス" not in client.get("/api/exercise-timers").get_json()


def test_timer_rejects_invalid_value(client):
    # 分1〜5・秒10〜50の組み合わせ以外は拒否（95秒 = 1分35秒は不正）
    res = client.post("/api/exercise-timers", json={"exercise": "ベンチプレス", "restSeconds": 95})
    assert res.status_code == 400


def test_timer_carried_and_purged_with_custom_exercise(client):
    client.post("/api/exercises", json={"part": "胸", "exercise": "自作種目"})
    client.post("/api/exercise-timers", json={"exercise": "自作種目", "restSeconds": 130})
    # リネームでタイマー設定が引き継がれる
    client.patch("/api/exercises/胸/自作種目", json={"newName": "自作種目2"})
    timers = client.get("/api/exercise-timers").get_json()
    assert timers.get("自作種目2") == 130 and "自作種目" not in timers
    # 削除でタイマー設定も消える
    client.delete("/api/exercises/胸/自作種目2")
    assert "自作種目2" not in client.get("/api/exercise-timers").get_json()


# ---------------- エラーハンドラ ----------------

def test_unknown_route_returns_json_404(client):
    res = client.get("/api/nope")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_method_not_allowed_returns_json_405(client):
    res = client.post("/api/body-parts")
    assert res.status_code == 405
    assert "error" in res.get_json()
