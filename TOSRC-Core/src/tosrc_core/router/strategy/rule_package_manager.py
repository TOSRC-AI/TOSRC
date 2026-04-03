#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则包管理器：加载、解析、管理外置JSON行业规则包
完全兼容《外接LLM调教系统方案》中的规则包格式，支持热更新、多行业插拔
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from ...common.utils.logger import get_logger
from ...common.interface.dal import BaseDAL

logger = get_logger()

class RulePackageManager:
    """规则包管理器
    规则目录由适配层传入，不硬编码路径
    """
    def __init__(self, 
                 rule_dir: str,
                 dal: Optional[BaseDAL] = None,
                 auto_reload: bool = True):
        """
        初始化规则包管理器
        :param rule_dir: 规则包存储目录，由适配层传入
        :param dal: 数据访问层实例，用于同步规则到数据库
        :param auto_reload: 是否开启自动热更新
        """
        self.rule_dir = rule_dir
        self.dal = dal
        self.auto_reload = auto_reload
        
        os.makedirs(self.rule_dir, exist_ok=True)
        
        # 规则包缓存：{scene: {rule_data, last_modify_time}}
        self.rule_cache: Dict[str, Dict[str, Any]] = {}
        # 规则包后缀名
        self.rule_suffix = "_rules.json"
        
        # 初始加载所有规则包
        self._load_all_rule_packages()
    
    def _load_rule_package(self, scene: str, file_path: str) -> bool:
        """加载单个规则包
        Args:
            scene: 行业场景编码（如rental、finance）
            file_path: 规则包文件路径
        Returns:
            是否加载成功
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                rule_data = json.load(f)
            
            # 基础格式校验
            required_fields = ["scene", "entity_rules", "intent_rules", "emotion_rules", "negative_rules"]
            for field in required_fields:
                if field not in rule_data:
                    logger.error(f"规则包{file_path}缺少必填字段: {field}")
                    return False
            
            # 缓存规则包和修改时间
            self.rule_cache[scene] = {
                "data": rule_data,
                "modify_time": os.path.getmtime(file_path),
                "file_path": file_path
            }
            logger.info(f"规则包加载成功: {scene} -> {file_path}")
            return True
        except Exception as e:
            logger.error(f"规则包加载失败: {file_path}, 错误: {str(e)}")
            return False
    
    def _load_all_rule_packages(self) -> None:
        """加载目录下所有规则包"""
        if not os.path.exists(self.rule_dir):
            logger.warning(f"规则包目录不存在: {self.rule_dir}，将自动创建")
            os.makedirs(self.rule_dir, exist_ok=True)
            return
        
        for file_name in os.listdir(self.rule_dir):
            if file_name.endswith(self.rule_suffix):
                scene = file_name.replace(self.rule_suffix, "")
                file_path = os.path.join(self.rule_dir, file_name)
                self._load_rule_package(scene, file_path)
        
        logger.info(f"所有规则包加载完成，共加载{len(self.rule_cache)}个场景规则包")
    
    def _check_and_reload(self, scene: str) -> None:
        """检查规则包是否有更新，自动重载"""
        if not self.auto_reload or scene not in self.rule_cache:
            return
        
        cache_info = self.rule_cache[scene]
        current_modify_time = os.path.getmtime(cache_info["file_path"])
        if current_modify_time > cache_info["modify_time"]:
            logger.info(f"检测到规则包{scene}更新，自动重载")
            self._load_rule_package(scene, cache_info["file_path"])
    
    def get_scene_rules(self, scene: str) -> Dict[str, Any]:
        """获取指定场景的规则
        Args:
            scene: 行业场景编码
        Returns:
            规则数据，不存在返回空字典
        """
        # 自动检查更新
        self._check_and_reload(scene)
        return self.rule_cache.get(scene, {}).get("data", {})
    
    def list_all_scenes(self) -> List[str]:
        """获取所有已加载的场景列表"""
        return list(self.rule_cache.keys())
    
    def reload_all(self) -> None:
        """强制重载所有规则包"""
        self.rule_cache.clear()
        self._load_all_rule_packages()
    
    def save_rule_package(self, scene: str, rule_data: Dict[str, Any]) -> bool:
        """保存规则包到文件
        Args:
            scene: 场景编码
            rule_data: 规则数据
        Returns:
            是否保存成功
        """
        try:
            file_path = os.path.join(self.rule_dir, f"{scene}{self.rule_suffix}")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(rule_data, f, ensure_ascii=False, indent=2)
            logger.info(f"规则包保存成功: {scene} -> {file_path}")
            # 重新加载
            self._load_rule_package(scene, file_path)
            return True
        except Exception as e:
            logger.error(f"规则包保存失败: {scene}, 错误: {str(e)}")
            return False
    
    def create_default_rule_package(self, scene: str, scene_name: str = "") -> bool:
        """创建默认规则包模板
        Args:
            scene: 场景编码
            scene_name: 场景名称
        Returns:
            是否创建成功
        """
        default_rule = {
            "scene": scene,
            "scene_name": scene_name or scene,
            "entity_rules": [],
            "intent_rules": [],
            "emotion_rules": {
                "positive_words": [],
                "negative_words": [],
                "urgent_words": [],
                "calm_words": []
            },
            "negative_rules": [],
            "priority": [1, 2, 3, 4]  # 否定规则>实体规则>意图规则>情绪规则
        }
        return self.save_rule_package(scene, default_rule)

# 全局单例
# 全局实例已移除，由适配层根据场景创建
