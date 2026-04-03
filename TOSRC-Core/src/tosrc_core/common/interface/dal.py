"""
数据访问层抽象接口
TOSRC-Core仅依赖此接口，具体实现由单/多租户适配层提供
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
class BaseDAL(ABC):
    """数据访问层基类"""
    @abstractmethod
    def get_intent_by_id(self, intent_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查询意图"""
        pass
    @abstractmethod
    def get_all_intents(self) -> List[Dict[str, Any]]:
        """查询所有意图"""
        pass
    @abstractmethod
    def get_keyword_by_text_and_relation(self, keyword: str, type: str, relation_id: int) -> Optional[Dict[str, Any]]:
        """根据关键词文本和关联ID查询关键词"""
        pass
    @abstractmethod
    def add_keyword(self, keyword: str, type: str, relation_id: int, weight: float, is_enabled: int, description: str = "") -> int:
        """新增关键词"""
        pass
    @abstractmethod
    def update_keyword_weight(self, keyword_id: int, weight: float) -> bool:
        """更新关键词权重"""
        pass
    @abstractmethod
    def get_entity_by_type(self, entity_type: str) -> Optional[Dict[str, Any]]:
        """根据实体类型查询实体信息"""
        pass
    @abstractmethod
    def save_route_record(self, intent: Dict[str, Any], entities: List[Dict[str, Any]]) -> int:
        """保存路由记录"""
        pass
    @abstractmethod
    def get_all_entities(self) -> List[Dict[str, Any]]:
        """查询所有实体"""
        pass
    @abstractmethod
    def get_all_keywords(self, type: Optional[str] = None, relation_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """查询关键词列表"""
        pass
    
    @abstractmethod
    def get_business_entity_keyword_cache(self, industry_code: str = "default") -> Dict[str, Any]:
        """获取业务实体关键词缓存，用于快速匹配"""
        pass
    
    @abstractmethod
    def get_business_entity_cache(self, industry_code: str = "default") -> Dict[str, Any]:
        """获取业务实体缓存，用于实体提取匹配"""
        pass
    
    # ===== 通用SQL操作接口 =====
    @abstractmethod
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询SQL，返回结果列表"""
        pass
    
    @abstractmethod
    def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """执行插入SQL，返回自增ID"""
        pass
    
    @abstractmethod
    def execute_update(self, sql: str, params: tuple = ()) -> bool:
        """执行更新/删除SQL，返回是否成功"""
        pass
    
    # ===== 事务接口 =====
    @abstractmethod
    def begin_transaction(self) -> None:
        """开启事务"""
        pass
    
    @abstractmethod
    def commit_transaction(self) -> None:
        """提交事务"""
        pass
    
    @abstractmethod
    def rollback_transaction(self) -> None:
        """回滚事务"""
        pass