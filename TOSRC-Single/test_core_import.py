#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证TOSRC-Core核心模块导入和基本功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TOSRC-Core/src"))

print("🔍 开始验证TOSRC-Core核心模块导入...")

try:
    from tosrc_core.router.scheduler import Scheduler
    print("✅ 导入成功：tosrc_core.router.scheduler.Scheduler")
except Exception as e:
    print(f"❌ 导入失败：Scheduler，错误：{str(e)}")
    sys.exit(1)

try:
    from tosrc_core.semantic.neuron_core import NeuronCore
    print("✅ 导入成功：tosrc_core.semantic.neuron_core.NeuronCore")
except Exception as e:
    print(f"❌ 导入失败：NeuronCore，错误：{str(e)}")
    sys.exit(1)

try:
    from tosrc_core.router.strategy.rule_package_manager import RulePackageManager
    print("✅ 导入成功：tosrc_core.router.strategy.rule_package_manager.RulePackageManager")
except Exception as e:
    print(f"❌ 导入失败：RulePackageManager，错误：{str(e)}")
    sys.exit(1)

try:
    from tosrc_core.router.strategy.rule_miner import RuleMiner
    print("✅ 导入成功：tosrc_core.router.strategy.rule_miner.RuleMiner")
except Exception as e:
    print(f"❌ 导入失败：RuleMiner，错误：{str(e)}")
    sys.exit(1)

try:
    from tosrc_core.plugin.manager.llm_annotator import LLMAnnotator
    print("✅ 导入成功：tosrc_core.plugin.manager.llm_annotator.LLMAnnotator")
except Exception as e:
    print(f"❌ 导入失败：LLMAnnotator，错误：{str(e)}")
    sys.exit(1)

try:
    from tosrc_core.plugin.manager.auto_learner import AutoLearner
    print("✅ 导入成功：tosrc_core.plugin.manager.auto_learner.AutoLearner")
except Exception as e:
    print(f"❌ 导入失败：AutoLearner，错误：{str(e)}")
    sys.exit(1)

try:
    from tosrc_core.common.interface.dal import BaseDAL
    from tosrc_core.common.interface.net import BaseNetworkAdapter
    from tosrc_core.common.interface.tenant import BaseTenantAdapter
    print("✅ 导入成功：所有抽象接口")
except Exception as e:
    print(f"❌ 导入失败：抽象接口，错误：{str(e)}")
    sys.exit(1)

print("\n🎉 所有核心模块导入验证成功！TOSRC-Core引用正常。")
print("\n📋 接下来可以开始后续优化工作：")
print("1. API模块化拆分")
print("2. main.py瘦身优化")
print("3. 服务启动逻辑验证")