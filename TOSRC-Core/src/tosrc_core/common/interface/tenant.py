"""
租户适配层抽象接口
TOSRC-Core仅依赖此接口，具体实现由多租户适配层提供，单租户无需实现
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
class BaseTenantAdapter(ABC):
    """租户适配层基类"""
    @abstractmethod
    def get_current_tenant_id(self) -> Optional[str]:
        """获取当前请求的租户ID"""
        pass
    @abstractmethod
    def filter_by_tenant(self, query: str) -> str:
        """给查询条件添加租户过滤"""
        pass
    @abstractmethod
    def get_tenant_redis_key(self, key: str) -> str:
        """获取带租户前缀的Redis键"""
        pass
    @abstractmethod
    def is_tenant_enabled(self, tenant_id: str) -> bool:
        """检查租户是否启用"""
        pass