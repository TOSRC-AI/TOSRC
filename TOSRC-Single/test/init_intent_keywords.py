#!/usr/bin/env python3
"""
初始化意图关键词表，将现有硬编码的关键词全部导入数据库
"""
import sqlite3
import os

# 现有硬编码的关键词，一次性导入到数据库
intent_keyword_map = {
    # request类
    "request": ["帮我", "请", "需要", "要", "麻烦", "帮忙", "快点", "赶紧", "立即", "马上", "请求", "要求", "给我", "帮我查", "帮我看", "请帮我", "麻烦你", "请你", "需要你"],
    "request_action": ["打开", "关闭", "调整", "设置", "修改", "删除", "重启", "刷新", "切换", "执行"],
    "request_provide": ["给我", "发我", "提供", "告诉我", "给个", "发一下"],
    "request_help": ["帮我", "帮忙", "求助", "帮个忙", "帮一下"],
    
    # question类
    "question": ["吗", "怎么", "为什么", "多少", "在哪", "什么", "如何", "怎样", "咋", "何时", "何地", "何人", "是不是", "对不对", "有没有", "能不能", "可以吗", "多少钱", "多大", "多久"],
    
    # inform类
    "inform": ["是", "有", "带", "包含", "属于", "确实", "对的", "没错", "是的", "我有", "我是", "这里有", "房间有", "包含了", "状态是", "情况是", "事实是"],
    "inform_fact": ["有", "是", "包含", "带", "属于", "状态是", "事实是"],
    
    # emotion类
    "emotion": ["喜欢", "讨厌", "满意", "开心", "生气", "感谢", "抱歉", "太好了", "太棒了", "很差", "不好", "非常好", "我很", "感觉", "觉得", "高兴", "难过", "担心", "害怕"],
    "emotion_positive": ["喜欢", "满意", "开心", "太好了", "很棒", "很好", "非常好", "认可", "同意", "支持"],
    
    # social类
    "social": ["你好", "您好", "谢谢", "再见", "拜拜", "麻烦了", "打扰了", "辛苦了", "不好意思", "抱歉打扰", "哈喽", "hi", "hello", "在吗"],
    
    # narrative类
    "narrative": ["当时", "之前", "昨天", "前天", "上周", "上个月", "我刚才", "我之前", "事情是这样的", "之前我", "昨天我", "当时我", "有一次", "记得"]
}

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "data/bionic_kg.db")

def init_keywords():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空现有数据（如果有）
    cursor.execute("DELETE FROM intent_keyword")
    
    # 插入所有关键词
    inserted_count = 0
    for intent_code, keywords in intent_keyword_map.items():
        for keyword in keywords:
            try:
                cursor.execute(
                    "INSERT INTO intent_keyword (intent_code, keyword, weight, is_active) VALUES (?, ?, ?, ?)",
                    (intent_code, keyword, 1.0, 1)
                )
                inserted_count += 1
            except sqlite3.IntegrityError:
                # 已经存在，跳过
                pass
    
    conn.commit()
    conn.close()
    
    print(f"✅ 意图关键词初始化完成，共插入 {inserted_count} 条关键词记录")
    print(f"   涉及意图数量：{len(intent_keyword_map)} 个")

if __name__ == "__main__":
    init_keywords()
