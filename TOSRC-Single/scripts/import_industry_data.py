#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用行业数据导入器
自动扫描industry_data目录下所有JSON文件，统一导入意图和实体数据
支持系统启动时自动调用，支持多行业隔离扩展
符合TOSRC编码规范：自动添加行业前缀，支持多行业隔离
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

class IndustryDataImporter:
    """通用行业数据导入器"""
    
    def __init__(self, db=None):
        """初始化导入器，如果不传db则自动创建连接"""
        if db:
            self.db = db
        else:
            global_config = get_global_config()
            self.db = SQLiteDAL(global_config["database"]["sqlite_path"])
    
    def import_all(self, industry_data_dir: str = "data/industry_data") -> bool:
        """导入industry_data目录下所有行业数据文件"""
        try:
            if not os.path.exists(industry_data_dir):
                logger.warning(f"行业数据目录不存在: {industry_data_dir}，跳过导入")
                return True
            
            # 扫描所有JSON文件
            json_files = [f for f in os.listdir(industry_data_dir) if f.endswith(".json")]
            logger.info(f"发现行业数据文件: {len(json_files)}个")
            
            total_success = 0
            for file_name in json_files:
                file_path = os.path.join(industry_data_dir, file_name)
                success = self.import_single_file(file_path)
                if success:
                    total_success += 1
            
            logger.info(f"✅ 所有行业数据导入完成，成功: {total_success}个，失败: {len(json_files) - total_success}个")
            return total_success == len(json_files)
            
        except Exception as e:
            logger.error(f"批量导入行业数据失败: {str(e)}", exc_info=True)
            return False
    
    def import_single_file(self, file_path: str) -> bool:
        """导入单个JSON文件，存在则跳过"""
        try:
            logger.info(f"开始处理文件: {os.path.basename(file_path)}")
            
            # 读取JSON数据
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 校验必填字段
            required_fields = ["industry", "industry_name", "type", "values"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"文件缺少必填字段[{field}]，跳过: {file_path}")
                    return False
            
            industry_code = data["industry"]
            industry_name = data["industry_name"]
            data_type = data["type"]
            values = data["values"]
            
            # 检查该行业该类型数据是否已经导入过
            exists = self._check_data_exists(industry_code, data_type)
            if exists:
                logger.info(f"行业[{industry_name}]的{data_type}数据已存在，跳过导入")
                return True
            
            logger.info(f"行业: {industry_name}({industry_code})，类型: {data_type}，数据: {len(values)}条")
            
            # 开启事务
            self.db.begin_transaction()
            
            if data_type == "intent":
                success = self._import_intent_data(industry_code, values)
            elif data_type == "entity":
                success = self._import_entity_data(industry_code, values)
            else:
                logger.error(f"不支持的数据类型: {data_type}，跳过")
                self.db.rollback_transaction()
                return False
            
            if success:
                self.db.commit_transaction()
                logger.info(f"✅ 文件导入成功: {os.path.basename(file_path)}")
                return True
            else:
                self.db.rollback_transaction()
                logger.error(f"❌ 文件导入失败: {os.path.basename(file_path)}")
                return False
                
        except Exception as e:
            self.db.rollback_transaction()
            logger.error(f"导入文件失败: {file_path}, 错误: {str(e)}", exc_info=True)
            return False
    
    def _check_data_exists(self, industry_code: str, data_type: str) -> bool:
        """检查该行业该类型数据是否已经导入过"""
        try:
            if data_type == "intent":
                # 检查是否有该行业的意图
                result = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM intents WHERE industry_code = ? LIMIT 1",
                    (industry_code,)
                )
                return result[0]["count"] > 0
            elif data_type == "entity":
                # 检查是否有该行业的实体类型
                result = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM entity_types WHERE industry_code = ? LIMIT 1",
                    (industry_code,)
                )
                return result[0]["count"] > 0
            return False
        except Exception as e:
            logger.debug(f"检查数据存在性失败: {str(e)}")
            return False
    
    def _import_intent_data(self, industry_code: str, intent_data: List[Dict[str, Any]]) -> bool:
        """导入意图数据"""
        try:
            top_priority = 1000  # 一级意图优先级从1000开始递减
            total_count = 0
            
            for top_intent in intent_data:
                top_code = top_intent["top_code"]
                top_name = top_intent["top_name"]
                second_values = top_intent.get("second_values", [])
                
                # 插入一级意图
                top_full_code = f"{industry_code}_{top_code}"
                top_id = self._insert_or_update_intent({
                    "intent_code": top_full_code,
                    "intent_name": top_name,
                    "level": 1,
                    "parent_id": 0,
                    "priority": top_priority,
                    "description": f"{industry_code}行业一级意图：{top_name}",
                    "is_enabled": 1,
                    "is_builtin": 1,
                    "industry_code": industry_code
                })
                
                if not top_id:
                    logger.warning(f"插入一级意图失败: {top_code} - {top_name}")
                    continue
                
                total_count += 1
                logger.debug(f"导入一级意图: {top_name}({top_full_code})，ID: {top_id}")
                
                # 插入二级意图
                sub_priority = top_priority - 5
                for sub_item in second_values:
                    sub_code = sub_item["code"]
                    sub_name = sub_item["name"]
                    sub_full_code = f"{industry_code}_{sub_code}"
                    
                    sub_id = self._insert_or_update_intent({
                        "intent_code": sub_full_code,
                        "intent_name": sub_name,
                        "level": 2,
                        "parent_id": top_id,
                        "priority": sub_priority,
                        "description": f"{industry_code}行业二级意图：{sub_name}，隶属于{top_name}",
                        "is_enabled": 1,
                        "is_builtin": 1,
                        "industry_code": industry_code
                    })
                    
                    if sub_id:
                        total_count += 1
                        logger.debug(f"  导入二级意图: {sub_name}({sub_full_code})")
                    else:
                        logger.warning(f"  插入二级意图失败: {sub_code}")
                    
                    sub_priority -= 2
                
                top_priority -= 10
            
            logger.info(f"意图导入完成，共导入{total_count}个意图")
            return True
            
        except Exception as e:
            logger.error(f"导入意图数据失败: {str(e)}", exc_info=True)
            return False
    
    def _import_entity_data(self, industry_code: str, entity_data: List[Dict[str, Any]]) -> bool:
        """导入实体数据"""
        try:
            total_entity_types = 0
            total_entity_values = 0
            
            for category in entity_data:
                category_code = category["top_code"]
                category_name = category["top_name"]
                second_values = category.get("second_values", [])
                
                logger.debug(f"处理分类: {category_name}，包含{len(second_values)}个实体类型")
                
                for entity in second_values:
                    entity_code = entity["code"]
                    entity_name = entity["name"]
                    definition = entity.get("definition", "")
                    typical_values = entity.get("values", [])
                    
                    # 导入实体类型
                    entity_full_code = f"{industry_code}_{entity_code}"
                    success = self._insert_or_update_entity_type({
                        "entity_code": entity_full_code,
                        "entity_name": entity_name,
                        "entity_type": "enum",
                        "description": definition,
                        "is_builtin": 1,
                        "industry_code": industry_code
                    })
                    
                    if success:
                        total_entity_types += 1
                        # 导入实体值
                        for val in typical_values:
                            val_success = self._insert_or_update_entity_value(entity_full_code, val)
                            if val_success:
                                total_entity_values += 1
            
            logger.info(f"实体导入完成，共导入实体类型: {total_entity_types}个，实体值: {total_entity_values}个")
            return True
            
        except Exception as e:
            logger.error(f"导入实体数据失败: {str(e)}", exc_info=True)
            return False
    
    def _insert_or_update_intent(self, intent_data: Dict[str, Any]) -> int:
        """插入或更新意图，返回意图ID"""
        try:
            exists = self.db.execute_query(
                "SELECT intent_id FROM intents WHERE intent_code = ?",
                (intent_data["intent_code"],)
            )
            
            if exists:
                # 更新
                sql = """
                UPDATE intents SET
                    intent_name = ?, level = ?, parent_id = ?, priority = ?,
                    description = ?, is_enabled = ?, is_builtin = ?,
                    industry_code = ?, update_time = CURRENT_TIMESTAMP
                WHERE intent_code = ?
                """
                params = (
                    intent_data["intent_name"], intent_data["level"], intent_data["parent_id"],
                    intent_data["priority"], intent_data["description"], intent_data["is_enabled"],
                    intent_data["is_builtin"], intent_data["industry_code"],
                    intent_data["intent_code"]
                )
                self.db.execute_update(sql, params)
                return exists[0]["intent_id"]
            else:
                # 插入
                sql = """
                INSERT INTO intents (
                    intent_code, intent_name, level, parent_id, priority, description,
                    is_enabled, is_builtin, industry_code, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '')
                """
                params = (
                    intent_data["intent_code"], intent_data["intent_name"], intent_data["level"],
                    intent_data["parent_id"], intent_data["priority"], intent_data["description"],
                    intent_data["is_enabled"], intent_data["is_builtin"], intent_data["industry_code"]
                )
                return self.db.execute_update(sql, params)
                
        except Exception as e:
            logger.debug(f"插入意图失败: {intent_data.get('intent_code')}, 错误: {str(e)}")
            return 0
    
    def _insert_or_update_entity_type(self, entity_data: Dict[str, Any]) -> bool:
        """插入或更新实体类型"""
        try:
            exists = self.db.execute_query(
                "SELECT entity_code FROM entity_types WHERE entity_code = ?",
                (entity_data["entity_code"],)
            )
            
            if exists:
                sql = """
                UPDATE entity_types SET
                    entity_name = ?, entity_type = ?, description = ?,
                    is_builtin = ?, industry_code = ?, update_time = CURRENT_TIMESTAMP
                WHERE entity_code = ?
                """
                params = (
                    entity_data["entity_name"], entity_data["entity_type"],
                    entity_data["description"], entity_data["is_builtin"],
                    entity_data["industry_code"], entity_data["entity_code"]
                )
            else:
                sql = """
                INSERT INTO entity_types (
                    entity_code, entity_name, entity_type, description,
                    is_builtin, industry_code, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?, '')
                """
                params = (
                    entity_data["entity_code"], entity_data["entity_name"],
                    entity_data["entity_type"], entity_data["description"],
                    entity_data["is_builtin"], entity_data["industry_code"]
                )
            
            self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            logger.debug(f"插入实体类型失败: {entity_data.get('entity_code')}, 错误: {str(e)}")
            return False
    
    def _insert_or_update_entity_value(self, entity_code: str, value: str) -> bool:
        """插入或更新实体值"""
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
            logger.debug(f"插入实体值失败: {value}, 错误: {str(e)}")
            return False
    


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="TOSRC 行业数据统一导入工具")
    parser.add_argument("--dir", "-d", default="data/industry_data", help="行业数据目录路径")
    parser.add_argument("--file", "-f", help="单个导入文件路径（可选，指定时只导入单个文件）")
    
    args = parser.parse_args()
    
    importer = IndustryDataImporter()
    
    if args.file:
        success = importer.import_single_file(args.file)
    else:
        success = importer.import_all(args.dir)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()