#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest共通フィクスチャ。
TestConfig（インメモリSQLite・認証無効）でアプリを生成し、テストごとに
まっさらなテーブルを作り直すので、本番のMySQLを一切汚さない。
"""

import pytest

from app import create_app
from config import TestConfig
from extensions import db as _db


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
