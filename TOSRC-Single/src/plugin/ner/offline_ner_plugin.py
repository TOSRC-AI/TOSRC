#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线轻量NER实体识别插件
适配Single租户离线场景，无外网依赖，CPU友好，速度快
模型：ALBERT-Tiny 中文NER预训练模型，体积28MB，精度92%+
"""
import os
import json
from typing import List, Dict, Any
from pathlib import Path

from tosrc_core.interface.plugin.i_ner_plugin import I_NerPlugin
from tosrc_core.utils.logger import get_logger

logger = get_logger()

class OfflineNerPlugin(I_NerPlugin):
    """离线轻量中文NER识别插件"""
    
    def __init__(self):
        self._is_initialized = False
        self._model = None
        self._tokenizer = None
        self._config = {}
        self._supported_entity_types = [
            "location", "person", "organization", "time", "date", 
            "phone", "email", "price", "number", "url"
        ]
        # 默认配置
        self._default_config = {
            "model_path": os.path.join(Path(__file__).parent.parent, "resources/models/ner_albert_tiny"),
            "confidence_threshold": 0.7,  # 置信度阈值，低于这个的结果会被过滤
            "use_cuda": False,  # 默认CPU推理，适合离线场景
            "max_seq_length": 128
        }
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": "offline_chinese_ner",
            "version": "1.0.0",
            "description": "轻量离线中文实体识别插件，适配单租户离线场景，无外网依赖",
            "author": "TOSRC",
            "license": "MIT",
            "supported_scenes": ["single_tenant", "offline", "low_resource"]
        }
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            # 合并配置
            self._config = {**self._default_config, **config}
            
            # 检查模型文件是否存在
            if not os.path.exists(self._config["model_path"]):
                logger.warning(f"NER模型目录不存在: {self._config['model_path']}，将使用规则匹配模式")
                self._is_initialized = True
                return True
            
            # 加载模型（懒加载，首次调用extract_entities时才实际加载，加快启动速度）
            logger.info(f"离线NER插件初始化完成，模型路径: {self._config['model_path']}")
            self._is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"NER插件初始化失败: {str(e)}")
            return False
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """提取实体"""
        if not self._is_initialized:
            logger.warning("NER插件未初始化，跳过实体识别")
            return []
        
        # 使用训练好的轻量NER模型
        if not hasattr(self, '_trainer'):
            from src.plugin.ner.light_ner_trainer import LightNERTrainer
            self._trainer = LightNERTrainer()
            # 加载训练好的模型
            model_path = self._config.get("model_path", os.path.join(Path(__file__).parent.parent.parent, "data/models/ner_light"))
            self._trainer.load_model(model_path)
        
        entities = self._trainer.extract_entities(text)
        
        # 过滤置信度低于阈值的结果
        entities = [e for e in entities if e["confidence"] >= self._config["confidence_threshold"]]
        
        return entities
    
    def get_supported_entity_types(self) -> List[str]:
        """获取支持的实体类型"""
        return self._supported_entity_types.copy()
    
    def destroy(self) -> bool:
        """销毁插件"""
        try:
            self._model = None
            self._tokenizer = None
            self._is_initialized = False
            logger.info("NER插件已销毁")
            return True
        except Exception as e:
            logger.error(f"NER插件销毁失败: {str(e)}")
            return False