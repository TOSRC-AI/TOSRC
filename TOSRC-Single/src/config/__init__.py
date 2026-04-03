#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块

包含配置加载、环境变量管理等
"""

import os
from typing import Optional

class StorageConfig:
    """
    存储配置类
    统一管理 SQLite 和 JSONL 存储的配置
    """

    # SQLite 数据库路径
    SQLITE_DB_PATH = os.getenv("DATABASE_URL", "sqlite:///data/database/tosrc.db").replace("sqlite:///", "")

    # JSONL 日志目录
    ROUTE_LOG_DIR = os.getenv("ROUTE_LOG_DIR", "data/logs/routes")
    FEEDBACK_LOG_DIR = os.getenv("FEEDBACK_LOG_DIR", "data/logs/feedback")

    # 功能开关
    ENABLE_SQLITE_LOG = os.getenv("ENABLE_SQLITE_LOG", "true").lower() == "true"
    ENABLE_JSONL_LOG = os.getenv("ENABLE_JSONL_LOG", "true").lower() == "true"

    # 归档配置
    ARCHIVE_AFTER_DAYS = int(os.getenv("ARCHIVE_AFTER_DAYS", "7"))
    DELETE_AFTER_DAYS = int(os.getenv("DELETE_AFTER_DAYS", "90"))
    ENABLE_AUTO_ARCHIVE = os.getenv("ENABLE_AUTO_ARCHIVE", "true").lower() == "true"

    @classmethod
    def get_stats(cls) -> dict:
        """获取存储配置统计"""
        return {
            "sqlite": {
                "enabled": cls.ENABLE_SQLITE_LOG,
                "path": cls.SQLITE_DB_PATH
            },
            "jsonl": {
                "enabled": cls.ENABLE_JSONL_LOG,
                "route_log_dir": cls.ROUTE_LOG_DIR,
                "feedback_log_dir": cls.FEEDBACK_LOG_DIR
            },
            "archive": {
                "enabled": cls.ENABLE_AUTO_ARCHIVE,
                "archive_after_days": cls.ARCHIVE_AFTER_DAYS,
                "delete_after_days": cls.DELETE_AFTER_DAYS
            }
        }
