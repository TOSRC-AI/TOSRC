#!/usr/bin/env python3
"""
系统性能压测脚本
测试接口QPS、响应时间、并发性能
"""
import asyncio
import aiohttp
import time
import json
from statistics import mean, median, stdev
from typing import List, Dict

# 压测配置
BASE_URL = "http://127.0.0.1:8081"
API_KEY = "admin-llm-router-2026"
CONCURRENCY = 50  # 并发数
TOTAL_REQUESTS = 1000  # 总请求数
TIMEOUT = 10  # 超时时间

# 测试用例
TEST_CASES = [
    {"input_text": "预算3000元租两室一厅", "expected_intent": "租房查询"},
    {"input_text": "明天上海天气怎么样", "expected_intent": "天气查询"},
    {"input_text": "我家热水器坏了麻烦来修一下", "expected_intent": "房源报修"},
    {"input_text": "查一下这个月的水费是多少", "expected_intent": "缴费查询"},
    {"input_text": "投诉物业卫生打扫不干净", "expected_intent": "投诉建议"},
    {"input_text": "有没有地铁附近的房子，价格在2500左右", "expected_intent": "租房查询"},
    {"input_text": "周末会不会下雨啊", "expected_intent": "天气查询"},
    {"input_text": "空调不制冷了怎么处理", "expected_intent": "房源报修"},
    {"input_text": "电费什么时候交", "expected_intent": "缴费查询"},
    {"input_text": "建议小区增加健身设施", "expected_intent": "投诉建议"}
]

class PerformanceTester:
    def __init__(self):
        self.results = []
        self.errors = []
        self.start_time = None
        self.end_time = None
    
    async def send_request(self, session, test_case):
        """发送单个请求"""
        try:
            start = time.time()
            async with session.post(
                f"{BASE_URL}/api/v1/route",
                headers={
                    "X-API-Key": API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "input_text": test_case["input_text"],
                    "user_id": "stress_test_user"
                },
                timeout=TIMEOUT
            ) as response:
                end = time.time()
                response_time = (end - start) * 1000  # 转换为ms
                
                if response.status == 200:
                    result = await response.json()
                    success = result["code"] == 200 and "intent" in result["data"] and result["data"]["intent"] == test_case["expected_intent"]
                    if not success:
                        self.errors.append({
                            "case": test_case,
                            "status": response.status,
                            "error": f"业务错误: code={result['code']}, intent={result['data'].get('intent')}",
                            "response_time": response_time
                        })
                    self.results.append({
                        "success": success,
                        "response_time": response_time,
                        "status": response.status
                    })
                    return success
                else:
                    error_text = await response.text()
                    self.errors.append({
                        "case": test_case,
                        "status": response.status,
                        "error": f"HTTP错误: {error_text[:200]}",
                        "response_time": response_time
                    })
                    return False
                    
        except Exception as e:
            self.errors.append({
                "case": test_case,
                "error": str(e)
            })
            return False
    
    async def worker(self, session, queue):
        """工作协程"""
        while not queue.empty():
            test_case = await queue.get()
            await self.send_request(session, test_case)
            queue.task_done()
    
    async def run_test(self):
        """运行压测"""
        print(f"🚀 开始性能压测")
        print(f"配置：并发数={CONCURRENCY}，总请求数={TOTAL_REQUESTS}，测试用例数={len(TEST_CASES)}")
        
        self.start_time = time.time()
        
        # 创建请求队列
        queue = asyncio.Queue()
        for i in range(TOTAL_REQUESTS):
            test_case = TEST_CASES[i % len(TEST_CASES)]
            await queue.put(test_case)
        
        # 创建并发任务
        async with aiohttp.ClientSession() as session:
            workers = [asyncio.create_task(self.worker(session, queue)) for _ in range(CONCURRENCY)]
            await queue.join()
            
            # 取消所有worker
            for worker in workers:
                worker.cancel()
        
        self.end_time = time.time()
        self.print_report()
    
    def print_report(self):
        """输出压测报告"""
        total_time = self.end_time - self.start_time
        total_requests = len(self.results) + len(self.errors)
        successful = len([r for r in self.results if r["success"]])
        failed = len(self.errors) + len([r for r in self.results if not r["success"]])
        
        response_times = [r["response_time"] for r in self.results]
        
        print(f"\n📊 性能压测报告")
        print("=" * 60)
        print(f"总运行时间: {total_time:.2f}s")
        print(f"总请求数: {total_requests}")
        print(f"成功请求: {successful} ({successful/total_requests*100:.2f}%)")
        print(f"失败请求: {failed} ({failed/total_requests*100:.2f}%)")
        print(f"QPS: {total_requests / total_time:.2f} 请求/秒")
        print("\n⏱️  响应时间统计（毫秒）:")
        if response_times:
            print(f"  平均: {mean(response_times):.2f}ms")
            print(f"  中位数: {median(response_times):.2f}ms")
            print(f"  最小: {min(response_times):.2f}ms")
            print(f"  最大: {max(response_times):.2f}ms")
            if len(response_times) > 1:
                print(f"  标准差: {stdev(response_times):.2f}ms")
            # 百分位
            response_times.sort()
            p50 = response_times[int(len(response_times)*0.5)]
            p90 = response_times[int(len(response_times)*0.9)]
            p95 = response_times[int(len(response_times)*0.95)]
            p99 = response_times[int(len(response_times)*0.99)]
            print(f"\n  P50: {p50:.2f}ms")
            print(f"  P90: {p90:.2f}ms")
            print(f"  P95: {p95:.2f}ms")
            print(f"  P99: {p99:.2f}ms")
        
        if self.errors:
            print(f"\n❌ 错误信息（前5条）:")
            for i, err in enumerate(self.errors[:5]):
                status = err.get('status', 'N/A')
                error_msg = err.get('error', f'Status: {status}')
                print(f"  {i+1}. {error_msg}")
        
        print("=" * 60)
        
        # 性能评估
        print("\n🏆 性能评估:")
        qps = total_requests / total_time
        avg_rt = mean(response_times) if response_times else 0
        if qps >= 200 and avg_rt < 50:
            print("✅ 性能优秀：QPS≥200，平均响应时间<50ms")
        elif qps >= 100 and avg_rt < 100:
            print("🟡 性能良好：QPS≥100，平均响应时间<100ms")
        else:
            print("🔴 性能需要优化：QPS较低或响应时间较长")
            print("💡 优化方向：")
            print("  1. 增加缓存命中率")
            print("  2. 优化数据库查询")
            print("  3. 减少不必要的计算")
            print("  4. 优化正则匹配效率")

if __name__ == "__main__":
    tester = PerformanceTester()
    asyncio.run(tester.run_test())