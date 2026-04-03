#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仿生架构缓存层
Redis高频热数据缓存，提升性能
"""
import json
from typing import Dict, Any, Optional
import redis
from ...common.utils.logger import get_logger

logger = get_logger()

class BionicCache:
    """仿生架构缓存类（单例模式）"""
    _instance = None
    # 缓存开关，默认关闭
    _enabled = False
    # 缓存配置
    _redis_host = "127.0.0.1"
    _redis_port = 6379
    _redis_db = 0
    _redis_password = None
    # 缓存过期时间（秒）
    _default_ttl = 3600  # 1小时
    _user_weight_ttl = 86400  # 用户个性化权重缓存1天
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_cache()
        return cls._instance
    
    def _init_cache(self):
        """初始化缓存连接"""
        if not self._enabled:
            logger.info("仿生架构缓存已关闭，跳过初始化")
            return
        
        try:
            self.redis_client = redis.Redis(
                host=self._redis_host,
                port=self._redis_port,
                db=self._redis_db,
                password=self._redis_password,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            # 测试连接
            self.redis_client.ping()
            logger.info("仿生架构Redis缓存初始化成功")
        except Exception as e:
            logger.warning(f"Redis连接失败，缓存已禁用：{str(e)}")
            self._enabled = False
            self.redis_client = None
    
    def enable(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0, password: Optional[str] = None):
        """启用缓存"""
        self._enabled = True
        self._redis_host = host
        self._redis_port = port
        self._redis_db = db
        self._redis_password = password
        self._init_cache()
    
    def disable(self):
        """禁用缓存"""
        self._enabled = False
        if hasattr(self, 'redis_client') and self.redis_client:
            self.redis_client.close()
        logger.info("仿生架构缓存已禁用")
    
    def get_synapse_weights(self, intent_id: str, user_id: str = "global") -> Optional[Dict[str, float]]:
        """获取突触权重缓存"""
        if not self._enabled or not self.redis_client:
            return None
        
        try:
            key = f"bionic:synapse:{intent_id}:{user_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"读取突触权重缓存失败：{str(e)}")
            return None
    
    def set_synapse_weights(self, intent_id: str, weights: Dict[str, float], user_id: str = "global"):
        """设置突触权重缓存"""
        if not self._enabled or not self.redis_client:
            return
        
        try:
            key = f"bionic:synapse:{intent_id}:{user_id}"
            ttl = self._user_weight_ttl if user_id != "global" else self._default_ttl
            self.redis_client.setex(key, ttl, json.dumps(weights))
        except Exception as e:
            logger.warning(f"写入突触权重缓存失败：{str(e)}")
    
    def delete_synapse_weights(self, intent_id: str, user_id: str = "global"):
        """删除突触权重缓存，权重修改后调用"""
        if not self._enabled or not self.redis_client:
            return
        
        try:
            key = f"bionic:synapse:{intent_id}:{user_id}"
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"删除突触权重缓存失败：{str(e)}")
    
    def get_activation_result(self, text: str, user_id: str = "global") -> Optional[Dict[str, Any]]:
        """缓存识别结果，高频相同输入直接返回"""
        if not self._enabled or not self.redis_client:
            return None
        
        try:
            import hashlib
            text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            key = f"bionic:result:{text_hash}:{user_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"读取识别结果缓存失败：{str(e)}")
            return None
    
    def set_activation_result(self, text: str, result: Dict[str, Any], user_id: str = "global"):
        """缓存识别结果"""
        if not self._enabled or not self.redis_client:
            return
        
        try:
            import hashlib
            text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            key = f"bionic:result:{text_hash}:{user_id}"
            # 识别结果缓存5分钟
            self.redis_client.setex(key, 300, json.dumps(result))
        except Exception as e:
            logger.warning(f"写入识别结果缓存失败：{str(e)}")

# 全局单例实例
bionic_cache = BionicCache()
