#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSONL 功能测试脚本
"""
import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'TOSRC-Single'))

from src.utils.jsonl_logger import JSONLLogger
from src.utils.route_logger import RouteLogger
from src.utils.archiver import LogArchiver


def test_jsonl_logger():
    """测试 JSONLLogger 基础功能"""
    print("=" * 50)
    print("测试 JSONLLogger")
    print("=" * 50)

    log_dir = "test_logs"

    # 清理测试目录
    import shutil
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

    # 创建日志记录器
    logger = JSONLLogger(log_dir, "test", buffer_size=5)

    # 测试写入
    print("\n1. 测试写入...")
    for i in range(10):
        logger.write({
            "id": i,
            "message": f"Test message {i}",
            "timestamp": datetime.now().isoformat()
        })
    print(f"  ✓ 写入 10 条记录")

    # 刷新缓冲区
    logger.flush()
    print("  ✓ 缓冲区已刷新")

    # 测试读取
    print("\n2. 测试读取...")
    log_file = os.path.join(log_dir, f"test_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    records = JSONLLogger.read_all(log_file)
    print(f"  ✓ 读取到 {len(records)} 条记录")

    # 验证数据
    assert len(records) == 10, f"记录数不匹配: {len(records)} != 10"
    assert records[0]["id"] == 0
    print("  ✓ 数据验证通过")

    # 测试统计
    print("\n3. 测试统计...")
    stats = logger.get_stats()
    print(f"  总文件数: {stats['total_files']}")
    print(f"  总大小: {stats['total_size_human']}")
    print("  ✓ 统计功能正常")

    logger.close()
    print("\n✅ JSONLLogger 测试通过")
    return True


def test_route_logger():
    """测试 RouteLogger 路由记录器"""
    print("\n" + "=" * 50)
    print("测试 RouteLogger")
    print("=" * 50)

    log_dir = "test_logs/routes"

    # 清理测试目录
    import shutil
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

    # 创建路由记录器
    route_logger = RouteLogger(log_dir)

    # 测试保存记录
    print("\n1. 测试保存路由记录...")
    test_records = [
        {
            "text": "我想租个3000块的房子",
            "intent": {"intent_code": "budget_query", "intent_name": "预算查询"},
            "entities": [{"type": "amount", "text": "3000块", "value": 3000}],
            "confidence": 0.95,
            "mode": "rule",
            "latency_ms": 45
        },
        {
            "text": "附近有地铁吗",
            "intent": {"intent_code": "transport_query", "intent_name": "交通查询"},
            "entities": [{"type": "transport", "text": "地铁", "value": "地铁"}],
            "confidence": 0.88,
            "mode": "rule",
            "latency_ms": 32
        },
        {
            "text": "可以养宠物吗",
            "intent": {"intent_code": "pet_policy", "intent_name": "宠物政策"},
            "entities": [{"type": "pet", "text": "宠物", "value": "宠物"}],
            "confidence": 0.92,
            "mode": "llm",
            "latency_ms": 120
        }
    ]

    for record in test_records:
        route_logger.save(**record)

    route_logger.flush()
    print(f"  ✓ 保存 {len(test_records)} 条路由记录")

    # 测试查询
    print("\n2. 测试查询...")
    records = route_logger.query(limit=10)
    print(f"  ✓ 查询到 {len(records)} 条记录")

    # 测试统计
    print("\n3. 测试统计...")
    stats = route_logger.get_stats(days=1)
    print(f"  总请求数: {stats['total_requests']}")
    print(f"  平均置信度: {stats['average_confidence']}")
    print(f"  平均延迟: {stats['average_latency_ms']}ms")
    print(f"  Top意图: {stats['top_intents']}")
    print("  ✓ 统计功能正常")

    # 测试准确率统计
    print("\n4. 测试准确率统计...")
    accuracy = route_logger.get_intent_accuracy(days=1)
    print(f"  高置信度: {accuracy['high_confidence']['count']} ({accuracy['high_confidence']['percentage']}%)")
    print(f"  中置信度: {accuracy['medium_confidence']['count']} ({accuracy['medium_confidence']['percentage']}%)")
    print(f"  低置信度: {accuracy['low_confidence']['count']} ({accuracy['low_confidence']['percentage']}%)")
    print("  ✓ 准确率统计正常")

    route_logger.close()
    print("\n✅ RouteLogger 测试通过")
    return True


def test_performance():
    """测试性能"""
    print("\n" + "=" * 50)
    print("测试性能")
    print("=" * 50)

    log_dir = "test_logs/perf"

    # 清理测试目录
    import shutil
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

    route_logger = RouteLogger(log_dir)

    # 测试写入性能
    print("\n1. 测试写入性能...")
    count = 1000
    start = time.time()

    for i in range(count):
        route_logger.save(
            text=f"测试文本 {i}",
            intent={"intent_code": "test"},
            confidence=0.9,
            latency_ms=50
        )

    route_logger.flush()
    elapsed = time.time() - start

    print(f"  写入 {count} 条记录")
    print(f"  总耗时: {elapsed:.2f}s")
    print(f"  平均: {elapsed/count*1000:.2f}ms/条")
    print(f"  吞吐量: {count/elapsed:.0f} 条/秒")
    print("  ✓ 性能测试完成")

    route_logger.close()
    print("\n✅ 性能测试通过")
    return True


def test_archiver():
    """测试归档功能"""
    print("\n" + "=" * 50)
    print("测试 LogArchiver")
    print("=" * 50)

    log_dir = "test_logs/archive"

    # 清理测试目录
    import shutil
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

    # 创建一些测试文件
    os.makedirs(log_dir, exist_ok=True)

    # 创建今天的日志
    today = datetime.now().strftime("%Y-%m-%d")
    with open(os.path.join(log_dir, f"routes_{today}.jsonl"), "w") as f:
        f.write('{"test": "today"}\n')

    # 创建10天前的日志
    old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    with open(os.path.join(log_dir, f"routes_{old_date}.jsonl"), "w") as f:
        f.write('{"test": "old"}\n')

    print("\n1. 测试归档...")
    archiver = LogArchiver(log_dir, compress_after_days=7)
    result = archiver.archive_old_logs()

    print(f"  归档文件数: {result['archived_count']}")
    print(f"  跳过文件数: {result['skipped_count']}")
    print(f"  错误数: {result['error_count']}")
    print("  ✓ 归档完成")

    print("\n2. 测试统计...")
    stats = archiver.get_archive_stats()
    print(f"  活跃文件数: {len(stats['active_files'])}")
    print(f"  归档文件数: {len(stats['archived_files'])}")
    print("  ✓ 统计完成")

    print("\n✅ LogArchiver 测试通过")
    return True


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("JSONL 功能测试套件")
    print("=" * 50)

    tests = [
        ("JSONLLogger", test_jsonl_logger),
        ("RouteLogger", test_route_logger),
        ("性能测试", test_performance),
        ("LogArchiver", test_archiver),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 清理测试目录
    print("\n" + "=" * 50)
    print("清理测试数据...")
    if os.path.exists("test_logs"):
        import shutil
        shutil.rmtree("test_logs")
    print("✓ 清理完成")

    # 打印结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")

    return all(r for _, r in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
