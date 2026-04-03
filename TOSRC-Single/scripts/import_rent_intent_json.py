#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
租房行业意图JSON导入工具
从标准JSON格式导入完整意图体系，自动关联父子层级
"""
import os
import sys
import json
from typing import Dict, Any
from pathlib import Path

# 添加上层目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.config.loader import get_global_config
from src.adapter.dal.sqlite_dal import SQLiteDAL
from src.utils.logger import get_logger

logger = get_logger()

class RentIntentImporter:
    """租房行业意图导入器"""
    
    def __init__(self, industry_code: str = "rental", tenant_id: str = "", is_builtin: int = 1):
        self.industry_code = industry_code
        self.tenant_id = tenant_id
        self.is_builtin = is_builtin
        
        # 初始化数据库连接
        global_config = get_global_config()
        self.db = SQLiteDAL(global_config["database"]["sqlite_path"])
    
    def import_from_json(self, json_path: str) -> bool:
        """从JSON文件导入意图"""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            intents_data = data.get("intents", [])
            logger.info(f"开始导入租房行业意图，共{len(intents_data)}个一级意图")
            
            # 开启事务
            self.db.begin_transaction()
            
            try:
                total_count = 0
                top_priority = 1000  # 一级意图优先级从1000开始递减
                
                for top_intent in intents_data:
                    top_code = top_intent["top_intent"]
                    top_name = top_intent["top_name"]
                    second_intents = top_intent["second_intents"]
                    
                    # 插入一级意图
                    top_id = self._insert_intent({
                        "intent_code": f"{self.industry_code}_{top_code.replace('intent_', '')}" if self.industry_code else top_code.replace('intent_', ''),
                        "intent_name": top_name,
                        "level": 1,
                        "parent_id": 0,
                        "priority": top_priority,
                        "description": f"租房行业一级意图：{top_name}",
                        "is_enabled": 1
                    })
                    
                    if not top_id:
                        logger.warning(f"插入一级意图失败: {top_code} - {top_name}")
                        continue
                    
                    total_count += 1
                    logger.info(f"✅ 导入一级意图: {top_name}({top_code})，ID: {top_id}")
                    
                    # 插入二级意图
                    sub_priority = top_priority - 5  # 二级意图优先级从一级减5开始递减
                    for sub_code in second_intents:
                        # 转换为友好名称
                        sub_name = self._code_to_name(sub_code)
                        sub_id = self._insert_intent({
                            "intent_code": f"{self.industry_code}_{sub_code.replace('intent_', '')}" if self.industry_code else sub_code.replace('intent_', ''),
                            "intent_name": sub_name,
                            "level": 2,
                            "parent_id": top_id,
                            "priority": sub_priority,
                            "description": f"租房行业二级意图：{sub_name}，隶属于{top_name}",
                            "is_enabled": 1
                        })
                        
                        if sub_id:
                            total_count += 1
                            logger.debug(f"  导入二级意图: {sub_name}({sub_code})，父级ID: {top_id}")
                        else:
                            logger.warning(f"  插入二级意图失败: {sub_code}")
                        
                        sub_priority -= 2
                    
                    top_priority -= 10  # 下一个一级意图优先级减10
                
                self.db.commit_transaction()
                logger.info(f"✅ 全部导入完成，共导入{total_count}个意图（{len(intents_data)}个一级，{total_count - len(intents_data)}个二级）")
                return True
                
            except Exception as e:
                self.db.rollback_transaction()
                logger.error(f"导入失败，事务回滚: {str(e)}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"读取JSON文件失败: {str(e)}", exc_info=True)
            return False
    
    def _insert_intent(self, intent_data: Dict[str, Any]) -> int:
        """插入单个意图，返回自增ID，存在则更新"""
        try:
            exists = self.db.execute_query(
                "SELECT intent_id, intent_code FROM intents WHERE intent_code = ?",
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
                    self.is_builtin, self.industry_code, self.tenant_id,
                    intent_data["intent_code"]
                )
                self.db.execute_update(sql, params)
                return exists[0]["intent_id"]
            else:
                # 插入
                sql = """
                INSERT INTO intents (
                    intent_code, intent_name, level, parent_id, priority,
                    description, is_enabled, is_builtin, industry_code, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    intent_data["intent_code"], intent_data["intent_name"], intent_data["level"],
                    intent_data["parent_id"], intent_data["priority"], intent_data["description"],
                    intent_data["is_enabled"], self.is_builtin, self.industry_code, self.tenant_id
                )
                self.db.execute_update(sql, params)
                # 获取自增ID
                return self.db.execute_query("SELECT last_insert_rowid() as id")[0]["id"]
            
        except Exception as e:
            logger.debug(f"插入意图失败: {intent_data.get('intent_code')}, 错误: {str(e)}")
            return 0
    
    def _code_to_name(self, code: str) -> str:
        """将下划线编码转换为友好中文名称"""
        # 移除前缀
        if code.startswith("rent_"):
            code = code[5:]
        elif code.startswith("other_"):
            code = code[6:]
        
        # 替换下划线为空格，大写首字母
        parts = code.split("_")
        return "".join([p.capitalize() for p in parts])

def main():
    importer = RentIntentImporter(industry_code="rental")
    json_path = "/Volumes/1T/ai_project/ai-llm-router/data/租房行业/租房行业意图.json"
    importer.import_from_json(json_path)

if __name__ == "__main__":
    main()