#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仿生架构数据库访问层（BionicDB）
提供 SQLite 数据访问的全局单例实例
"""
import os
import sqlite3
import json
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

# 默认数据库路径（从环境变量或默认值推导）
DEFAULT_DB_PATH = os.getenv(
    "DATABASE_URL", "sqlite:///data/database/tosrc_single.db"
).replace("sqlite:///", "")

# 如果相对路径解析失败，尝试基于当前文件位置推导
if not os.path.isabs(DEFAULT_DB_PATH):
    _BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    DEFAULT_DB_PATH = os.path.join(_BASE_DIR, DEFAULT_DB_PATH)


class BionicDB:
    """仿生架构核心数据库访问类（最小恢复版）"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_db_dir()
        self._init_schema()

    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _init_schema(self):
        """自动初始化核心数据表（如果不存在）"""
        schema = """
        CREATE TABLE IF NOT EXISTS intents (
            intent_id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_code VARCHAR(100) NOT NULL UNIQUE,
            intent_name VARCHAR(100) NOT NULL,
            parent_id INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 500,
            is_enabled INTEGER DEFAULT 1,
            description TEXT,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS intent_neurons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_id VARCHAR(100) NOT NULL UNIQUE,
            intent_code VARCHAR(100) NOT NULL,
            intent_name VARCHAR(100),
            description TEXT,
            base_priority INTEGER DEFAULT 1,
            route_target VARCHAR(200),
            is_enabled INTEGER DEFAULT 1,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS synapse_weights (
            synapse_id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_id VARCHAR(100) NOT NULL,
            keyword VARCHAR(200) NOT NULL,
            weight FLOAT DEFAULT 1.0,
            user_id VARCHAR(64) DEFAULT 'global',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(intent_id, keyword, user_id)
        );
        CREATE TABLE IF NOT EXISTS entity_types (
            entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_code VARCHAR(100) NOT NULL UNIQUE,
            entity_name VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50) DEFAULT 'enum',
            description TEXT,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS entity_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_code VARCHAR(100) NOT NULL,
            keyword VARCHAR(128) NOT NULL,
            weight FLOAT DEFAULT 1.0,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS route_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            intent_code VARCHAR(100),
            intent_name VARCHAR(100),
            entities TEXT,
            confidence FLOAT DEFAULT 0.0,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS learning_samples (
            sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            intent_code VARCHAR(100),
            entities TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            is_annotated INTEGER DEFAULT 0,
            correct_intent VARCHAR(100),
            correct_entities TEXT,
            confidence FLOAT DEFAULT 0.0,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS system_config (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key VARCHAR(100) NOT NULL UNIQUE,
            config_value TEXT,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self.get_connection(write=True) as conn:
            conn.executescript(schema)

    @contextmanager
    def get_connection(self, write: bool = False):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            if write:
                conn.commit()
        finally:
            conn.close()

    # ========== 意图神经元 ==========
    def get_all_intent_neurons(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM intent_neurons WHERE is_enabled = 1")
            return [dict(row) for row in cursor.fetchall()]

    def get_synapse_weights_by_intent(self, intent_id: str, user_id: str = "global") -> Dict[str, float]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT keyword, weight FROM synapse_weights WHERE intent_id = ? AND user_id = ?",
                (intent_id, user_id),
            )
            return {row["keyword"]: row["weight"] for row in cursor.fetchall()}

    def add_intent_neuron(self, scene_id: str, intent_id: str, intent_name: str, description: str = "", base_priority: int = 1) -> bool:
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO intent_neurons (intent_id, intent_code, intent_name, description, base_priority) VALUES (?, ?, ?, ?, ?)",
                    (intent_id, intent_id, intent_name, description, base_priority),
                )
                return cursor.rowcount > 0
            except Exception:
                return False

    # ========== 路由管理 ==========
    def get_all_route_mappings(self) -> Dict[str, str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT intent_id, route_target FROM intent_neurons WHERE is_enabled = 1")
            return {row["intent_id"]: row["route_target"] or "" for row in cursor.fetchall()}

    def update_intent_route_target(self, intent_id: str, route_target: str) -> bool:
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE intent_neurons SET route_target = ? WHERE intent_id = ?",
                (route_target, intent_id),
            )
            return cursor.rowcount > 0

    # ========== 缓存类接口（stub 返回空结构） ==========
    def get_intent_keyword_cache(self) -> Dict[str, List[str]]:
        return {}

    def get_intent_dict_cache(self) -> Dict[str, Dict[str, Any]]:
        return {}

    def get_emotion_keyword_cache(self) -> Dict[str, List[Dict[str, Any]]]:
        return {}

    def get_emotion_dict_cache(self) -> Dict[str, Dict[str, Any]]:
        return {}

    def get_entity_keyword_cache(self) -> Dict[str, List[str]]:
        return {}

    def get_business_intent_keyword_cache(self, industry_code: str = "default") -> Dict[str, List[str]]:
        return {}

    def get_business_intent_cache(self, industry_code: str = "default") -> List[Dict[str, Any]]:
        return []

    def get_business_entity_keyword_cache(self, industry_code: str = "default") -> Dict[str, List[str]]:
        return {}

    def get_business_entity_cache(self, industry_code: str = "default") -> List[Dict[str, Any]]:
        return {}

    # ========== 突触权重 ==========
    def update_synapse_weight(self, intent_id: str, keyword: str, weight: float, user_id: str = "global") -> bool:
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO synapse_weights (intent_id, keyword, weight, user_id) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(intent_id, keyword, user_id) DO UPDATE SET weight=excluded.weight",
                (intent_id, keyword, weight, user_id),
            )
            return cursor.rowcount > 0

    def add_synapse_weight(self, intent_id: str, keyword: str, weight: float) -> bool:
        return self.update_synapse_weight(intent_id, keyword, weight)

    def batch_update_weights(self, update_batch: List[Dict[str, Any]]) -> bool:
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            for item in update_batch:
                cursor.execute(
                    "INSERT INTO synapse_weights (intent_id, keyword, weight) VALUES (?, ?, ?) "
                    "ON CONFLICT(intent_id, keyword, user_id) DO UPDATE SET weight=excluded.weight",
                    (item.get("intent_id"), item.get("keyword"), item.get("weight")),
                )
            return True

    # ========== 实体关联 ==========
    def add_entity_association(self, intent_id: str, entity_id: str) -> bool:
        # 简化实现：仅记录日志，不实际建表
        return True

    # ========== 样本管理 ==========
    def add_low_confidence_sample(self, sample: Dict[str, Any]) -> int:
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO learning_samples (text, intent_code, entities, confidence) VALUES (?, ?, ?, ?)",
                (
                    sample.get("text", ""),
                    sample.get("intent_code", ""),
                    json.dumps(sample.get("entities", [])),
                    sample.get("confidence", 0.0),
                ),
            )
            return cursor.lastrowid

    def get_low_confidence_samples(self, status: str = "pending", limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM learning_samples WHERE status = ? ORDER BY sample_id DESC LIMIT ?",
                (status, limit),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            for row in rows:
                try:
                    row["entities"] = json.loads(row.get("entities", "[]"))
                except Exception:
                    row["entities"] = []
            return rows

    def update_sample_status(self, sample_id: int, status: str, correct_intent: str = None, correct_entities: List[Dict] = None) -> bool:
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            is_annotated = 1 if status == "annotated" else 0
            cursor.execute(
                "UPDATE learning_samples SET status = ?, is_annotated = ?, correct_intent = ?, correct_entities = ? WHERE sample_id = ?",
                (status, is_annotated, correct_intent, json.dumps(correct_entities or []), sample_id),
            )
            return cursor.rowcount > 0

    def get_sample_by_id(self, sample_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM learning_samples WHERE sample_id = ?", (sample_id,))
            row = cursor.fetchone()
            if not row:
                return None
            row = dict(row)
            try:
                row["entities"] = json.loads(row.get("entities", "[]"))
            except Exception:
                row["entities"] = []
            try:
                row["correct_entities"] = json.loads(row.get("correct_entities", "[]"))
            except Exception:
                row["correct_entities"] = []
            return row

    # ========== 通用 DAL 兼容方法 ==========
    def get_intent_by_id(self, intent_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM intents WHERE intent_id = ?", (intent_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_intents(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM intents ORDER BY level, priority DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_child_intents(self, parent_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM intents WHERE parent_id = ?", (parent_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_entity_by_id(self, entity_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entity_types WHERE entity_id = ?", (entity_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_entity_by_type(self, entity_type: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entity_types WHERE entity_type = ?", (entity_type,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_emotion_by_id(self, emotion_id: int) -> Optional[Dict[str, Any]]:
        return None

    def get_all_entities(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entity_types ORDER BY entity_name")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_keywords(self, type: Optional[str] = None, relation_id: Optional[int] = None) -> List[Dict[str, Any]]:
        # 简化实现
        return []

    def get_keyword_by_text_and_relation(self, keyword: str, type: str, relation_id: int) -> Optional[Dict[str, Any]]:
        return None

    def add_keyword(self, keyword: str, type: str, relation_id: int, weight: float, is_enabled: int, description: str = "") -> int:
        return -1

    def update_keyword_weight(self, keyword_id: int, weight: float) -> bool:
        return False

    def update_keyword(self, keyword_id: int, keyword: str, type: str, relation_id: int, weight: float, is_enabled: int, description: str = "") -> bool:
        return False

    def delete_keyword(self, keyword_id: int) -> bool:
        return False

    def add_intent(self, intent_code: str, intent_name: str, parent_id: int, level: int, priority: int, is_enabled: int, description: str = "") -> int:
        with self.get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO intents (intent_code, intent_name, parent_id, level, priority, is_enabled, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (intent_code, intent_name, parent_id, level, priority, is_enabled, description),
            )
            return cursor.lastrowid

    def update_intent(self, intent_id: int, intent_code: str = None, intent_name: str = None, parent_id: int = None, level: int = None, priority: int = None, is_enabled: int = None, description: str = None) -> bool:
        return False

    def delete_intent(self, intent_id: int) -> bool:
        return False

    def _load_intent_cache(self):
        pass


# 全局单例实例
bionic_db = BionicDB()
