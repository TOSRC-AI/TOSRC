#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时自动测试脚本
功能：定时运行批量测试，保存历史结果，分析准确率变化趋势
"""
import os
import sys
import json
import time
import schedule
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import matplotlib.pyplot as plt
from test_batch import BatchTester, load_test_cases_from_file

# 配置
TEST_CASE_FILE = "test_cases_house_rent.json"  # 默认测试用例文件
TEST_INTERVAL_MINUTES = 60  # 测试间隔，单位分钟
HISTORY_DIR = "./test_reports/history"  # 历史结果保存目录
TREND_REPORT_PATH = "./test_reports/accuracy_trend.html"  # 趋势报告路径

# 确保目录存在
os.makedirs(HISTORY_DIR, exist_ok=True)

class TestScheduler:
    def __init__(self, test_case_file: str = TEST_CASE_FILE):
        self.test_case_file = test_case_file
        self.tester = BatchTester()
        # 加载测试用例
        self.test_cases = load_test_cases_from_file(test_case_file)
        print(f"加载测试用例：{test_case_file}，共 {len(self.test_cases)} 个用例")
    
    def run_test(self) -> Dict[str, Any]:
        """运行一次测试并保存结果"""
        print(f"\n=== 开始定时测试，时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        
        # 运行测试
        self.tester.run_all_tests()
        self.tester.generate_report()
        
        # 获取统计结果
        total = len(self.tester.results)
        passed = sum(1 for r in self.tester.results if r["是否通过"])
        route_correct = sum(1 for r in self.tester.results if "实际路由" in r and r["实际路由"] == r["预期路由"])
        intent_correct = sum(1 for r in self.tester.results if "实际意图" in r and r["实际意图"] == r["预期意图"])
        entity_correct = sum(
            1 for r in self.tester.results 
            if all(
                (e["type"], e["text"]) in {(ae["type"], ae["text"]) for ae in r.get("实际实体", [])} 
                for e in r["预期实体"]
            )
        )
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_cases": total,
            "passed": passed,
            "overall_accuracy": round(passed / total * 100, 2),
            "route_accuracy": round(route_correct / total * 100, 2),
            "intent_accuracy": round(intent_correct / total * 100, 2),
            "entity_accuracy": round(entity_correct / total * 100, 2),
            "low_confidence_count": len(self.tester.low_confidence_samples),
            "failed_cases": [
                {"input": r["输入"], "error": r["错误信息"]} 
                for r in self.tester.results if not r["是否通过"]
            ]
        }
        
        # 保存历史结果
        history_file = f"{HISTORY_DIR}/test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"测试完成，总体准确率：{stats['overall_accuracy']}%，结果已保存到：{history_file}")
        return stats
    
    def load_history_data(self) -> pd.DataFrame:
        """加载所有历史测试数据"""
        history_files = [f for f in os.listdir(HISTORY_DIR) if f.startswith("test_result_") and f.endswith(".json")]
        history_data = []
        
        for file in history_files:
            file_path = os.path.join(HISTORY_DIR, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history_data.append(data)
            except Exception as e:
                print(f"加载历史文件失败：{file}，错误：{str(e)}")
        
        if not history_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(history_data)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
        return df
    
    def generate_trend_report(self) -> str:
        """生成准确率趋势分析报告"""
        df = self.load_history_data()
        if df.empty:
            return "没有历史测试数据，无法生成趋势报告"
        
        # 生成HTML报告
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Router 测试准确率趋势报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-card h3 {{ font-size: 14px; color: #666; margin-bottom: 10px; }}
        .stat-card .value {{ font-size: 28px; font-weight: bold; color: #007bff; }}
        .chart-container {{ margin-bottom: 30px; }}
        .failed-cases {{ margin-top: 30px; }}
        .failed-cases h3 {{ margin-bottom: 15px; color: #dc3545; }}
        .case-item {{ background: #f8d7da; padding: 10px; margin-bottom: 10px; border-radius: 4px; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LLM Router 测试准确率趋势报告</h1>
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}，共 {len(df)} 次历史测试记录</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>最新总体准确率</h3>
                <div class="value">{df.iloc[-1]['overall_accuracy']}%</div>
            </div>
            <div class="stat-card">
                <h3>最新路由准确率</h3>
                <div class="value">{df.iloc[-1]['route_accuracy']}%</div>
            </div>
            <div class="stat-card">
                <h3>最新意图准确率</h3>
                <div class="value">{df.iloc[-1]['intent_accuracy']}%</div>
            </div>
            <div class="stat-card">
                <h3>最新实体准确率</h3>
                <div class="value">{df.iloc[-1]['entity_accuracy']}%</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>准确率趋势图</h3>
            <canvas id="accuracyChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>各维度准确率对比</h3>
            <canvas id="dimensionChart"></canvas>
        </div>
"""
        
        # 最新失败用例
        latest_failed = df.iloc[-1]["failed_cases"]
        if latest_failed:
            html_content += """
        <div class="failed-cases">
            <h3>最新测试失败用例</h3>
"""
            for case in latest_failed:
                html_content += f'<div class="case-item"><strong>输入：</strong>{case["input"]}<br><strong>错误：</strong>{case["error"]}</div>'
            html_content += "</div>"
        
        # 图表数据
        labels = [d.strftime("%m-%d %H:%M") for d in df["datetime"]]
        overall_data = df["overall_accuracy"].tolist()
        route_data = df["route_accuracy"].tolist()
        intent_data = df["intent_accuracy"].tolist()
        entity_data = df["entity_accuracy"].tolist()
        
        html_content += f"""
        <script>
            // 准确率趋势图
            const ctx1 = document.getElementById('accuracyChart').getContext('2d');
            new Chart(ctx1, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [
                        {{
                            label: '总体准确率 (%)',
                            data: {json.dumps(overall_data)},
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            tension: 0.3,
                            fill: true
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            min: 0,
                            max: 100,
                            title: {{
                                display: true,
                                text: '准确率 (%)'
                            }}
                        }}
                    }}
                }}
            }});
            
            // 各维度对比图
            const ctx2 = document.getElementById('dimensionChart').getContext('2d');
            new Chart(ctx2, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [
                        {{
                            label: '路由准确率 (%)',
                            data: {json.dumps(route_data)},
                            borderColor: '#28a745',
                            tension: 0.3
                        }},
                        {{
                            label: '意图准确率 (%)',
                            data: {json.dumps(intent_data)},
                            borderColor: '#ffc107',
                            tension: 0.3
                        }},
                        {{
                            label: '实体准确率 (%)',
                            data: {json.dumps(entity_data)},
                            borderColor: '#dc3545',
                            tension: 0.3
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            min: 0,
                            max: 100,
                            title: {{
                                display: true,
                                text: '准确率 (%)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </div>
</body>
</html>
"""
        
        # 保存报告
        with open(TREND_REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"趋势报告已生成：{TREND_REPORT_PATH}")
        return TREND_REPORT_PATH
    
    def run_scheduled_tests(self, interval_minutes: int = TEST_INTERVAL_MINUTES):
        """启动定时测试任务"""
        print(f"启动定时测试任务，间隔：{interval_minutes} 分钟")
        print("首次测试立即开始...")
        
        # 首次运行
        self.run_test()
        self.generate_trend_report()
        
        # 定时任务
        schedule.every(interval_minutes).minutes.do(lambda: (
            self.run_test(),
            self.generate_trend_report()
        ))
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

def main():
    import argparse
    parser = argparse.ArgumentParser(description="LLM Router 定时自动测试工具")
    parser.add_argument("-f", "--file", default=TEST_CASE_FILE, help="测试用例文件路径")
    parser.add_argument("-i", "--interval", type=int, default=TEST_INTERVAL_MINUTES, help="测试间隔（分钟）")
    parser.add_argument("-o", "--once", action="store_true", help="仅运行一次测试，不启动定时任务")
    parser.add_argument("-r", "--report", action="store_true", help="仅生成历史趋势报告，不运行测试")
    args = parser.parse_args()
    
    scheduler = TestScheduler(args.file)
    
    if args.report:
        report_path = scheduler.generate_trend_report()
        print(f"趋势报告已生成：{report_path}")
        return
    
    if args.once:
        scheduler.run_test()
        scheduler.generate_trend_report()
        return
    
    # 启动定时任务
    scheduler.run_scheduled_tests(args.interval)

if __name__ == "__main__":
    main()
