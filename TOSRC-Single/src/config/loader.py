"""
配置加载模块化类，统一管理所有配置的读取与解析
"""
import os
import json
from typing import Dict, Any

class ConfigLoader:
    """配置加载器（单例模式）"""
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all_configs()
        return cls._instance

    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """加载单个配置文件"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在：{file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_all_configs(self):
        """加载所有模块化配置，合并为全局配置"""
        # 项目根目录（适配不同调用路径）
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_root = os.path.join(root_path, "data", "config")

        # 加载各模块配置
        self._config["global"] = self._load_config_file(os.path.join(config_root, "global_config.json"))
        self._config["scheduler"] = self._load_config_file(os.path.join(config_root, "scheduler_config.json"))
        self._config["llm"] = self._load_config_file(os.path.join(config_root, "llm_config.json"))
        
        # 支持环境变量覆盖敏感配置（生产环境推荐）
        if os.getenv("ADMIN_API_KEY"):
            self._config["global"]["admin"]["admin_api_key"] = os.getenv("ADMIN_API_KEY")

    def get_config(self, module: str, key: str = None) -> Any:
        """获取配置：支持获取整个模块配置，或模块下的具体key"""
        if module not in self._config:
            raise KeyError(f"配置模块不存在：{module}")
        if key is None:
            return self._config[module]
        return self._config[module].get(key, None)

# 对外提供统一的配置实例（单例，全局唯一）
config_loader = ConfigLoader()

# 简化配置获取方法（按需导出，供其他模块调用）
def get_global_config(key: str = None) -> Any:
    return config_loader.get_config("global", key)

def get_scheduler_config(key: str = None) -> Any:
    return config_loader.get_config("scheduler", key)

def get_llm_config(key: str = None) -> Any:
    return config_loader.get_config("llm", key)

def get_auto_learn_config(key: str = None) -> Any:
    auto_learn_config = get_global_config("auto_learn")
    if key is None:
        return auto_learn_config
    return auto_learn_config.get(key, None)