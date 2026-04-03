#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuronCore 单元测试
"""
import pytest

from tosrc_core.semantic.intent.neuron_core import cn_to_num, _cn_integer_to_num


@pytest.mark.unit
class TestChineseNumberConversion:
    """测试中文数字转换功能"""

    def test_cn_to_num_simple(self):
        """测试简单中文数字转换"""
        assert cn_to_num("十") == 10
        assert cn_to_num("十五") == 15
        assert cn_to_num("二十") == 20
        assert cn_to_num("一百") == 100

    def test_cn_to_num_complex(self):
        """测试复杂中文数字转换"""
        assert cn_to_num("三千五") == 3500
        assert cn_to_num("一万二") == 12000
        assert cn_to_num("两万五") == 25000
        assert cn_to_num("三千零五") == 3005

    def test_cn_to_num_mixed(self):
        """测试混合数字+中文"""
        assert cn_to_num("1万2") == 12000
        assert cn_to_num("2千5") == 2500
        assert cn_to_num("3百") == 300

    def test_cn_to_num_decimal(self):
        """测试小数转换"""
        assert cn_to_num("零点五") == 0.5
        assert cn_to_num("三点八") == 3.8

    def test_cn_to_num_large(self):
        """测试大数字"""
        assert cn_to_num("一百万") == 1000000
        assert cn_to_num("一千万") == 10000000
        assert cn_to_num("一亿") == 100000000

    def test_cn_to_num_edge_cases(self):
        """测试边界情况"""
        assert cn_to_num("") == 0.0
        assert cn_to_num(None) == 0.0
        assert cn_to_num("invalid") == 0.0

    def test_cn_to_num_with_units(self):
        """测试带单位的数字"""
        assert cn_to_num("3k5") == 3500
        assert cn_to_num("2w3") == 23000


@pytest.mark.unit
class TestSynapseNeuronCore:
    """测试 SynapseNeuronCore 类"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        from tosrc_core.semantic.intent.neuron_core import SynapseNeuronCore

        # 获取两个实例
        instance1 = SynapseNeuronCore()
        instance2 = SynapseNeuronCore()

        # 应该是同一个实例
        assert instance1 is instance2

    def test_thread_safe_initialization(self):
        """测试线程安全的初始化"""
        import threading
        from tosrc_core.semantic.intent.neuron_core import SynapseNeuronCore

        instances = []

        def get_instance():
            instance = SynapseNeuronCore()
            instances.append(instance)

        # 多线程获取实例
        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有实例应该相同
        assert len(set(id(i) for i in instances)) == 1
