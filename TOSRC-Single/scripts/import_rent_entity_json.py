#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
租房行业实体JSON导入工具
从标准实体JSON文件批量导入实体类型和实体值
"""
import os
import sys
import json
from typing import List, Dict, Any
from pathlib import Path

# 添加上层目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.config.loader import get_global_config
from src.adapter.dal.sqlite_dal import SQLiteDAL

logger = get_logger()

class RentEntityImporter:
    """租房行业实体导入器"""
    
    def __init__(self, industry_code: str = "rental"):
        self.industry_code = industry_code
        self.db = SQLiteDAL(get_global_config()["database"]["sqlite_path"])
    
    def import_from_json(self, json_path: str) -> bool:
        """从实体JSON文件导入"""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            categories = data.get("entity_system", {}).get("entity_categories", [])
            logger.info(f"开始导入租房行业实体，共{len(categories)}个分类")
            
            # 开启事务
            self.db.begin_transaction()
            
            total_entity_types = 0
            total_entity_values = 0
            
            for category in categories:
                category_code = category["category_code"]
                category_name = category["category_name"]
                entities = category.get("entities", [])
                
                logger.info(f"处理分类: {category_name}，包含{len(entities)}个实体类型")
                
                for entity in entities:
                    entity_code = entity["entity_code"]
                    entity_name = entity["entity_name"]
                    definition = entity.get("definition", "")
                    typical_values = entity.get("typical_values", [])
                    
                    # 导入实体类型
                    entity_type_code = f"{self.industry_code}_{entity_code}"
                    success = self._import_entity_type({
                        "entity_code": entity_type_code,
                        "entity_name": entity_name,
                        "entity_type": "enum",
                        "description": definition
                    })
                    
                    if success:
                        total_entity_types += 1
                        # 导入实体值
                        for val in typical_values:
                            val_success = self._import_entity_value(entity_type_code, val)
                            if val_success:
                                total_entity_values += 1
            
            self.db.commit_transaction()
            logger.info(f"✅ 实体导入完成，共导入实体类型: {total_entity_types}个，实体值: {total_entity_values}个")
            return True
            
        except Exception as e:
            self.db.rollback_transaction()
            logger.error(f"导入失败，事务回滚: {str(e)}", exc_info=True)
            return False
    
    def _import_entity_type(self, entity_data: Dict[str, Any]) -> bool:
        """导入单个实体类型"""
        try:
            exists = self.db.execute_query(
                "SELECT entity_code FROM entity_types WHERE entity_code = ?",
                (entity_data["entity_code"],)
            )
            
            if exists:
                sql = """
                UPDATE entity_types SET
                    entity_name = ?, entity_type = ?, description = ?,
                    industry_code = ?, update_time = CURRENT_TIMESTAMP
                WHERE entity_code = ?
                """
                params = (
                    entity_data["entity_name"], entity_data["entity_type"],
                    entity_data["description"], self.industry_code,
                    entity_data["entity_code"]
                )
            else:
                sql = """
                INSERT INTO entity_types (
                    entity_code, entity_name, entity_type, description,
                    is_builtin, industry_code, tenant_id
                ) VALUES (?, ?, ?, ?, 1, ?, '')
                """
                params = (
                    entity_data["entity_code"], entity_data["entity_name"],
                    entity_data["entity_type"], entity_data["description"],
                    self.industry_code
                )
            
            self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            logger.debug(f"导入实体类型失败: {entity_data.get('entity_code')}, 错误: {str(e)}")
            return False
    
    def _import_entity_value(self, entity_code: str, value: str) -> bool:
        """导入单个实体值"""
        try:
            exists = self.db.execute_query(
                "SELECT id FROM entity_values WHERE entity_code = ? AND value = ?",
                (entity_code, value)
            )
            
            if not exists:
                sql = """
                INSERT INTO entity_values (entity_code, value, weight, is_enabled)
                VALUES (?, ?, 1.0, 1)
                """
                self.db.execute_update(sql, (entity_code, value))
            return True
            
        except Exception as e:
            logger.debug(f"导入实体值失败: {value}, 错误: {str(e)}")
            return False

def main():
    importer = RentEntityImporter(industry_code="rental")
    json_path = "/Volumes/1T/ai_project/ai-llm-router/data/租房行业/租房行业实体.json"
    importer.import_from_json(json_path)

if __name__ == "__main__":
    main()