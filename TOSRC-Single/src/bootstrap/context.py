"""
单租户核心组件上下文（单例模式）
模块化管理所有核心组件，确保线程安全，替代裸全局变量
"""
import threading
from typing import Any
from src.utils.logger import logger
from src.bootstrap.db_init import init_db
from src.bootstrap.component_init import init_core_components
from src.config.loader import get_global_config, get_scheduler_config, get_llm_config, get_auto_learn_config

class SingleTenantContext:
    """单租户核心组件上下文（线程安全单例）"""
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def init(self):
        """初始化所有核心组件（仅执行一次，线程安全）"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            # 1. 加载全局配置
            self.global_config = get_global_config()
            
            # 2. 初始化数据库（首次初始化禁用连接池，避免与 CoreInitializer 兼容性问题）
            from src.adapter.dal.sqlite_dal import SQLiteDAL
            self.db = SQLiteDAL(self.global_config["database"]["sqlite_path"], use_pool=False)
            
            # 3. 执行Core层通用初始化（自动建表、加载默认意图库）
            from tosrc_core.common.bootstrap.initializer import CoreInitializer
            initializer = CoreInitializer(self.db)
            init_success = initializer.initialize_all()
            if not init_success:
                from src.utils.logger import logger
                logger.error("❌ Core层初始化失败")
                raise RuntimeError("Core层初始化失败")
            
            # 3.5 自动导入行业数据（存在则跳过，失败不影响启动）
            try:
                from scripts.import_industry_data import IndustryDataImporter
                data_importer = IndustryDataImporter(db=self.db)
                data_importer.import_all()
            except Exception as e:
                logger.warning(f"行业数据导入失败，不影响系统启动: {str(e)}")
            
            # 4. 初始化网络适配器（离线模式）
            from src.adapter.net.offline_adapter import offline_net_adapter
            self.net_adapter = offline_net_adapter
            
            # 4. 初始化核心组件
            self.scheduler, self.neuron_core, self.rule_package_manager, self.llm_annotator, self.auto_learner = init_core_components(
                db=self.db,
                net_adapter=self.net_adapter,
                scheduler_config=get_scheduler_config(),
                llm_config=get_llm_config(),
                auto_learn_config=get_auto_learn_config()
            )
            
            # 标记初始化完成
            self._initialized = True
            from src.utils.logger import logger
            logger.info("✅ 单租户核心组件初始化完成")

# 对外提供获取上下文的方法（模块化导出）
def get_tenant_context() -> SingleTenantContext:
    return SingleTenantContext()

# 简化组件获取方法（按需导出，供API模块调用）
def get_scheduler() -> Any:
    return get_tenant_context().scheduler

def get_neuron_core() -> Any:
    return get_tenant_context().neuron_core

def get_db() -> Any:
    return get_tenant_context().db

def get_rule_package_manager() -> Any:
    return get_tenant_context().rule_package_manager