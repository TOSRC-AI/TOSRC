#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量测试脚本
功能：批量测试路由/意图/实体识别准确率，自动生成测试报告
"""
import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import List, Dict, Any
import csv

# 配置
API_BASE_URL = "http://localhost:8765"
API_KEY = "admin-llm-router-2026"  # 替换为实际API Key
TEST_REPORTS_DIR = "./test_reports"
LOW_CONFIDENCE_THRESHOLD = 0.8  # 低于该置信度的样本自动收集

# 测试用例清单
TEST_CASES = [
    # 天气查询类
    {
        "input": "明天北京天气怎么样", 
        "expect_route": "weather_service", 
        "expect_intent": "weather_query",
        "expect_entities": [
            {"type": "TIME", "text": "明天"},
            {"type": "LOCATION", "text": "北京"}
        ]
    },
    {
        "input": "上海下周一会下雨吗", 
        "expect_route": "weather_service", 
        "expect_intent": "weather_query",
        "expect_entities": [
            {"type": "TIME", "text": "下周一"},
            {"type": "LOCATION", "text": "上海"}
        ]
    },
    {
        "input": "今天广州气温多少度", 
        "expect_route": "weather_service", 
        "expect_intent": "weather_query",
        "expect_entities": [
            {"type": "TIME", "text": "今天"},
            {"type": "LOCATION", "text": "广州"}
        ]
    },
    # 时间查询类
    {
        "input": "现在几点了", 
        "expect_route": "time_service", 
        "expect_intent": "time_query",
        "expect_entities": []
    },
    {
        "input": "明天是几号", 
        "expect_route": "time_service", 
        "expect_intent": "time_query",
        "expect_entities": [
            {"type": "TIME", "text": "明天"}
        ]
    },
    {
        "input": "昨天星期几", 
        "expect_route": "time_service", 
        "expect_intent": "time_query",
        "expect_entities": [
            {"type": "TIME", "text": "昨天"}
        ]
    },
    # 股票查询类
    {
        "input": "贵州茅台今天股价多少", 
        "expect_route": "stock_service", 
        "expect_intent": "stock_query",
        "expect_entities": [
            {"type": "STOCK", "text": "贵州茅台"}
        ]
    },
    {
        "input": "腾讯的港股行情", 
        "expect_route": "stock_service", 
        "expect_intent": "stock_query",
        "expect_entities": [
            {"type": "STOCK", "text": "腾讯"}
        ]
    },
    {
        "input": "苹果美股现在多少钱", 
        "expect_route": "stock_service", 
        "expect_intent": "stock_query",
        "expect_entities": [
            {"type": "STOCK", "text": "苹果"}
        ]
    },
    # 新闻查询类
    {
        "input": "今天有什么新闻", 
        "expect_route": "news_service", 
        "expect_intent": "news_query",
        "expect_entities": [
            {"type": "TIME", "text": "今天"}
        ]
    },
    {
        "input": "科技头条有什么消息", 
        "expect_route": "news_service", 
        "expect_intent": "news_query",
        "expect_entities": []
    },
    # 闲聊类
    {
        "input": "你好", 
        "expect_route": "chat_service", 
        "expect_intent": "chat",
        "expect_entities": []
    },
    {
        "input": "讲个笑话吧", 
        "expect_route": "chat_service", 
        "expect_intent": "chat",
        "expect_entities": []
    },
    {
        "input": "早上好", 
        "expect_route": "chat_service", 
        "expect_intent": "chat",
        "expect_entities": []
    },
    # 默认路由类（规则未覆盖）
    {
        "input": "推荐一首好听的歌", 
        "expect_route": "default_llm_service", 
        "expect_intent": "other",
        "expect_entities": []
    },
    {
        "input": "我要订机票", 
        "expect_route": "default_llm_service", 
        "expect_intent": "other",
        "expect_entities": []
    }
]

class BatchTester:
    def __init__(self):
        self.results = []
        self.low_confidence_samples = []
        self.start_time = None
        self.end_time = None
    
    def test_single_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """测试单个用例"""
        input_text = case["input"]
        result = {
            "输入": input_text,
            "预期路由": case["expect_route"],
            "预期意图": case["expect_intent"],
            "预期实体": case.get("expect_entities", []),
            "是否通过": True,
            "错误信息": []
        }
        
        try:
            start_time = time.time()
            # 调用路由接口
            resp = requests.post(
                f"{API_BASE_URL}/api/v1/route",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                },
                json={"input_text": input_text},
                timeout=5
            )
            resp.raise_for_status()
            resp_data = resp.json()
            
            if resp_data["code"] != 200:
                result["是否通过"] = False
                result["错误信息"].append(f"接口返回错误：{resp_data.get('message', '未知错误')}")
                return result
            
            route_data = resp_data["data"]
            total_time = (time.time() - start_time) * 1000
            
            # 验证路由
            actual_route = route_data["route_to"]
            if actual_route != case["expect_route"]:
                result["是否通过"] = False
                result["错误信息"].append(f"路由不匹配：预期={case['expect_route']}，实际={actual_route}")
            
            # 验证意图
            actual_intent = route_data.get("intent", "")
            if not actual_intent:
                # 路由接口没有返回意图，调用独立意图接口
                intent_resp = requests.post(
                    f"{API_BASE_URL}/api/v1/intent",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": API_KEY
                    },
                    json={"input_text": input_text},
                    timeout=5
                )
                intent_data = intent_resp.json()["data"]
                actual_intent = intent_data["intent"]
                intent_confidence = intent_data["confidence"]
                intent_time = intent_data["response_time"]
            else:
                intent_confidence = route_data.get("confidence", 0)
                intent_time = 0
            
            if actual_intent != case["expect_intent"]:
                result["是否通过"] = False
                result["错误信息"].append(f"意图不匹配：预期={case['expect_intent']}，实际={actual_intent}")
            
            # 验证实体
            actual_entities = route_data.get("entities", [])
            if not actual_entities and case.get("expect_entities", []):
                # 路由接口没有返回实体，调用独立实体接口
                entity_resp = requests.post(
                    f"{API_BASE_URL}/api/v1/entity",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": API_KEY
                    },
                    json={"input_text": input_text},
                    timeout=5
                )
                entity_data = entity_resp.json()["data"]
                actual_entities = entity_data["entities"]
                entity_time = entity_data["response_time"]
            else:
                entity_time = 0
            
            # 实体匹配验证（只验证实体类型和文本，忽略顺序）
            expect_entities = case.get("expect_entities", [])
            if expect_entities:
                actual_entity_set = {(e["type"], e["text"]) for e in actual_entities}
                expect_entity_set = {(e["type"], e["text"]) for e in expect_entities}
                if not expect_entity_set.issubset(actual_entity_set):
                    result["是否通过"] = False
                    missing = expect_entity_set - actual_entity_set
                    result["错误信息"].append(f"实体缺失：{missing}")
            
            # 补充结果信息
            result["实际路由"] = actual_route
            result["实际意图"] = actual_intent
            result["意图置信度"] = intent_confidence
            result["实际实体"] = actual_entities
            result["总响应时间"] = round(total_time, 2)
            result["意图响应时间"] = intent_time
            result["实体响应时间"] = entity_time
            
            # 收集低置信度样本
            if intent_confidence < LOW_CONFIDENCE_THRESHOLD:
                self.low_confidence_samples.append({
                    "input": input_text,
                    "intent": actual_intent,
                    "confidence": intent_confidence,
                    "route": actual_route
                })
                
        except Exception as e:
            result["是否通过"] = False
            result["错误信息"].append(f"请求异常：{str(e)}")
        
        return result
    
    def run_all_tests(self) -> None:
        """运行所有测试用例"""
        self.start_time = datetime.now()
        print(f"批量测试开始，共 {len(TEST_CASES)} 个用例，开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 100)
        
        for i, case in enumerate(TEST_CASES, 1):
            print(f"[{i}/{len(TEST_CASES)}] 测试：{case['input'][:30]}...", end=" ")
            result = self.test_single_case(case)
            self.results.append(result)
            
            if result["是否通过"]:
                print("✅ 通过")
            else:
                print(f"❌ 失败：{result['错误信息']}")
        
        self.end_time = datetime.now()
        print("-" * 100)
        print(f"批量测试结束，结束时间：{self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时：{(self.end_time - self.start_time).total_seconds():.2f} 秒")
    
    def generate_report(self) -> None:
        """生成测试报告"""
        # 统计结果
        total = len(self.results)
        passed = sum(1 for r in self.results if r["是否通过"])
        failed = total - passed
        accuracy = passed / total * 100
        
        # 统计各维度准确率
        route_correct = sum(1 for r in self.results if "实际路由" in r and r["实际路由"] == r["预期路由"])
        intent_correct = sum(1 for r in self.results if "实际意图" in r and r["实际意图"] == r["预期意图"])
        entity_correct = sum(
            1 for r in self.results 
            if all(
                (e["type"], e["text"]) in {(ae["type"], ae["text"]) for ae in r.get("实际实体", [])} 
                for e in r["预期实体"]
            )
        )
        
        route_accuracy = route_correct / total * 100
        intent_accuracy = intent_correct / total * 100
        entity_accuracy = entity_correct / total * 100
        
        # 生成报告文件名
        report_time = self.start_time.strftime("%Y%m%d_%H%M%S")
        json_report_path = f"{TEST_REPORTS_DIR}/test_report_{report_time}.json"
        html_report_path = f"{TEST_REPORTS_DIR}/test_report_{report_time}.html"
        
        # 保存JSON报告
        report_data = {
            "统计信息": {
                "总用例数": total,
                "通过数": passed,
                "失败数": failed,
                "总体准确率": round(accuracy, 2),
                "路由准确率": round(route_accuracy, 2),
                "意图准确率": round(intent_accuracy, 2),
                "实体准确率": round(entity_accuracy, 2),
                "开始时间": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "结束时间": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "总耗时": round((self.end_time - self.start_time).total_seconds(), 2)
            },
            "低置信度样本": self.low_confidence_samples,
            "详细结果": self.results
        }
        
        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # 保存低置信度样本
        if self.low_confidence_samples:
            low_conf_path = f"{TEST_REPORTS_DIR}/low_confidence_samples_{report_time}.json"
            with open(low_conf_path, "w", encoding="utf-8") as f:
                json.dump(self.low_confidence_samples, f, ensure_ascii=False, indent=2)
            print(f"低置信度样本已保存到：{low_conf_path}")
        
        # 生成HTML报告
        html_content = self._generate_html_report(report_data)
        with open(html_report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 打印统计结果
        print("\n" + "=" * 50)
        print("测试统计结果：")
        print(f"总用例数：{total}")
        print(f"通过：{passed}，失败：{failed}")
        print(f"总体准确率：{accuracy:.2f}%")
        print(f"路由准确率：{route_accuracy:.2f}%")
        print(f"意图准确率：{intent_accuracy:.2f}%")
        print(f"实体准确率：{entity_accuracy:.2f}%")
        print(f"\nJSON报告已保存到：{json_report_path}")
        print(f"HTML报告已保存到：{html_report_path}")
        print("=" * 50)
    
    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """生成HTML格式报告"""
        stats = report_data["统计信息"]
        results = report_data["详细结果"]
        
        # 状态样式映射
        status_style = {
            True: "background-color: #d4edda; color: #155724;",
            False: "background-color: #f8d7da; color: #721c24;"
        }
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Router 批量测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-card h3 {{ font-size: 14px; color: #666; margin-bottom: 10px; }}
        .stat-card .value {{ font-size: 28px; font-weight: bold; color: #007bff; }}
        .low-confidence {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .passed {{ color: #28a745; font-weight: bold; }}
        .failed {{ color: #dc3545; font-weight: bold; }}
        .error {{ color: #dc3545; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LLM Router 批量测试报告</h1>
            <p>测试时间：{stats['开始时间']} 至 {stats['结束时间']}，总耗时：{stats['总耗时']} 秒</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>总用例数</h3>
                <div class="value">{stats['总用例数']}</div>
            </div>
            <div class="stat-card">
                <h3>通过数</h3>
                <div class="value" style="color: #28a745;">{stats['通过数']}</div>
            </div>
            <div class="stat-card">
                <h3>失败数</h3>
                <div class="value" style="color: #dc3545;">{stats['失败数']}</div>
            </div>
            <div class="stat-card">
                <h3>总体准确率</h3>
                <div class="value">{stats['总体准确率']}%</div>
            </div>
            <div class="stat-card">
                <h3>路由准确率</h3>
                <div class="value">{stats['路由准确率']}%</div>
            </div>
            <div class="stat-card">
                <h3>意图准确率</h3>
                <div class="value">{stats['意图准确率']}%</div>
            </div>
            <div class="stat-card">
                <h3>实体准确率</h3>
                <div class="value">{stats['实体准确率']}%</div>
            </div>
        </div>
"""
        # 低置信度样本
        if self.low_confidence_samples:
            html += f"""
        <div class="low-confidence">
            <h3>⚠️ 低置信度样本（< {LOW_CONFIDENCE_THRESHOLD * 100}%）</h3>
            <p>共 {len(self.low_confidence_samples)} 个，建议补充规则优化</p>
            <ul>
                {''.join([f'<li>{s["input"]} -> 意图：{s["intent"]}（置信度：{s["confidence"]*100:.1f}%）</li>' for s in self.low_confidence_samples])}
            </ul>
        </div>
"""
        
        # 详细结果表格
        html += """
        <h3>详细测试结果</h3>
        <table>
            <thead>
                <tr>
                    <th>序号</th>
                    <th>输入内容</th>
                    <th>预期路由</th>
                    <th>实际路由</th>
                    <th>预期意图</th>
                    <th>实际意图</th>
                    <th>置信度</th>
                    <th>响应时间</th>
                    <th>结果</th>
                    <th>错误信息</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for i, result in enumerate(results, 1):
            status_class = "passed" if result["是否通过"] else "failed"
            error_msg = "<br>".join(result["错误信息"]) if result["错误信息"] else ""
            confidence = f"{result.get('意图置信度', 0)*100:.1f}%" if result.get("意图置信度") else "-"
            response_time = f"{result.get('总响应时间', 0)}ms" if result.get("总响应时间") else "-"
            
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{result['输入']}</td>
                    <td>{result['预期路由']}</td>
                    <td>{result.get('实际路由', '-')}</td>
                    <td>{result['预期意图']}</td>
                    <td>{result.get('实际意图', '-')}</td>
                    <td>{confidence}</td>
                    <td>{response_time}</td>
                    <td class="{status_class}">{"✅ 通过" if result["是否通过"] else "❌ 失败"}</td>
                    <td class="error">{error_msg}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        return html

def load_test_cases_from_file(file_path: str) -> List[Dict[str, Any]]:
    """从文件加载测试用例，支持JSON/CSV格式"""
    if file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif file_path.endswith(".csv"):
        cases = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                case = {
                    "input": row["input"],
                    "expect_route": row["expect_route"],
                    "expect_intent": row["expect_intent"],
                    "expect_entities": json.loads(row.get("expect_entities", "[]"))
                }
                cases.append(case)
        return cases
    else:
        raise ValueError("不支持的文件格式，仅支持JSON/CSV")

if __name__ == "__main__":
    # 支持从命令行传入测试用例文件
    import argparse
    parser = argparse.ArgumentParser(description="LLM Router 批量测试脚本")
    parser.add_argument("-f", "--file", help="测试用例文件路径（JSON/CSV格式）")
    args = parser.parse_args()
    
    tester = BatchTester()
    
    if args.file:
        TEST_CASES = load_test_cases_from_file(args.file)
        print(f"加载测试用例文件：{args.file}，共 {len(TEST_CASES)} 个用例")
    
    tester.run_all_tests()
    tester.generate_report()
