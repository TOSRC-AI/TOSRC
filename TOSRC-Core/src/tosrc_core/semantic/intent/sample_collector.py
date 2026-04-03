#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低置信度样本自动收集模块
自动收集识别置信度低于阈值的样本，用于自主学习和标注
"""
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from ...common.utils.logger import get_logger
from src.bionic.db import bionic_db

logger = get_logger()

class SampleCollector:
    """低置信度样本收集器（单例模式）"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init_config()
        return cls._instance
    
    def init_config(self):
        """初始化配置"""
        self.enable_collection = True  # 是否开启样本收集
        self.confidence_threshold = 0.7  # 置信度低于这个值的样本会被收集
        self.storage_path = Path("data/samples/low_confidence/")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        # 异步写入队列，避免阻塞主流程
        self._queue = asyncio.Queue()
        # 启动异步写入任务
        asyncio.create_task(self._async_writer())
    
    def collect(self, text: str, intent_result: Dict[str, Any], user_id: str = "global", scene_id: str = ""):
        """
        收集低置信度样本
        :param text: 用户输入文本
        :param intent_result: 意图识别结果
        :param user_id: 用户ID
        :param scene_id: 场景ID
        """
        if not self.enable_collection:
            return
        
        confidence = intent_result.get("confidence", 0.0)
        if confidence < self.confidence_threshold:
            sample = {
                "input_text": text,
                "confidence": confidence,
                "actual_intent": intent_result.get("intent_id", ""),
                "actual_intent_name": intent_result.get("intent_name", ""),
                "scene_id": scene_id or intent_result.get("scene_id", ""),
                "user_id": user_id,
                "synapse_weights": intent_result.get("synapse_weights", {}),
                "timestamp": int(time.time() * 1000),
                "status": "pending"  # pending:待标注, annotated:已标注, ignored:已忽略
            }
            
            # 异步写入队列，不阻塞主流程
            try:
                asyncio.create_task(self._queue.put(sample))
            except Exception as e:
                logger.warning(f"样本加入队列失败：{str(e)}")
    
    async def _async_writer(self):
        """异步写入样本到存储"""
        while True:
            try:
                sample = await self._queue.get()
                # 存储到JSON文件，按天分片
                date_str = time.strftime("%Y%m%d")
                file_path = self.storage_path / f"low_confidence_{date_str}.jsonl"
                
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                
                # 同时存储到数据库，方便查询
                bionic_db.add_low_confidence_sample(sample)
                
                logger.debug(f"低置信度样本已收集：{sample['input_text']}，置信度：{sample['confidence']:.2f}")
                
            except Exception as e:
                logger.error(f"样本写入失败：{str(e)}")
            finally:
                self._queue.task_done()
    
    def get_pending_samples(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取待标注的样本列表"""
        return bionic_db.get_low_confidence_samples(status="pending", limit=limit)
    
    def annotate_sample(self, sample_id: int, correct_intent: str, correct_entities: List[Dict[str, Any]] = None):
        """标注样本，自动更新权重"""
        # 1. 更新样本状态为已标注
        bionic_db.update_sample_status(sample_id, "annotated", correct_intent, correct_entities)
        # 2. 自动强化正确的突触权重
        sample = bionic_db.get_sample_by_id(sample_id)
        if sample:
            from src.bionic.auto_optimizer import auto_optimizer
            # 构造失败用例格式，调用自动优化
            failed_case = {
                "input": sample["input_text"],
                "expect_intent": correct_intent,
                "actual_intent": sample["actual_intent"],
                "error_type": "意图错误",
                "expect_entities": correct_entities or []
            }
            auto_optimizer.optimize_from_failed_cases([failed_case])
            logger.info(f"样本标注完成，已自动优化权重：{sample['input_text']} → {correct_intent}")
    
    def ignore_sample(self, sample_id: int):
        """忽略样本"""
        bionic_db.update_sample_status(sample_id, "ignored")
        logger.info(f"样本已忽略：ID={sample_id}")

# 全局单例实例
sample_collector = SampleCollector()
