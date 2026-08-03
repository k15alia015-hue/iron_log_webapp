#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリの設定をFlask流のConfigクラスで定義する。
app.config.from_object(...) で読み込む。環境ごとに Development / Production / Test を使い分ける。

DB接続情報・認証情報は.envから読み込む。
DATABASE_URL を環境変数で渡すと、MySQL接続文字列より優先される（テスト・一時利用向け）。
"""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

# .envはプロジェクトルート(backend/の一つ上)に置く
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))


def _build_mysql_uri():
    user = os.environ.get("DB_USER", "iron_log_user")
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "iron_log")
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{name}?charset=utf8mb4"
    )


class Config:
    """全環境共通のベース設定。"""

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or _build_mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ==== パスワード保護の設定 ====
    # ユーザー名・パスワードは必ず.env(IRON_LOG_USERNAME / IRON_LOG_PASSWORD)で設定すること。
    AUTH_ENABLED = True
    AUTH_USERNAME = os.environ.get("IRON_LOG_USERNAME", "change_me")
    AUTH_PASSWORD = os.environ.get("IRON_LOG_PASSWORD", "change_me")


class DevelopmentConfig(Config):
    """ローカル開発用。"""

    DEBUG = True


class ProductionConfig(Config):
    """本番用。"""

    DEBUG = False


class TestConfig(Config):
    """自動テスト用。実DBを汚さないようインメモリSQLiteを使い、認証も無効化する。"""

    TESTING = True
    DEBUG = True
    AUTH_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # インメモリSQLiteはコネクションごとに別DBになるため、単一コネクションを共有する
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
