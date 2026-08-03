#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリ全体にかけるBasic認証。
ユーザー名・パスワードは app.config（＝Configクラス／.env）から読む。
config の AUTH_ENABLED が False のときは認証をかけない（テスト用）。
"""

from hmac import compare_digest

from flask import Response, current_app, request


def check_auth(username, password):
    """入力されたユーザー名・パスワードが正しいか確認する。

    タイミング攻撃を避けるため compare_digest で定数時間比較する。
    """
    expected_user = current_app.config["AUTH_USERNAME"]
    expected_pass = current_app.config["AUTH_PASSWORD"]
    # compare_digestは非ASCII文字列を直接扱えないため、UTF-8バイト列で比較する
    return (
        compare_digest((username or "").encode("utf-8"), expected_user.encode("utf-8"))
        and compare_digest((password or "").encode("utf-8"), expected_pass.encode("utf-8"))
    )


def authenticate():
    """認証を促すレスポンスを返す。"""
    return Response(
        "この画面を見るにはログインが必要です。",
        401,
        {"WWW-Authenticate": 'Basic realm="IRON LOG"'},
    )


def register_auth(app):
    """静的ファイルを含む、アプリ全体にBasic認証をかける。"""

    @app.before_request
    def require_login():
        if not app.config.get("AUTH_ENABLED", True):
            return
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
