"""
单租户离线网络适配器实现
实现TOSRC-Core定义的BaseNetworkAdapter接口，禁用所有联网功能
"""
from typing import Any, Optional, Dict
from tosrc_core.common.interface.net import BaseNetworkAdapter

class OfflineNetworkAdapter(BaseNetworkAdapter):
    """离线网络适配器，禁用所有联网功能"""
    def __init__(self):
        self.offline_mode = True
    
    def load_plugin(self, plugin_id: str, plugin_path: Optional[str] = None) -> Any:
        """仅加载本地插件，禁用云插件"""
        if not plugin_path:
            raise ValueError("离线模式下必须指定本地插件路径")
        # 本地插件加载逻辑
        logger.info(f"加载本地插件：{plugin_id} -> {plugin_path}")
        # 简化实现，后续完善
        return None
    
    def get_remote_resource(self, resource_url: str) -> Optional[bytes]:
        """离线模式下禁用远程资源加载"""
        logger.warning("离线模式下禁止加载远程资源")
        return None
    
    def report_log(self, log_data: Dict[str, Any]) -> bool:
        """离线模式下日志仅本地存储，不上报"""
        # 本地日志已通过logger模块处理
        return True
    
    def is_offline_mode(self) -> bool:
        """是否为离线模式"""
        return self.offline_mode

# 全局实例
offline_net_adapter = OfflineNetworkAdapter()