#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步6大类意图字典到数据库，自动去重，已存在的不会重复添加
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bionic.db import bionic_db

# 完整的6大类意图体系，按照优先级从高到低排序
# 优先级数值规则：数值越小优先级越高
# 100~199: request类（最高）
# 200~299: question类
# 300~399: inform类
# 400~499: emotion类
# 500~599: social类
# 600~699: narrative类（最低）
intent_hierarchy = {
    "request": {
        "name": "请求/指令",
        "priority": 100,
        "children": [
            ("request_action", "要求操作、控制、执行", 101),
            ("request_provide", "请求提供资料、物品、信息", 102),
            ("request_help", "求助、帮忙", 103),
            ("request_urge", "催促、加快处理", 104),
            ("request_service", "预约、办理、报修、售后", 105),
            ("request_aftersale", "报修、投诉、售后处理", 106),
            ("request_book", "预约、预订、安排时间", 107),
            ("request_negotiate", "议价、商量、讨价还价", 108),
            ("request_modify", "修改、调整、更换", 109),
            ("request_demand", "提出要求、强调条件", 110),
            ("request_permission", "请求许可、征求同意", 111),
            ("request_feedback", "要求回复、回应", 112),
            ("request_cancel", "取消、中止、撤回", 113),
            ("request_stop", "停止、取消、关闭", 114)
        ]
    },
    "question": {
        "name": "询问/疑问",
        "priority": 200,
        "children": [
            ("query_confirm", "确认、核实、是不是", 201),
            ("query_info", "查询信息、定义、情况", 202),
            ("query_price", "询问价格、费用", 203),
            ("query_availability", "询问有无、是否可提供", 204),
            ("query_condition", "询问条件、要求、限制", 205),
            ("query_time", "询问时间、时段、期限", 206),
            ("query_location", "询问地点、位置、地址", 207),
            ("query_method", "询问方法、怎么做、流程", 208),
            ("query_reason", "询问原因、为什么", 209),
            ("query_choice", "询问选择、建议、推荐", 210),
            ("query_opinion", "询问看法、评价、感受", 211),
            ("query_intention", "询问打算、计划、目的", 212)
        ]
    },
    "inform": {
        "name": "告知/陈述",
        "priority": 300,
        "children": [
            ("inform_confirm", "确认信息、核实、肯定答复", 301),
            ("inform_fact", "陈述事实、状态、结果", 302),
            ("inform_progress", "同步进度、告知进展", 303),
            ("inform_availability", "说明有无、是否可提供", 304),
            ("inform_condition", "陈述条件、限定要求", 305),
            ("inform_announce", "宣布决定、说明计划", 306),
            ("inform_explain", "解释、说明、科普", 307),
            ("inform_opinion", "表达观点、评价、判断", 308),
            ("inform_background", "交代背景、补充前情", 309),
            ("inform_remind", "提醒、警示、通知", 310),
            ("inform_correct", "纠正错误、更正信息", 311),
            ("inform_request_refuse", "陈述拒绝、说明无法满足", 312)
        ]
    },
    "emotion": {
        "name": "表达情绪/态度",
        "priority": 400,
        "children": [
            ("emotion_thank_apology", "感谢、道歉、抱歉", 401),
            ("emotion_negative", "不满、生气、烦躁、失望", 402),
            ("emotion_complain", "抱怨、吐槽、发牢骚", 403),
            ("emotion_worry", "担心、焦虑、害怕", 404),
            ("emotion_surprise_negative", "意外差、被坑、离谱", 405),
            ("emotion_sad", "难过、失落、可惜", 406),
            ("emotion_regret", "后悔、遗憾", 407),
            ("emotion_hesitate", "犹豫、纠结、拿不定主意", 408),
            ("emotion_reserve", "保留意见、暂不表态、观望", 409),
            ("emotion_polite_refuse", "委婉拒绝、客气回绝", 410),
            ("emotion_positive", "满意、开心、赞美、认同", 411),
            ("emotion_hope_expect", "期待、盼望、想要、希望", 412),
            ("emotion_relief", "放心、安心、踏实", 413),
            ("emotion_surprise_positive", "惊喜、超出预期", 414),
            ("emotion_agree_accept", "同意、接受、可以", 415)
        ]
    },
    "social": {
        "name": "社交寒暄/礼仪",
        "priority": 500,
        "children": [
            ("social_greet", "问候、打招呼", 501),
            ("social_farewell", "告别、结束对话", 502),
            ("social_polite", "客套、礼貌用语、客气话", 503),
            ("social_comfort", "安慰、安抚、共情", 504),
            ("social_encourage", "鼓励、打气", 505),
            ("social_chat", "闲聊、开启话题", 506)
        ]
    },
    "narrative": {
        "name": "叙事/描述",
        "priority": 600,
        "children": [
            ("narrative_state", "描述状态、状况、现状", 601),
            ("narrative_object", "描写物品、人物、外观", 602),
            ("narrative_scene", "描写场景、环境、景物", 603),
            ("narrative_process", "叙述步骤、过程、动作", 604),
            ("narrative_feeling", "描述主观感受、体验", 605),
            ("narrative_story", "讲述经历、故事、回忆", 606)
        ]
    }
}

def sync_intent_dict():
    """同步意图字典到数据库，自动去重"""
    added_count = 0
    skipped_count = 0
    
    with bionic_db.get_connection(write=True) as conn:
        cursor = conn.cursor()
        
        for parent_code, parent_info in intent_hierarchy.items():
            # 插入一级意图
            cursor.execute('''
                INSERT OR IGNORE INTO intent_dict 
                (intent_level, intent_code, intent_name, parent_code, priority, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (1, parent_code, parent_info["name"], None, parent_info["priority"], 1))
            
            if cursor.rowcount > 0:
                added_count += 1
                print(f"✅ 新增一级意图：{parent_code} - {parent_info['name']} (优先级:{parent_info['priority']})")
            else:
                # 已存在的话更新优先级
                cursor.execute('''
                    UPDATE intent_dict 
                    SET priority = ?, intent_name = ?
                    WHERE intent_code = ?
                ''', (parent_info["priority"], parent_info["name"], parent_code))
                skipped_count += 1
                print(f"ℹ️ 一级意图已存在：{parent_code} - {parent_info['name']} (优先级已更新为:{parent_info['priority']})")
            
            # 插入二级意图
            for (child_code, child_name, child_priority) in parent_info["children"]:
                cursor.execute('''
                    INSERT OR IGNORE INTO intent_dict 
                    (intent_level, intent_code, intent_name, parent_code, priority, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (2, child_code, child_name, parent_code, child_priority, 1))
                
                if cursor.rowcount > 0:
                    added_count += 1
                    print(f"✅ 新增二级意图：{child_code} - {child_name} (优先级:{child_priority})")
                else:
                    # 已存在的话更新优先级
                    cursor.execute('''
                        UPDATE intent_dict 
                        SET priority = ?, intent_name = ?
                        WHERE intent_code = ?
                    ''', (child_priority, child_name, child_code))
                    skipped_count += 1
                    print(f"ℹ️ 二级意图已存在：{child_code} - {child_name} (优先级已更新为:{child_priority})")
        
        conn.commit()
    
    print(f"\n🎉 同步完成！新增：{added_count} 个，已存在跳过：{skipped_count} 个")
    print(f"当前数据库总意图数：一级6个，二级共 {sum([len(v['children']) for v in intent_hierarchy.values()])} 个")

if __name__ == "__main__":
    sync_intent_dict()
