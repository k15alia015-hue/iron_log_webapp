#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エラー処理の一元化。

Presenterは検証に失敗したら ApiError を raise するだけでよく、
ここで登録したハンドラが一括で JSON レスポンス {"error": ...} に変換する。
未定義のURL(404)や許可されないメソッド(405)もJSONで返す。
"""

from flask import jsonify


class ApiError(Exception):
    """APIの想定内エラー。message と HTTPステータスを持つ。"""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify({"error": err.message}), err.status

    @app.errorhandler(404)
    def handle_not_found(_err):
        return jsonify({"error": "リソースが見つかりません"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_err):
        return jsonify({"error": "許可されていないメソッドです"}), 405
