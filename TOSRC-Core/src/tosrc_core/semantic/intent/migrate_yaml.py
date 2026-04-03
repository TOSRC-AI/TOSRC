#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML配置自动迁移工具
将现有场景配置包一键导入到仿生架构知识图谱数据库
"""
import os
import yaml
from typing import Dict, Any
from pathlib import Path
from .db import bionic_db
from ...common.utils.logger import get_logger
from src.scene_loader import get_scene_loader

logger = get_logger()
scene_loader = get_scene_loader()

class YAMLMigrator:
    """YAML配置迁移器"""
    def __init__(self):
        self.config_root = Path(__file__).parent.parent.parent / "config" / "dev" / "scene_packages"
    
    def migrate_all_scenes(self) -> Dict[str, Any]:
        """迁移所有场景配置"""
        result = {
            "success": 0,
            "failed": 0,
            "scenes": []
        }
        
        # 获取所有场景目录
        scene_dirs = [d for d in self.config_root.iterdir() if d.is_dir()]
        for scene_dir in scene_dirs:
            scene_id = scene_dir.name
            try:
                self._migrate_single_scene(scene_id)
                result["success"] += 1
                result["scenes"].append(scene_id)
                logger.info(f"场景 {scene_id} 迁移成功")
            except Exception as e:
                result["failed"] += 1
                logger.error(f"场景 {scene_id} 迁移失败: {str(e)}")
        
        # 重载神经元核心
        from .neuron_core import synapse_core
        synapse_core.reload()
        
        logger.info(f"所有场景迁移完成: 成功{result['success']}个, 失败{result['failed']}个")
        return result
    
    def _migrate_single_scene(self, scene_id: str):
        """迁移单个场景配置"""
        scene_config = scene_loader.get_scene_config(scene_id)
        if not scene_config:
            raise ValueError(f"场景 {scene_id} 配置不存在")
        
        # 1. 迁移意图神经元和突触权重
        intents = scene_config["intent"]["intents"]
        for intent in intents:
            intent_id = intent["intent_id"]
            intent_name = intent["intent_name"]
            description = intent.get("description", "")
            base_priority = intent.get("priority", 1)
            
            # 添加意图神经元
            bionic_db.add_intent_neuron(
                scene_id=scene_id,
                intent_id=intent_id,
                intent_name=intent_name,
                description=description,
                base_priority=base_priority
            )
            
            # 添加突触权重（从规则中提取关键词）
            rules = intent.get("rules", [])
            for rule in rules:
                rule_type = rule["rule_type"]
                confidence = rule.get("confidence", 1.0)
                if rule_type == "keyword":
                    keywords = rule.get("keywords", [])
                    for kw in keywords:
                        # 关键词权重 = 置信度 * 关键词长度（越长的关键词权重越高）
                        weight = confidence * (1 + len(kw) * 0.1)
                        bionic_db.add_synapse_weight(intent_id, kw, weight)
                elif rule_type == "regex":
                    # 正则规则暂时按最高权重处理，后续扩展
                    pass
        
        # 2. 迁移意图-实体关联（智能关联）
        entities = scene_config["entity"]["entities"]
        
        # 定义意图-实体智能关联规则
        intent_entity_mapping = {
            # 天气场景
            "天气查询": ["时间", "地点", "天气类型"],
            "天气预警查询": ["时间", "地点", "预警类型", "预警级别"],
            
            # 租房场景
            "租房查询": ["房型", "租赁方式", "配套", "价格", "地铁", "特殊需求"],
            "房价咨询": ["价格", "付款方式"],
            "房源报修": ["设施", "房间", "问题"],
            "户型咨询": ["房型", "朝向", "面积"]
        }
        
        for intent in intents:
            intent_id = intent["intent_id"]
            
            # 获取该意图应该关联的实体
            if intent_id in intent_entity_mapping:
                entity_ids = intent_entity_mapping[intent_id]
                for entity_id in entity_ids:
                    # 检查实体是否存在于场景配置中
                    if any(e["entity_id"] == entity_id for e in entities):
                        bionic_db.add_entity_association(intent_id, entity_id)
                        logger.debug(f"添加实体关联: {intent_id} -> {entity_id}")
                    else:
                        logger.warning(f"实体 {entity_id} 不在场景 {scene_id} 的配置中")
            else:
                logger.warning(f"意图 {intent_id} 没有定义实体关联规则")
        
        logger.info(f"场景 {scene_id} 迁移完成，共导入{len(intents)}个意图神经元")

def run_migration():
    """执行迁移"""
    migrator = YAMLMigrator()
    return migrator.migrate_all_scenes()

if __name__ == "__main__":
    run_migration()
