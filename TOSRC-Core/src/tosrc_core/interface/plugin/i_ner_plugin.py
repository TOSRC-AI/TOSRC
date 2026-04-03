#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NER实体识别插件标准接口
Core层通用接口定义，所有NER实现都必须遵循此接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class I_NerPlugin(ABC):
    """NER实体识别插件抽象接口"""
    
    @abstractmethod
    def get_plugin_info(self) -> Dict[str, Any]:
        """
        获取插件基本信息
        :return: 插件信息字典，包含name, version, description, author等字段
        """
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化插件
        :param config: 配置参数，模型路径、阈值等
        :return: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取实体
        :param text: 输入文本
        :return: 实体列表，每个实体包含: type, value, start, end, confidence字段
        示例：[
            {"type": "location", "value": "北京市朝阳区", "start": 0, "end": 6, "confidence": 0.95},
            {"type": "price", "value": "3000元", "start": 10, "end": 14, "confidence": 0.88}
        ]
        """
        pass
    
    @abstractmethod
    def get_supported_entity_types(self) -> List[str]:
        """
        获取支持的实体类型列表
        :return: 实体类型编码列表
        """
        pass
    
    @abstractmethod
    def destroy(self) -> bool:
        """
        销毁插件，释放资源
        :return: 销毁是否成功
        """
        pass