#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリ全体にかけるBasic認証。
"""

from flask import Response, request

from config import AUTH_PASSWORD, AUTH_USERNAME


def check_auth(username, password):
    """入力されたユーザー名・パスワードが正しいか確認する。"""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


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
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
