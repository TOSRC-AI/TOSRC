#!/usr/bin/env python3
"""
初始化实体关键词表，导入房源相关实体规则
"""
import sqlite3
import os

# 房源实体关键词配置（按照行业实体设计.md定义）
entity_keywords = {
    # 房源基本信息
    "house_base": {
        "户型": ["一室一厅", "两室一厅", "三室一厅", "一居室", "两居室", "三居室", "单间", "loft", "复式", "开间"],
        "面积": ["平", "平米", "平方", "㎡", "平方米", "多大面积", "多少平"],
        "楼层": ["一楼", "二楼", "三楼", "四楼", "五楼", "六楼", "七楼", "八楼", "九楼", "十楼", "低层", "中层", "高层", "底层", "顶楼"],
        "朝向": ["朝南", "朝北", "朝东", "朝西", "南北通透", "朝南向", "朝北向", "朝东向", "朝西向", "南向", "北向", "东向", "西向"],
        "装修": ["精装修", "简装修", "毛坯", "豪华装修", "中等装修", "精装", "简装", "新装", "旧装修"]
    },
    # 位置小区
    "location_community": {
        "城市": ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "西安", "南京"],
        "商圈": ["中关村", "国贸", "望京", "西二旗", "上地", "亦庄", "通州", "昌平", "朝阳", "海淀"],
        "地铁": ["地铁", "地铁站", "号线", "站", "地铁口", "近地铁", "临地铁"],
        "小区": ["小区", "社区", "公寓", "花园", "苑", "里", "园", "庭", "苑"]
    },
    # 室内设施
    "indoor_facility": {
        "卫生间": ["卫生间", "洗手间", "厕所", "独卫", "独立卫生间", "公用卫生间", "公卫", "主卫", "次卫"],
        "阳台": ["阳台", "露台", "带阳台", "无阳台"],
        "厨房": ["厨房", "开放式厨房", "燃气", "天然气"],
        "家电": ["空调", "冰箱", "洗衣机", "电视", "热水器", "油烟机", "燃气灶", "微波炉", "烤箱", "加湿器", "净化器"],
        "家具": ["床", "衣柜", "沙发", "茶几", "餐桌", "椅子", "书桌", "电视柜"]
    },
    # 租赁信息
    "rent_info": {
        "租金": ["元", "块", "钱", "多少钱", "房租", "租金", "价位", "价格", "费用"],
        "租赁方式": ["整租", "合租", "短租", "长租", "月租", "年租", "押一付一", "押一付三", "付三押一", "付一押一"]
    },
    # 房源条件
    "house_condition": {
        "采光": ["采光", "阳光", "光线", "向阳"],
        "通风": ["通风", "通透", "风大", "空气好"],
        "安静": ["安静", "不吵", "噪音小", "隔音好"],
        "私密性": ["私密", "私密性好", "独立"]
    },
    # 限制要求
    "limit_requirement": {
        "养宠物": ["养宠物", "宠物", "猫", "狗", "可以养猫", "可以养狗"],
        "做饭": ["做饭", "厨房可用", "可以做饭", "能做饭"]
    }
}

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "data/bionic_kg.db")

def init_entity_keywords():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空现有数据（如果有）
    cursor.execute("DELETE FROM entity_keyword")
    
    # 插入所有实体关键词
    inserted_count = 0
    for entity_type, entities in entity_keywords.items():
        for entity_name, keywords in entities.items():
            for keyword in keywords:
                try:
                    cursor.execute(
                        "INSERT INTO entity_keyword (entity_type, entity_name, keyword, weight, is_active) VALUES (?, ?, ?, ?, ?)",
                        (entity_type, entity_name, keyword, 1.0, 1)
                    )
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    # 已经存在，跳过
                    pass
    
    conn.commit()
    conn.close()
    
    print(f"✅ 实体关键词初始化完成，共插入 {inserted_count} 条关键词记录")
    print(f"   涉及实体类型：{len(entity_keywords)} 个")
    print(f"   覆盖实体名称：{sum(len(v) for v in entity_keywords.values())} 个")

if __name__ == "__main__":
    init_entity_keywords()
