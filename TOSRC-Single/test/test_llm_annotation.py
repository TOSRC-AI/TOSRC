#!/usr/bin/env python3
"""测试DeepSeek标注功能"""
import json
from src.core.llm_annotator import llm_annotator

# 测试文本
text = "咨询的这套朝阳小区80平的房源，客服回复特别及时，清晰告知我租金2200元、押一付三，没有任何隐藏报价，讲解得很透明，特别靠谱！"
scene = "rental"

print(f"测试文本: {text}")
print("调用LLM标注...")

annotation = llm_annotator.annotate(text, scene)
if annotation:
    print("\n✅ 标注成功:")
    print(json.dumps(annotation, indent=2, ensure_ascii=False))
    # 查看保存的标注文件
    import os
    scene_dir = os.path.join("data", "annotations", scene)
    files = sorted(os.listdir(scene_dir))
    if files:
        latest_file = os.path.join(scene_dir, files[-1])
        print(f"\n✅ 标注结果已保存到: {latest_file}")
else:
    print("\n❌ 标注失败，请检查API Key配置")
