#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准行业Schema导入工具
仅支持格式：标准JSON schema（包含意图、实体、映射关系）
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# 添加上层目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger()

class IndustrySchemaImporter:
    def __init__(self, industry_code: str = "default", tenant_id: str = "", is_builtin: int = 1):
        self.industry_code = industry_code
        self.tenant_id = tenant_id
        self.is_builtin = is_builtin
        # 初始化数据库连接
        from src.config.loader import get_global_config
        from src.adapter.dal.sqlite_dal import SQLiteDAL
        global_config = get_global_config()
        self.db = SQLiteDAL(global_config["database"]["sqlite_path"])
    
    def import_schema(self, schema_path: str) -> bool:
        """导入标准行业schema JSON文件"""
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            
            industry_name = schema.get("industry", self.industry_code)
            logger.info(f"开始导入{industry_name}行业Schema...")
            
            # 1. 导入意图
            intents = schema.get("intents", {})
            intent_count = 0
            intent_code_map = {}  # 存储短编码到全编码的映射
            for intent_code, intent_info in intents.items():
                full_intent_code = f"intent_{self.industry_code}_{intent_code}"
                intent_code_map[intent_code] = full_intent_code
                intent_data = {
                    "intent_code": full_intent_code,
                    "intent_name": intent_info["name"],
                    "intent_level": 2,
                    "parent_id": 0,  # 默认父级为0，后续可以关联到通用顶层意图
                    "priority": 300 + intent_count * 10,
                    "description": intent_info.get("desc", ""),
                    "is_active": 1,
                    "is_builtin": self.is_builtin
                }
                self._insert_intent(intent_data)
                intent_count += 1
            
            logger.info(f"导入意图完成，共{intent_count}个意图")
            
            # 2. 导入实体类型、实体值和关键词
            entities = schema.get("entities", {})
            entity_count = 0
            value_count = 0
            keyword_count = 0
            for entity_code, entity_info in entities.items():
                full_entity_code = f"entity_{self.industry_code}_{entity_code}"
                entity_data = {
                    "entity_code": full_entity_code,
                    "entity_name": entity_info["desc"],
                    "entity_type": "enum",
                    "description": entity_info.get("desc", ""),
                    "is_builtin": self.is_builtin
                }
                self._insert_entity_type(entity_data)
                entity_count += 1
                
                # 导入实体值和关键词
                values = entity_info.get("values", [])
                for val in values:
                    self._insert_entity_value(full_entity_code, val)
                    self._insert_entity_keyword(full_entity_code, val)
                    value_count += 1
                    keyword_count += 1
            
            logger.info(f"导入实体完成，共{entity_count}个实体类型，{value_count}个实体值，{keyword_count}个关键词")
            
            # 3. 导入意图-实体关联映射
            mapping = schema.get("intent_entity_mapping", {})
            mapping_count = 0
            for intent_code, entity_codes in mapping.items():
                full_intent_code = intent_code_map.get(intent_code, f"intent_{self.industry_code}_{intent_code}")
                for entity_code in entity_codes:
                    full_entity_code = f"entity_{self.industry_code}_{entity_code}"
                    self._insert_intent_entity_mapping(full_intent_code, full_entity_code)
                    mapping_count += 1
            
            logger.info(f"导入意图实体映射完成，共{mapping_count}条关联规则")
            
            # 4. 导入标注样本（如果有对话数据）
            labeled_data_path = schema_path.replace("_schema.json", "_conversation_labeled.json")
            if os.path.exists(labeled_data_path):
                self.import_labeled_data(labeled_data_path)
            
            logger.info(f"✅ {industry_name}行业Schema导入完成！")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导入Schema失败: {str(e)}", exc_info=True)
            return False
    
    def import_labeled_data(self, data_path: str) -> bool:
        """导入标注对话数据（用于训练和测试）"""
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            conversations = data.get("data", [])
            logger.info(f"开始导入标注对话数据，共{len(conversations)}条...")
            
            # 统计信息
            intent_stats = {}
            entity_stats = {}
            for conv in conversations:
                for intent in conv.get("intents", []):
                    intent_stats[intent] = intent_stats.get(intent, 0) + 1
                for entity in conv.get("entities", []):
                    entity_stats[entity["type"]] = entity_stats.get(entity["type"], 0) + 1
            
            logger.info(f"标注数据统计：意图覆盖{len(intent_stats)}类，实体覆盖{len(entity_stats)}类")
            # 后续可以将标注数据导入学习样本表
            return True
            
        except Exception as e:
            logger.error(f"导入标注数据失败: {str(e)}")
            return False
    
    def _insert_intent(self, intent_data: Dict[str, Any]) -> int:
        """插入意图，返回自增ID"""
        try:
            exists = self.db.execute_query(
                "SELECT intent_id, intent_code FROM intents WHERE intent_code = ?",
                (intent_data["intent_code"],)
            )
            
            if exists:
                sql = """
                UPDATE intents SET
                    intent_name = ?, level = ?, parent_id = ?, priority = ?,
                    description = ?, is_enabled = ?, is_builtin = ?,
                    industry_code = ?, tenant_id = ?,
                    update_time = CURRENT_TIMESTAMP
                WHERE intent_code = ?
                """
                params = (
                    intent_data["intent_name"], intent_data["intent_level"],
                    intent_data.get("parent_id", 0), intent_data["priority"],
                    intent_data["description"], intent_data["is_active"],
                    intent_data["is_builtin"], self.industry_code, self.tenant_id,
                    intent_data["intent_code"]
                )
                self.db.execute_update(sql, params)
                return exists[0]["intent_id"]
            else:
                sql = """
                INSERT INTO intents (
                    intent_code, intent_name, level, parent_id, priority,
                    description, is_enabled, is_builtin, industry_code, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    intent_data["intent_code"], intent_data["intent_name"],
                    intent_data["intent_level"], intent_data.get("parent_id", 0),
                    intent_data["priority"], intent_data["description"],
                    intent_data["is_active"], intent_data["is_builtin"],
                    self.industry_code, self.tenant_id
                )
                self.db.execute_update(sql, params)
                # 获取自增ID
                return self.db.execute_query("SELECT last_insert_rowid() as id")[0]["id"]
            
        except Exception as e:
            logger.warning(f"插入意图失败: {intent_data.get('intent_code')}, 错误: {str(e)}")
            return 0
    
    def _insert_entity_type(self, entity_data: Dict[str, Any]) -> bool:
        """插入实体类型"""
        try:
            exists = self.db.execute_query(
                "SELECT entity_code FROM entity_types WHERE entity_code = ?",
                (entity_data["entity_code"],)
            )
            
            if exists:
                sql = """
                UPDATE entity_types SET
                    entity_name = ?, entity_type = ?, extract_pattern = ?, description = ?, is_builtin = ?,
                    industry_code = ?, tenant_id = ?,
                    update_time = CURRENT_TIMESTAMP
                WHERE entity_code = ?
                """
                params = (
                    entity_data["entity_name"], entity_data["entity_type"],
                    entity_data.get("extract_pattern", ""), entity_data["description"],
                    entity_data["is_builtin"], self.industry_code, self.tenant_id,
                    entity_data["entity_code"]
                )
            else:
                sql = """
                INSERT INTO entity_types (
                    entity_code, entity_name, entity_type, extract_pattern, description,
                    is_builtin, industry_code, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    entity_data["entity_code"], entity_data["entity_name"],
                    entity_data["entity_type"], entity_data.get("extract_pattern", ""),
                    entity_data["description"], entity_data["is_builtin"],
                    self.industry_code, self.tenant_id
                )
            
            self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            logger.warning(f"插入实体类型失败: {entity_data.get('entity_code')}, 错误: {str(e)}")
            return False
    
    def _insert_entity_value(self, entity_code: str, value: str, weight: float = 1.0) -> bool:
        """插入实体值"""
        try:
            exists = self.db.execute_query(
                "SELECT id FROM entity_values WHERE entity_code = ? AND value = ?",
                (entity_code, value)
            )
            
            if not exists:
                sql = """
                INSERT INTO entity_values (entity_code, value, weight, is_enabled)
                VALUES (?, ?, ?, 1)
                """
                params = (entity_code, value, weight)
                self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            logger.debug(f"插入实体值失败: {value}, 错误: {str(e)}")
            return False
    
    def _insert_entity_keyword(self, entity_code: str, keyword: str, weight: float = 1.0) -> bool:
        """插入实体关键词"""
        try:
            exists = self.db.execute_query(
                "SELECT id FROM entity_keywords WHERE entity_code = ? AND keyword = ?",
                (entity_code, keyword)
            )
            
            if not exists:
                sql = """
                INSERT INTO entity_keywords (entity_code, keyword, weight, is_enabled)
                VALUES (?, ?, ?, 1)
                """
                params = (entity_code, keyword, weight)
                self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            logger.debug(f"插入关键词失败: {keyword}, 错误: {str(e)}")
            return False
    
    def _insert_intent_entity_mapping(self, intent_code: str, entity_code: str, is_required: int = 0, priority: int = 10) -> bool:
        """插入意图-实体关联映射"""
        try:
            exists = self.db.execute_query(
                "SELECT id FROM intent_entity_mapping WHERE intent_code = ? AND entity_code = ?",
                (intent_code, entity_code)
            )
            
            if not exists:
                sql = """
                INSERT INTO intent_entity_mapping (intent_code, entity_code, is_required, priority)
                VALUES (?, ?, ?, ?)
                """
                params = (intent_code, entity_code, is_required, priority)
                self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            logger.debug(f"插入意图实体映射失败: {intent_code}->{entity_code}, 错误: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description="标准行业Schema导入工具")
    parser.add_argument("--industry", "-i", required=True, help="行业编码，如rental、weather")
    parser.add_argument("--tenant", "-t", default="", help="租户ID，单租户可不填")
    parser.add_argument("--input", "-f", required=True, help="输入Schema JSON文件路径")
    parser.add_argument("--builtin", "-b", type=int, default=1, help="是否内置数据，默认1")
    
    args = parser.parse_args()
    
    importer = IndustrySchemaImporter(
        industry_code=args.industry,
        tenant_id=args.tenant,
        is_builtin=args.builtin
    )
    
    success = importer.import_schema(args.input)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()