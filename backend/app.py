#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
BOOTSTRAP
===================================================================
Model(models.py) / View(views.py) / Presenter(presenters.py) と、
設定(config.py)・DB接続とマイグレーション(extensions.py)・認証(auth.py)・
エラー処理(errors.py)・CLIコマンド(cli.py) を組み立てて起動する
アプリケーションファクトリ。アプリケーションロジックはここには書かない。

環境は環境変数 FLASK_CONFIG（development / production / testing）で切り替える。
スキーマは Flask-Migrate で管理する（初回や別環境では `flask db upgrade`）。
===================================================================
"""

import os

import config as config_module
from auth import register_auth
from cli import register_cli
from errors import register_error_handlers
from extensions import db, migrate
from flask import Flask
from views import bp as views_bp

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BACKEND_DIR, "..", "frontend")

_CONFIGS = {
    "development": config_module.DevelopmentConfig,
    "production": config_module.ProductionConfig,
    "testing": config_module.TestConfig,
}


def create_app(config_object=None):
    """アプリケーションファクトリ。config_objectを渡すとその設定で生成する
    （テスト用）。省略時は環境変数 FLASK_CONFIG（既定: development）で決める。"""
    if config_object is None:
        name = os.environ.get("FLASK_CONFIG", "development")
        config_object = _CONFIGS.get(name, config_module.DevelopmentConfig)

    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
    )
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    register_auth(app)
    register_error_handlers(app)
    register_cli(app)
    app.register_blueprint(views_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
