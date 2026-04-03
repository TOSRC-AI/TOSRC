"""
网络适配层抽象接口
TOSRC-Core仅依赖此接口，具体实现由单/多租户适配层提供
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
class BaseNetworkAdapter(ABC):
    """网络适配层基类"""
    @abstractmethod
    def load_plugin(self, plugin_id: str, plugin_path: Optional[str] = None) -> Any:
        """加载插件
        单租户实现仅加载本地插件，多租户实现支持加载云插件
        """
        pass
    @abstractmethod
    def get_remote_resource(self, resource_url: str) -> Optional[bytes]:
        """获取远程资源
        单租户实现直接返回None（禁用联网），多租户实现支持加载远程资源
        """
        pass
    @abstractmethod
    def report_log(self, log_data: Dict[str, Any]) -> bool:
        """上报日志
        单租户实现仅本地存储日志，多租户实现支持远程上报
        """
        pass
    @abstractmethod
    def is_offline_mode(self) -> bool:
        """是否为离线模式"""
        pass