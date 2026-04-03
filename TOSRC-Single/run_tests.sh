#!/bin/bash
# 全量自动化测试脚本
# 任何修改必须通过本脚本所有测试才能发布

echo "============================================="
echo "🚀 开始运行LLM Router全量自动化测试"
echo "============================================="

# 1. 清理端口
echo "📦 清理8765端口占用..."
lsof -i :8765 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 2

# 2. 启动测试服务
echo "🔧 启动测试服务..."
source .venv/bin/activate
python main.py > test_server.log 2>&1 &
SERVER_PID=$!
echo "服务PID: $SERVER_PID"

# 3. 等待服务启动
echo "⏳ 等待服务启动完成..."
sleep 5

# 4. 检查服务是否启动成功
curl -s http://localhost:8765/health > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 服务启动失败，日志如下："
    cat test_server.log
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✅ 服务启动成功，开始运行测试用例"
echo "============================================="

# 5. 运行pytest测试
pytest test/ -v --tb=short
TEST_EXIT_CODE=$?

echo "============================================="
echo "🧹 停止测试服务..."
kill $SERVER_PID 2>/dev/null
rm -f test_server.log

# 6. 输出测试结果
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ 全部测试用例通过！可以发布"
    exit 0
else
    echo "❌ 存在测试用例失败！禁止发布"
    exit 1
fi
