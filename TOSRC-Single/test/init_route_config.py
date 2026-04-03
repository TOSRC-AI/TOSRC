#!/usr/bin/env python3
"""
初始化数据库中的路由配置
"""
import sys
sys.path.append('/Volumes/1T/ai_project/ai-llm-router')

from src.bionic.db import bionic_db

def init_routes():
    """初始化路由配置到数据库"""
    print("=== 初始化路由配置 ===")
    
    route_configs = [
        ("租房", "租房查询", "租房查询", "房屋租赁服务大模型"),
        ("租房", "房源报修", "房源报修", "物业服务大模型"),
        ("天气", "天气查询", "天气查询", "天气服务大模型"),
        ("生活服务", "缴费查询", "缴费查询", "生活缴费服务大模型"),
        ("生活服务", "投诉建议", "投诉建议", "客户服务大模型")
    ]
    
    added = 0
    updated = 0
    
    for scene_id, intent_id, intent_name, route_target in route_configs:
        # 先更新路由目标
        if bionic_db.update_intent_route_target(intent_id, route_target):
            updated += 1
            print(f"✅ 更新路由: {intent_id} → {route_target}")
        else:
            # 不存在则添加
            if bionic_db.add_intent_neuron(scene_id, intent_id, intent_name, route_target=route_target):
                added += 1
                print(f"✅ 添加路由: {intent_id} → {route_target}")
    
    print(f"\n🏆 初始化完成: 新增{added}条，更新{updated}条路由配置")
    
    # 验证
    print("\n📋 当前所有路由配置:")
    routes = bionic_db.get_all_route_mappings()
    for intent_id, route_target in routes.items():
        print(f"  {intent_id}: {route_target}")
    
    print("\n✅ 路由配置已全部存储到数据库，无需硬编码！")
    print("  支持动态更新路由，修改后调用reload_route_config()立即生效，无需重启服务")

if __name__ == "__main__":
    init_routes()