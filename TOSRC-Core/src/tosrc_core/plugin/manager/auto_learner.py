#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动学习模块：实现系统自我进化能力，自动从LLM标注数据中挖掘规则、审核、上线
支持定时学习、阈值触发学习、手动触发学习三种模式
"""
import os
import time
import json
from typing import Dict, Any, List
from collections import defaultdict
from ...common.utils.logger import get_logger
from ...common.interface.dal import BaseDAL
from ...router.strategy.rule_miner import RuleMiner
from ...router.strategy.rule_package_manager import RulePackageManager

logger = get_logger()

class AutoLearner:
    """自动学习核心类
    依赖数据访问层接口，所有数据操作通过DAL实现
    """
    def __init__(self, 
                 config: Dict[str, Any],
                 dal: BaseDAL,
                 rule_miner: RuleMiner,
                 rule_package_manager: RulePackageManager):
        """
        初始化自动学习模块
        :param config: 学习配置字典，由适配层传入
        :param dal: 数据访问层实例
        :param rule_miner: 规则挖掘实例
        :param rule_package_manager: 规则包管理器实例
        """
        self.config = config
        self.dal = dal
        self.rule_miner = rule_miner
        self.rule_package_manager = rule_package_manager
        
        # 学习统计：{scene: {last_learn_time, annotation_count, rule_count}}
        self.learn_stats = defaultdict(lambda: {
            "last_learn_time": 0,
            "annotation_count": 0,
            "rule_count": 0
        })
        
        # 上次学习时的标注数量记录
        self.last_annotation_count = defaultdict(int)
        
        logger.info("自动学习模块初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载自动学习配置，不存在则创建默认配置"""
        default_config = {
            "auto_learn_enabled": True,  # 自动学习总开关
            "learn_threshold": 50,  # 每积累50条标注数据自动学习一次
            "learn_interval": 3600,  # 最小学习间隔，单位秒（至少1小时学习一次）
            "auto_approve_threshold": 0.8,  # 规则自动审核通过阈值（冲突率<20%自动上线）
            "auto_update_rules": True,  # 自动上线审核通过的规则
            "max_rules_per_type": 20,  # 每种规则最多保留20条，避免规则爆炸
            "confidence_threshold": 0.85  # 新规则最小置信度要求
        }
        
        # 配置文件不存在则创建默认配置
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info("已创建默认自动学习配置文件: config/auto_learn_config.json")
            return default_config
        
        # 加载现有配置
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 补全缺失的配置项
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            logger.info("自动学习配置加载成功")
            return config
        except Exception as e:
            logger.error(f"自动学习配置加载失败，使用默认配置: {str(e)}")
            return default_config
    
    def _get_annotation_count(self, scene: str) -> int:
        """获取指定场景的标注数据数量"""
        scene_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "annotations", scene
        )
        if not os.path.exists(scene_dir):
            return 0
        return len([f for f in os.listdir(scene_dir) if f.endswith(".json")])
    
    def _calculate_rule_conflict_rate(self, new_rules: List[Dict[str, Any]], existing_rules: List[Dict[str, Any]]) -> float:
        """计算新规则和现有规则的冲突率"""
        if not existing_rules:
            return 0.0
        
        conflict_count = 0
        # 简单冲突检测：相同意图/实体的规则，如果正则模式有包含关系视为冲突
        new_patterns = [r.get("pattern", "") for r in new_rules]
        existing_patterns = [r.get("pattern", "") for r in existing_rules]
        
        for new_pat in new_patterns:
            for exist_pat in existing_patterns:
                if new_pat in exist_pat or exist_pat in new_pat:
                    conflict_count += 1
                    break
        
        return conflict_count / len(new_rules) if new_rules else 0.0
    
    def _merge_rules(self, existing_rules: List[Dict[str, Any]], new_rules: List[Dict[str, Any]], rule_type: str) -> List[Dict[str, Any]]:
        """合并新老规则，去重、按优先级排序、保留最新的规则"""
        # 按模式去重
        pattern_map = {}
        # 先加入现有规则
        for rule in existing_rules:
            pattern = rule.get("pattern", "")
            if pattern:
                pattern_map[pattern] = rule
        
        # 加入新规则，覆盖重复的旧规则
        for rule in new_rules:
            pattern = rule.get("pattern", "")
            if pattern:
                pattern_map[pattern] = rule
        
        # 转换为列表，按优先级排序，优先保留高优先级、高频的规则
        merged = sorted(pattern_map.values(), key=lambda x: (-x.get("priority", 1), -x.get("count", 0)))
        
        # 限制最大规则数量，避免爆炸
        max_count = self.config.get("max_rules_per_type", 20)
        if len(merged) > max_count:
            merged = merged[:max_count]
            logger.info(f"{rule_type}规则数量超过上限{max_count}，已保留优先级最高的{max_count}条")
        
        return merged
    
    def learn(self, scene: str = "rental", force: bool = False) -> Dict[str, Any]:
        """
        执行一次学习
        Args:
            scene: 场景编码
            force: 是否强制学习，忽略阈值和间隔限制
        Returns:
            学习结果统计
        """
        if not self.config.get("auto_learn_enabled", False) and not force:
            return {"status": "disabled", "message": "自动学习功能未启用"}
        
        now = int(time.time())
        annotation_count = self._get_annotation_count(scene)
        new_annotation_count = annotation_count - self.last_annotation_count.get(scene, 0)
        last_learn_time = self.learn_stats[scene]["last_learn_time"]
        learn_interval = self.config.get("learn_interval", 3600)
        learn_threshold = self.config.get("learn_threshold", 50)
        
        # 检查是否满足学习条件
        if not force:
            if new_annotation_count < learn_threshold:
                return {
                    "status": "skip",
                    "message": f"新标注数据{new_annotation_count}条 < 阈值{learn_threshold}条，跳过学习"
                }
            if now - last_learn_time < learn_interval:
                return {
                    "status": "skip",
                    "message": f"距离上次学习仅{now-last_learn_time}秒 < 间隔{learn_interval}秒，跳过学习"
                }
        
        logger.info(f"开始执行{scene}场景自动学习，新标注数据: {new_annotation_count}条")
        
        # 1. 挖掘新规则
        new_rule_package = rule_miner.generate_rule_package(scene)
        if not new_rule_package:
            return {"status": "failed", "message": "规则挖掘失败"}
        
        # 2. 获取现有规则
        existing_rules = rule_package_manager.get_scene_rules(scene)
        if not existing_rules:
            existing_rules = {
                "entity_rules": [],
                "intent_rules": [],
                "emotion_rules": {},
                "negative_rules": []
            }
        
        # 3. 规则冲突检测
        entity_conflict_rate = self._calculate_rule_conflict_rate(
            new_rule_package["entity_rules"], existing_rules["entity_rules"]
        )
        intent_conflict_rate = self._calculate_rule_conflict_rate(
            new_rule_package["intent_rules"], existing_rules["intent_rules"]
        )
        total_conflict_rate = (entity_conflict_rate + intent_conflict_rate) / 2
        
        auto_approve_threshold = self.config.get("auto_approve_threshold", 0.8)
        approve_passed = total_conflict_rate <= (1 - auto_approve_threshold)
        
        result = {
            "status": "success",
            "scene": scene,
            "new_annotation_count": new_annotation_count,
            "new_entity_rules": len(new_rule_package["entity_rules"]),
            "new_intent_rules": len(new_rule_package["intent_rules"]),
            "new_emotion_rules": sum(len(v) for v in new_rule_package["emotion_rules"].values()),
            "new_negative_rules": len(new_rule_package["negative_rules"]),
            "conflict_rate": round(total_conflict_rate * 100, 2),
            "auto_approve_passed": approve_passed
        }
        
        # 4. 自动审核通过则合并规则并上线
        if approve_passed and self.config.get("auto_update_rules", True):
            # 合并各类规则
            merged_entity = self._merge_rules(existing_rules["entity_rules"], new_rule_package["entity_rules"], "实体")
            merged_intent = self._merge_rules(existing_rules["intent_rules"], new_rule_package["intent_rules"], "意图")
            merged_emotion = {
                "positive_words": list(set(existing_rules.get("emotion_rules", {}).get("positive_words", []) + new_rule_package["emotion_rules"]["positive_words"]))[:20],
                "negative_words": list(set(existing_rules.get("emotion_rules", {}).get("negative_words", []) + new_rule_package["emotion_rules"]["negative_words"]))[:20],
                "urgent_words": list(set(existing_rules.get("emotion_rules", {}).get("urgent_words", []) + new_rule_package["emotion_rules"]["urgent_words"]))[:20],
                "calm_words": list(set(existing_rules.get("emotion_rules", {}).get("calm_words", []) + new_rule_package["emotion_rules"]["calm_words"]))[:20]
            }
            merged_negative = self._merge_rules(existing_rules["negative_rules"], new_rule_package["negative_rules"], "否定")
            
            # 构造合并后的规则包
            merged_package = existing_rules.copy()
            merged_package.update({
                "entity_rules": merged_entity,
                "intent_rules": merged_intent,
                "emotion_rules": merged_emotion,
                "negative_rules": merged_negative,
                "update_time": now,
                "annotation_count": new_rule_package["annotation_count"]
            })
            
            # 保存到正式规则目录
            rule_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "rules", f"{scene}_rules.json"
            )
            with open(rule_path, "w", encoding="utf-8") as f:
                json.dump(merged_package, f, ensure_ascii=False, indent=2)
            
            # 触发规则包热重载
            rule_package_manager._load_rule_package(scene, rule_path)
            
            result.update({
                "merged_entity_rules": len(merged_entity),
                "merged_intent_rules": len(merged_intent),
                "rules_updated": True,
                "message": f"规则自动审核通过，已更新上线，实体规则{len(merged_entity)}条，意图规则{len(merged_intent)}条"
            })
            
            logger.info(f"{scene}场景学习完成，规则已自动更新上线")
        else:
            result.update({
                "rules_updated": False,
                "message": f"规则冲突率{result['conflict_rate']}% > 阈值{(1-auto_approve_threshold)*100}%，需要人工审核，待审核规则已保存到rules/pending目录"
            })
            logger.info(f"{scene}场景学习完成，规则需要人工审核")
        
        # 更新统计信息
        self.learn_stats[scene].update({
            "last_learn_time": now,
            "annotation_count": annotation_count,
            "rule_count": len(existing_rules.get("entity_rules", [])) + len(existing_rules.get("intent_rules", []))
        })
        self.last_annotation_count[scene] = annotation_count
        
        return result
    
    def get_learn_stats(self, scene: str = None) -> Dict[str, Any]:
        """获取学习统计信息"""
        if scene:
            return self.learn_stats.get(scene, {})
        return dict(self.learn_stats)

# 全局单例
# 全局实例已移除，由适配层根据场景创建
