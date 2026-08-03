#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
BOOTSTRAP
===================================================================
Model(models.py) / View(views.py) / Presenter(presenters.py) と
DB接続(extensions.py)・設定(config.py)・認証(auth.py)を組み立てて
起動するだけのエントリーポイント。アプリケーションロジックはここには書かない。
===================================================================
"""

import os

import config
from auth import register_auth
from extensions import db
from flask import Flask
from views import bp as views_bp

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BACKEND_DIR, "..", "frontend")


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    register_auth(app)
    app.register_blueprint(views_bp)

    return app


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="127.0.0.1", port=5000)
