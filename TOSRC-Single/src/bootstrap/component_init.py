"""
核心组件初始化模块化方法，单独拆分，解耦初始化逻辑
"""
from typing import Tuple, Any
from tosrc_core.router.scheduler import Scheduler
from tosrc_core.semantic.neuron_core import NeuronCore
from tosrc_core.router.strategy.rule_package_manager import RulePackageManager
from tosrc_core.router.strategy.rule_miner import RuleMiner
from tosrc_core.plugin.manager.llm_annotator import LLMAnnotator
from tosrc_core.plugin.manager.auto_learner import AutoLearner
from src.utils.logger import logger

def init_core_components(db, net_adapter, scheduler_config: dict, llm_config: dict, auto_learn_config: dict) -> Tuple[Any, Any, Any, Any, Any]:
    """
    初始化所有核心组件
    :param db: 数据访问层实例
    :param net_adapter: 网络适配器实例
    :param scheduler_config: 调度器配置
    :param llm_config: LLM配置
    :param auto_learn_config: 自动学习配置
    :return: (scheduler, neuron_core, rule_package_manager, llm_annotator, auto_learner)
    """
    try:
        logger.info("开始初始化核心组件...")
        
        # 初始化规则包管理器
        rule_package_manager = RulePackageManager(
            rule_dir="./data/rules",
            dal=db,
            auto_reload=True
        )
        logger.info("规则包管理器初始化完成")
        
        # 初始化规则挖掘模块
        rule_miner = RuleMiner(dal=db)
        logger.info("规则挖掘模块初始化完成")
        
        # 初始化LLM标注器
        llm_annotator = LLMAnnotator(
            config=llm_config,
            net_adapter=net_adapter,
            dal=db
        )
        logger.info("LLM标注器初始化完成")
        
        # 初始化自动学习模块
        auto_learner = AutoLearner(
            config=auto_learn_config,
            dal=db,
            rule_miner=rule_miner,
            rule_package_manager=rule_package_manager
        )
        logger.info("自动学习模块初始化完成")
        
        # 初始化语义识别核心
        neuron_core = NeuronCore(
            dal=db,
            net_adapter=net_adapter
        )
        logger.info("语义识别核心初始化完成")
        
        # 初始化调度引擎
        scheduler = Scheduler(
            dal=db,
            net_adapter=net_adapter,
            neuron_core=neuron_core,
            llm_annotator=llm_annotator,
            auto_learner=auto_learner,
            rule_package_manager=rule_package_manager,
            rule_miner=rule_miner,
            config=scheduler_config
        )
        logger.info("调度引擎初始化完成")
        
        return scheduler, neuron_core, rule_package_manager, llm_annotator, auto_learner
        
    except Exception as e:
        logger.error(f"❌ 核心组件初始化失败：{str(e)}", exc_info=True)
        raise Exception(f"核心组件初始化失败：{str(e)}") from e