#!/usr/bin/env python3
"""
测试SQLiteDataManager工具库功能
"""
import sys
sys.path.append('.')
from src.db.sqlite_manager import sqlite_manager
import json

def test_sqlite_manager():
    print("=== 测试SQLiteDataManager功能 ===")
    
    # 测试1: 插入数据
    print("\n🚀 测试1: 插入数据")
    insert_result = sqlite_manager.insert(
        "intent_rules",
        {
            "intent_name": "测试意图",
            "keyword": "测试关键词",
            "priority": 2
        }
    )
    print(f"插入结果: {insert_result}")
    assert insert_result["status"] == "success", "插入失败"
    test_id = insert_result["id"]
    
    # 测试2: 查询单条数据
    print("\n🚀 测试2: 查询单条数据")
    result = sqlite_manager.query_one("intent_rules", {"id": test_id})
    print(f"查询结果: {result}")
    assert result["intent_name"] == "测试意图", "查询结果错误"
    
    # 测试3: 更新数据
    print("\n🚀 测试3: 更新数据")
    update_result = sqlite_manager.update(
        "intent_rules",
        {"priority": 5, "keyword": "更新后的关键词"},
        {"id": test_id}
    )
    print(f"更新结果: {update_result}")
    assert update_result["status"] == "success", "更新失败"
    
    # 验证更新
    updated = sqlite_manager.query_one("intent_rules", {"id": test_id})
    assert updated["priority"] == 5, "更新后数据错误"
    assert updated["keyword"] == "更新后的关键词", "更新后数据错误"
    
    # 测试4: 查询多条数据
    print("\n🚀 测试4: 查询多条数据")
    sqlite_manager.insert("intent_rules", {"intent_name": "测试意图2", "keyword": "关键词2"})
    sqlite_manager.insert("intent_rules", {"intent_name": "测试意图2", "keyword": "关键词3"})
    
    results = sqlite_manager.query_many("intent_rules", {"intent_name": "测试意图2"})
    print(f"查询到{len(results)}条数据")
    assert len(results) >= 2, "多条查询失败"
    
    # 测试5: 批量插入
    print("\n🚀 测试5: 批量插入")
    batch_data = [
        {"intent_name": "批量测试", "keyword": "批量关键词1"},
        {"intent_name": "批量测试", "keyword": "批量关键词2"},
        {"intent_name": "批量测试", "keyword": "批量关键词3"}
    ]
    batch_result = sqlite_manager.batch_insert("intent_rules", batch_data)
    print(f"批量插入结果: {batch_result}")
    assert batch_result["success"] == 3, "批量插入失败"
    
    # 测试6: 逻辑删除（规则表）
    print("\n🚀 测试6: 逻辑删除")
    delete_result = sqlite_manager.delete("intent_rules", {"id": test_id})
    print(f"删除结果: {delete_result}")
    assert delete_result["status"] == "success", "删除失败"
    
    # 验证逻辑删除
    deleted = sqlite_manager.query_one("intent_rules", {"id": test_id})
    assert deleted["is_active"] == 0, "逻辑删除失败"
    
    # 测试7: 自定义SQL查询
    print("\n🚀 测试7: 自定义SQL查询")
    custom_result = sqlite_manager.execute_custom_sql(
        "SELECT COUNT(*) as total FROM intent_rules WHERE is_active = 1"
    )
    print(f"有效规则总数: {custom_result[0]['total']}")
    assert custom_result[0]["total"] > 0, "自定义SQL查询失败"
    
    # 测试8: 版本记录检查
    print("\n🚀 测试8: 版本记录检查")
    versions = sqlite_manager.query_many("rule_versions", {"table_name": "intent_rules"}, limit=5)
    print(f"规则版本记录数: {len(versions)}")
    assert len(versions) >= 3, "版本记录失败"  # 插入、更新、删除各一次
    
    # 清理测试数据
    print("\n🧹 清理测试数据")
    sqlite_manager.execute_custom_sql(
        "DELETE FROM intent_rules WHERE intent_name LIKE '%测试%'",
        write=True
    )
    sqlite_manager.execute_custom_sql(
        "DELETE FROM rule_versions WHERE table_name = 'intent_rules'",
        write=True
    )
    
    print("\n✅ 所有测试通过！SQLiteDataManager功能正常")
    return True

if __name__ == "__main__":
    test_sqlite_manager()