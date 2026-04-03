#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量CSV导入工具
支持导入：意图、实体类型、实体值、实体关键词、意图-实体关联
完全适配之前定义的CSV格式规范
"""
import os
import sys
import csv
import argparse
from typing import List, Dict, Any
from pathlib import Path

# 添加上层目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.config.loader import get_global_config
from src.adapter.dal.sqlite_dal import SQLiteDAL

logger = get_logger()

class CSVBatchImporter:
    """CSV批量导入器"""
    
    def __init__(self, industry_code: str = "default", tenant_id: str = "", is_builtin: int = 1):
        self.industry_code = industry_code
        self.tenant_id = tenant_id
        self.is_builtin = is_builtin
        
        # 初始化数据库连接
        global_config = get_global_config()
        self.db = SQLiteDAL(global_config["database"]["sqlite_path"])
    
    def import_file(self, import_type: str, csv_path: str) -> bool:
        """
        导入CSV文件
        :param import_type: 导入类型：intent/entity_type/entity_value/entity_keyword/intent_mapping
        :param csv_path: CSV文件路径
        :return: 导入是否成功
        """
        if not os.path.exists(csv_path):
            logger.error(f"CSV文件不存在: {csv_path}")
            return False
        
        # 读取CSV文件
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            logger.error(f"读取CSV文件失败: {str(e)}")
            return False
        
        if not rows:
            logger.warning("CSV文件为空，跳过导入")
            return True
        
        logger.info(f"开始导入{import_type}，共{len(rows)}条数据")
        
        # 根据类型分发处理
        import_handlers = {
            "intent": self._import_intents,
            "entity_type": self._import_entity_types,
            "entity_value": self._import_entity_values,
            "entity_keyword": self._import_entity_keywords,
            "intent_mapping": self._import_intent_mapping
        }
        
        if import_type not in import_handlers:
            logger.error(f"不支持的导入类型: {import_type}")
            logger.info(f"支持的类型: {list(import_handlers.keys())}")
            return False
        
        success_count = import_handlers[import_type](rows)
        logger.info(f"导入完成，成功: {success_count}条，失败: {len(rows) - success_count}条")
        
        return success_count == len(rows)
    
    def _import_intents(self, rows: List[Dict[str, Any]]) -> int:
        """导入意图数据"""
        success = 0
        required_fields = ["intent_code", "intent_name", "level", "parent_id", "priority"]
        
        for row in rows:
            try:
                # 校验必填字段
                for field in required_fields:
                    if field not in row or not row[field].strip():
                        logger.warning(f"缺少必填字段[{field}]，跳过: {row}")
                        continue
                
                # 构建数据
                intent_data = {
                    "intent_code": f"{self.industry_code}_{row['intent_code'].strip()}" if self.industry_code else row['intent_code'].strip(),
                    "intent_name": row['intent_name'].strip(),
                    "level": int(row['level'].strip()),
                    "parent_id": int(row['parent_id'].strip()),
                    "priority": int(row['priority'].strip()),
                    "description": row.get('description', '').strip(),
                    "is_enabled": int(row.get('is_enabled', '1').strip()),
                    "is_builtin": self.is_builtin,
                    "industry_code": self.industry_code,
                    "tenant_id": self.tenant_id
                }
                
                # 检查是否已存在
                exists = self.db.execute_query(
                    "SELECT intent_code FROM intents WHERE intent_code = ?",
                    (intent_data["intent_code"],)
                )
                
                if exists:
                    # 更新
                    sql = """
                    UPDATE intents SET
                        intent_name = ?, level = ?, parent_id = ?, priority = ?,
                        description = ?, is_enabled = ?, is_builtin = ?,
                        industry_code = ?, tenant_id = ?,
                        update_time = CURRENT_TIMESTAMP
                    WHERE intent_code = ?
                    """
                    params = (
                        intent_data["intent_name"], intent_data["level"], intent_data["parent_id"],
                        intent_data["priority"], intent_data["description"], intent_data["is_enabled"],
                        intent_data["is_builtin"], intent_data["industry_code"], intent_data["tenant_id"],
                        intent_data["intent_code"]
                    )
                else:
                    # 插入
                    sql = """
                    INSERT INTO intents (
                        intent_code, intent_name, level, parent_id, priority, description,
                        is_enabled, is_builtin, industry_code, tenant_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        intent_data["intent_code"], intent_data["intent_name"], intent_data["level"],
                        intent_data["parent_id"], intent_data["priority"], intent_data["description"],
                        intent_data["is_enabled"], intent_data["is_builtin"],
                        intent_data["industry_code"], intent_data["tenant_id"]
                    )
                
                self.db.execute_update(sql, params)
                success += 1
                logger.debug(f"导入意图成功: {intent_data['intent_code']} - {intent_data['intent_name']}")
                
            except Exception as e:
                logger.warning(f"导入意图失败: {row}, 错误: {str(e)}")
                continue
        
        return success
    
    def _import_entity_types(self, rows: List[Dict[str, Any]]) -> int:
        """导入实体类型数据"""
        success = 0
        required_fields = ["entity_code", "entity_name", "entity_type"]
        
        for row in rows:
            try:
                for field in required_fields:
                    if field not in row or not row[field].strip():
                        logger.warning(f"缺少必填字段[{field}]，跳过: {row}")
                        continue
                
                entity_data = {
                    "entity_code": f"{self.industry_code}_{row['entity_code'].strip()}" if self.industry_code else row['entity_code'].strip(),
                    "entity_name": row['entity_name'].strip(),
                    "entity_type": row['entity_type'].strip(),
                    "extract_pattern": row.get('extract_pattern', '').strip(),
                    "description": row.get('description', '').strip(),
                    "is_builtin": self.is_builtin,
                    "industry_code": self.industry_code,
                    "tenant_id": self.tenant_id
                }
                
                exists = self.db.execute_query(
                    "SELECT entity_code FROM entity_types WHERE entity_code = ?",
                    (entity_data["entity_code"],)
                )
                
                if exists:
                    sql = """
                    UPDATE entity_types SET
                        entity_name = ?, entity_type = ?, extract_pattern = ?,
                        description = ?, is_builtin = ?, industry_code = ?,
                        tenant_id = ?, update_time = CURRENT_TIMESTAMP
                    WHERE entity_code = ?
                    """
                    params = (
                        entity_data["entity_name"], entity_data["entity_type"],
                        entity_data["extract_pattern"], entity_data["description"],
                        entity_data["is_builtin"], entity_data["industry_code"],
                        entity_data["tenant_id"], entity_data["entity_code"]
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
                        entity_data["entity_type"], entity_data["extract_pattern"],
                        entity_data["description"], entity_data["is_builtin"],
                        entity_data["industry_code"], entity_data["tenant_id"]
                    )
                
                self.db.execute_update(sql, params)
                success += 1
                logger.debug(f"导入实体类型成功: {entity_data['entity_code']} - {entity_data['entity_name']}")
                
            except Exception as e:
                logger.warning(f"导入实体类型失败: {row}, 错误: {str(e)}")
                continue
        
        return success
    
    def _import_entity_values(self, rows: List[Dict[str, Any]]) -> int:
        """导入实体值数据"""
        success = 0
        required_fields = ["entity_code", "value"]
        
        for row in rows:
            try:
                for field in required_fields:
                    if field not in row or not row[field].strip():
                        logger.warning(f"缺少必填字段[{field}]，跳过: {row}")
                        continue
                
                entity_code = f"{self.industry_code}_{row['entity_code'].strip()}" if self.industry_code else row['entity_code'].strip()
                value = row['value'].strip()
                
                # 检查实体类型是否存在
                entity_exists = self.db.execute_query(
                    "SELECT entity_code FROM entity_types WHERE entity_code = ?",
                    (entity_code,)
                )
                if not entity_exists:
                    logger.warning(f"实体类型不存在，跳过: {entity_code}")
                    continue
                
                value_data = {
                    "entity_code": entity_code,
                    "value": value,
                    "alias": row.get('alias', '').strip(),
                    "weight": float(row.get('weight', '1.0').strip()),
                    "is_enabled": int(row.get('is_enabled', '1').strip())
                }
                
                exists = self.db.execute_query(
                    "SELECT id FROM entity_values WHERE entity_code = ? AND value = ?",
                    (value_data["entity_code"], value_data["value"])
                )
                
                if exists:
                    sql = """
                    UPDATE entity_values SET
                        alias = ?, weight = ?, is_enabled = ?
                    WHERE entity_code = ? AND value = ?
                    """
                    params = (
                        value_data["alias"], value_data["weight"], value_data["is_enabled"],
                        value_data["entity_code"], value_data["value"]
                    )
                else:
                    sql = """
                    INSERT INTO entity_values (
                        entity_code, value, alias, weight, is_enabled
                    ) VALUES (?, ?, ?, ?, ?)
                    """
                    params = (
                        value_data["entity_code"], value_data["value"],
                        value_data["alias"], value_data["weight"], value_data["is_enabled"]
                    )
                
                self.db.execute_update(sql, params)
                success += 1
                logger.debug(f"导入实体值成功: {entity_code} - {value}")
                
            except Exception as e:
                logger.warning(f"导入实体值失败: {row}, 错误: {str(e)}")
                continue
        
        return success
    
    def _import_entity_keywords(self, rows: List[Dict[str, Any]]) -> int:
        """导入实体关键词数据"""
        success = 0
        required_fields = ["entity_code", "keyword"]
        
        for row in rows:
            try:
                for field in required_fields:
                    if field not in row or not row[field].strip():
                        logger.warning(f"缺少必填字段[{field}]，跳过: {row}")
                        continue
                
                entity_code = f"{self.industry_code}_{row['entity_code'].strip()}" if self.industry_code else row['entity_code'].strip()
                keyword = row['keyword'].strip()
                
                # 检查实体类型是否存在
                entity_exists = self.db.execute_query(
                    "SELECT entity_code FROM entity_types WHERE entity_code = ?",
                    (entity_code,)
                )
                if not entity_exists:
                    logger.warning(f"实体类型不存在，跳过: {entity_code}")
                    continue
                
                keyword_data = {
                    "entity_code": entity_code,
                    "keyword": keyword,
                    "weight": float(row.get('weight', '1.0').strip()),
                    "is_enabled": int(row.get('is_enabled', '1').strip())
                }
                
                exists = self.db.execute_query(
                    "SELECT id FROM entity_keywords WHERE entity_code = ? AND keyword = ?",
                    (keyword_data["entity_code"], keyword_data["keyword"])
                )
                
                if exists:
                    sql = """
                    UPDATE entity_keywords SET
                        weight = ?, is_enabled = ?
                    WHERE entity_code = ? AND keyword = ?
                    """
                    params = (
                        keyword_data["weight"], keyword_data["is_enabled"],
                        keyword_data["entity_code"], keyword_data["keyword"]
                    )
                else:
                    sql = """
                    INSERT INTO entity_keywords (
                        entity_code, keyword, weight, is_enabled
                    ) VALUES (?, ?, ?, ?)
                    """
                    params = (
                        keyword_data["entity_code"], keyword_data["keyword"],
                        keyword_data["weight"], keyword_data["is_enabled"]
                    )
                
                self.db.execute_update(sql, params)
                success += 1
                logger.debug(f"导入实体关键词成功: {entity_code} - {keyword}")
                
            except Exception as e:
                logger.warning(f"导入实体关键词失败: {row}, 错误: {str(e)}")
                continue
        
        return success
    
    def _import_intent_mapping(self, rows: List[Dict[str, Any]]) -> int:
        """导入意图-实体关联数据"""
        success = 0
        required_fields = ["intent_code", "entity_code"]
        
        for row in rows:
            try:
                for field in required_fields:
                    if field not in row or not row[field].strip():
                        logger.warning(f"缺少必填字段[{field}]，跳过: {row}")
                        continue
                
                intent_code = f"{self.industry_code}_{row['intent_code'].strip()}" if self.industry_code else row['intent_code'].strip()
                entity_code = f"{self.industry_code}_{row['entity_code'].strip()}" if self.industry_code else row['entity_code'].strip()
                
                # 检查意图和实体是否存在
                intent_exists = self.db.execute_query(
                    "SELECT intent_code FROM intents WHERE intent_code = ?",
                    (intent_code,)
                )
                entity_exists = self.db.execute_query(
                    "SELECT entity_code FROM entity_types WHERE entity_code = ?",
                    (entity_code,)
                )
                
                if not intent_exists:
                    logger.warning(f"意图不存在，跳过: {intent_code}")
                    continue
                if not entity_exists:
                    logger.warning(f"实体类型不存在，跳过: {entity_code}")
                    continue
                
                mapping_data = {
                    "intent_code": intent_code,
                    "entity_code": entity_code,
                    "is_required": int(row.get('is_required', '0').strip()),
                    "priority": int(row.get('priority', '10').strip())
                }
                
                exists = self.db.execute_query(
                    "SELECT id FROM intent_entity_mapping WHERE intent_code = ? AND entity_code = ?",
                    (mapping_data["intent_code"], mapping_data["entity_code"])
                )
                
                if exists:
                    sql = """
                    UPDATE intent_entity_mapping SET
                        is_required = ?, priority = ?
                    WHERE intent_code = ? AND entity_code = ?
                    """
                    params = (
                        mapping_data["is_required"], mapping_data["priority"],
                        mapping_data["intent_code"], mapping_data["entity_code"]
                    )
                else:
                    sql = """
                    INSERT INTO intent_entity_mapping (
                        intent_code, entity_code, is_required, priority
                    ) VALUES (?, ?, ?, ?)
                    """
                    params = (
                        mapping_data["intent_code"], mapping_data["entity_code"],
                        mapping_data["is_required"], mapping_data["priority"]
                    )
                
                self.db.execute_update(sql, params)
                success += 1
                logger.debug(f"导入意图实体关联成功: {intent_code} -> {entity_code}")
                
            except Exception as e:
                logger.warning(f"导入意图实体关联失败: {row}, 错误: {str(e)}")
                continue
        
        return success

def main():
    parser = argparse.ArgumentParser(description="TOSRC 批量CSV导入工具")
    parser.add_argument("--type", "-t", required=True, 
                        choices=["intent", "entity_type", "entity_value", "entity_keyword", "intent_mapping"],
                        help="导入类型")
    parser.add_argument("--input", "-f", required=True, help="CSV文件路径")
    parser.add_argument("--industry", "-i", default="", help="行业编码，导入时会自动添加到编码前缀")
    parser.add_argument("--tenant", "-tenant", default="", help="租户ID")
    parser.add_argument("--builtin", "-b", type=int, default=1, help="是否内置数据，默认1")
    
    args = parser.parse_args()
    
    importer = CSVBatchImporter(
        industry_code=args.industry,
        tenant_id=args.tenant,
        is_builtin=args.builtin
    )
    
    success = importer.import_file(args.type, args.input)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()