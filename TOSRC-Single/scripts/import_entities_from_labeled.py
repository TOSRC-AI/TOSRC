#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从标注对话数据批量导入实体值到数据库
"""
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.config.loader import get_global_config
from src.adapter.dal.sqlite_dal import SQLiteDAL

logger = get_logger()

def import_entities_from_labeled_data(json_path: str, industry_code: str = "rental"):
    """从标注数据导入实体值"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        db = SQLiteDAL(get_global_config()["database"]["sqlite_path"])
        # 实体类型映射，标注数据里的key对应数据库的实体编码
        entity_type_map = {
            "location": "rental_location",
            "house_type": "rental_house_type",
            "time": "rental_service_time",
            "quantity": "rental_price",
            "behavior": "rental_service_item",
            "feature": "rental_house_tag",
            "price": "rental_price",
            "pay_type": "rental_payment_method",
            "person": "rental_tenant"
        }
        
        total = 0
        for conv in data:
            entities = conv.get("entities", {})
            for entity_key, entity_value in entities.items():
                entity_code = entity_type_map.get(entity_key)
                if not entity_code:
                    continue
                
                # 检查是否已存在
                exists = db.execute_query(
                    "SELECT id FROM entity_values WHERE entity_code = ? AND value = ?",
                    (entity_code, entity_value)
                )
                if not exists:
                    # 插入实体值
                    db.execute_update(
                        "INSERT INTO entity_values (entity_code, value, weight, is_enabled) VALUES (?, ?, 1.0, 1)",
                        (entity_code, entity_value)
                    )
                    total += 1
                    logger.debug(f"导入实体值: {entity_value} -> {entity_code}")
        
        logger.info(f"✅ 从标注数据导入实体值完成，共导入{total}个新实体值")
        return True
        
    except Exception as e:
        logger.error(f"导入失败: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    json_path = "/Volumes/1T/ai_project/ai-llm-router/data/租房行业/租房数据标注99.json"
    import_entities_from_labeled_data(json_path)