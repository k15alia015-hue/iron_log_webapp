#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask拡張のインスタンスを保持する。
models.py / app.py の両方から参照されるため、循環importを避けるために独立させている。
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
