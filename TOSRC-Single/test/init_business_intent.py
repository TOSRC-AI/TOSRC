#!/usr/bin/env python3
"""
初始化业务意图，完全配置化，支持多行业扩展（当前先导入租房领域）
"""
import sqlite3
import os

# 租房领域业务意图（来自行业意图设计.md）
business_intents = {
    "rental": [
        {
            "code": "house_search",
            "name": "找房求租",
            "priority": 1000,
            "related_general_intent": "request,question",
            "keywords": ["我想租房", "找房子", "有没有房源", "推荐房子", "找朝南", "独卫", "整租", "合租", "短租", "长租", "月租", "两室一厅", "一室一厅", "北京房源", "上海租房"]
        },
        {
            "code": "house_consult",
            "name": "房源咨询",
            "priority": 1001,
            "related_general_intent": "question",
            "keywords": ["多大面积", "电梯房吗", "装修怎么样", "采光好不好", "小区环境", "楼层", "朝向", "面积", "有没有阳台", "有卫生间吗"]
        },
        {
            "code": "fee_consult",
            "name": "费用咨询",
            "priority": 1002,
            "related_general_intent": "question",
            "keywords": ["房租多少钱", "押金多少", "物业费", "月付", "中介费", "多少钱", "价格", "费用", "付款方式"]
        },
        {
            "code": "book_viewing",
            "name": "预约看房",
            "priority": 1003,
            "related_general_intent": "request",
            "keywords": ["我想看房", "什么时候看房", "约看房", "明天能看房吗", "取消看房", "预约看房"]
        },
        {
            "code": "apply_rent",
            "name": "申请租房",
            "priority": 1004,
            "related_general_intent": "request",
            "keywords": ["这套我要租", "怎么订房", "可以签约吗", "我想定下来", "办理入住"]
        },
        {
            "code": "lease_consult",
            "name": "租期入住咨询",
            "priority": 1005,
            "related_general_intent": "question",
            "keywords": ["什么时候入住", "可以租多久", "短租", "续租", "租期最少几个月"]
        },
        {
            "code": "limit_consult",
            "name": "居住限制咨询",
            "priority": 1006,
            "related_general_intent": "question",
            "keywords": ["可以养宠物吗", "能做饭吗", "可以合租吗", "能住几个人", "带小孩"]
        },
        {
            "code": "repair_feedback",
            "name": "报修反馈",
            "priority": 1007,
            "related_general_intent": "request,inform",
            "keywords": ["空调坏了", "马桶堵了", "停水停电", "楼上太吵", "房子漏水", "报修", "维修"]
        },
        {
            "code": "rent_transfer",
            "name": "退租转租",
            "priority": 1008,
            "related_general_intent": "request,question",
            "keywords": ["押金怎么退", "我要退租", "可以转租吗", "退租扣钱", "办理转租"]
        },
        {
            "code": "contact_staff",
            "name": "联系房东/中介",
            "priority": 1009,
            "related_general_intent": "request",
            "keywords": ["房东电话", "联系中介", "和房东沟通", "维修师傅什么时候来", "中介电话"]
        },
        {
            "code": "small_talk",
            "name": "闲聊寒暄",
            "priority": 1010,
            "related_general_intent": "social",
            "keywords": ["你好", "在吗", "谢谢", "再见", "拜拜", "没事了"]
        },
        {
            "code": "other",
            "name": "其他意图",
            "priority": 1011,
            "related_general_intent": "",
            "keywords": ["我要投诉", "怎么发布房源", "帮我换一套", "房源是真的吗", "看不懂合同"]
        }
    ]
}

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "data/bionic_kg.db")

def init_business_intents():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空现有数据（如果有）
    cursor.execute("DELETE FROM business_intent WHERE industry_code = 'rental'")
    cursor.execute("DELETE FROM business_intent_keyword WHERE industry_code = 'rental'")
    
    # 插入所有业务意图
    inserted_intent_count = 0
    inserted_keyword_count = 0
    
    for industry_code, intents in business_intents.items():
        for intent in intents:
            # 插入意图基本信息
            cursor.execute(
                "INSERT INTO business_intent (industry_code, intent_code, intent_name, priority, related_general_intent, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (industry_code, intent["code"], intent["name"], intent["priority"], intent["related_general_intent"], 1)
            )
            inserted_intent_count += 1
            
            # 插入关键词
            for keyword in intent["keywords"]:
                try:
                    cursor.execute(
                        "INSERT INTO business_intent_keyword (industry_code, intent_code, keyword, weight, is_active) VALUES (?, ?, ?, ?, ?)",
                        (industry_code, intent["code"], keyword, 1.0, 1)
                    )
                    inserted_keyword_count += 1
                except sqlite3.IntegrityError:
                    # 已经存在，跳过
                    pass
    
    conn.commit()
    conn.close()
    
    print(f"✅ 业务意图初始化完成")
    print(f"   业务类型：{len(business_intents)} 个")
    print(f"   导入业务意图：{inserted_intent_count} 个")
    print(f"   导入关键词：{inserted_keyword_count} 条")

if __name__ == "__main__":
    init_business_intents()
