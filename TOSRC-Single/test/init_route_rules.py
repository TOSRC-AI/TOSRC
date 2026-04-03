#!/usr/bin/env python3
"""
初始化路由规则，将现有rules.yaml的规则全部导入数据库，完全消除yaml硬编码
"""
import sqlite3
import os
import yaml

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "data/bionic_kg.db")
RULES_YAML_PATH = os.path.join(os.path.dirname(__file__), "config/rules.yaml")

def init_route_rules():
    # 读取现有yaml规则
    with open(RULES_YAML_PATH, 'r', encoding='utf-8') as f:
        rules_data = yaml.safe_load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空现有规则
    cursor.execute("DELETE FROM route_rule")
    
    inserted_count = 0
    for rule in rules_data['rules']:
        # 处理pattern，数组转逗号分隔字符串
        pattern = ','.join(rule['pattern']) if isinstance(rule['pattern'], list) else rule['pattern']
        
        # 处理entity_patterns，转成JSON字符串
        import json
        entity_patterns = json.dumps(rule['entity_patterns'], ensure_ascii=False) if rule.get('entity_patterns') else '{}'
        
        try:
            cursor.execute('''
            INSERT INTO route_rule (
                rule_id, name, intent, match_type, pattern, priority, confidence, 
                enabled, route_to, response_type, entity_patterns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule['id'],
                rule['name'],
                rule['intent'],
                rule['match_type'],
                pattern,
                rule['priority'],
                rule['confidence'],
                1 if rule['enabled'] else 0,
                rule['action']['route_to'],
                rule['action']['response_type'],
                entity_patterns
            ))
            inserted_count += 1
        except sqlite3.IntegrityError:
            # 已存在，跳过
            pass
    
    conn.commit()
    conn.close()
    
    print(f"✅ 路由规则初始化完成")
    print(f"   共导入规则：{inserted_count} 条")
    print(f"   规则来源：{RULES_YAML_PATH}")
    print(f"   现在可以删除rules.yaml文件，规则完全从数据库读取")

if __name__ == "__main__":
    init_route_rules()
