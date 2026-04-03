#!/bin/bash
# 轻量全量自动化测试脚本
# 无依赖，直接运行，任何修改必须通过本测试才能发布

echo "============================================="
echo "🚀 开始运行LLM Router轻量全量测试"
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

# 测试API密钥
API_KEY="admin-llm-router-2026"
BASE_URL="http://localhost:8765"
PASS_COUNT=0
FAIL_COUNT=0

# 测试用例
run_test() {
    local name="$1"
    local input="$2"
    local expected_intent="$3"
    local expected_route="$4"
    local expected_entities="$5"
    
    echo -n "🧪 测试用例: $name..."
    
    response=$(curl -s -X POST "$BASE_URL/api/v1/route" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"input_text\":\"$input\"}")
    
    # 检查响应状态
    if [ $? -ne 0 ]; then
        echo " ❌ 请求失败"
        FAIL_COUNT=$((FAIL_COUNT+1))
        return
    fi
    
    # 提取返回字段
    intent=$(echo "$response" | grep -o '"intent":"[^"]*"' | cut -d'"' -f4)
    route_to=$(echo "$response" | grep -o '"route_to":"[^"]*"' | cut -d'"' -f4)
    confidence=$(echo "$response" | grep -o '"confidence":[0-9.]*' | cut -d':' -f2)
    
    # 验证核心字段
    local pass=1
    if [ "$intent" != "$expected_intent" ]; then
        echo -n " ❌ 意图错误，预期:$expected_intent，实际:$intent"
        pass=0
    fi
    
    if [ "$route_to" != "$expected_route" ]; then
        echo -n " ❌ 路由错误，预期:$expected_route，实际:$route_to"
        pass=0
    fi
    
    # 验证实体
    if [ -n "$expected_entities" ]; then
        IFS='|' read -ra ENTITIES <<< "$expected_entities"
        for entity in "${ENTITIES[@]}"; do
            if ! echo "$response" | grep -q "\"text\":\"$entity\""; then
                echo -n " ❌ 缺失实体:$entity"
                pass=0
            fi
        done
    fi
    
    if [ $pass -eq 1 ]; then
        echo " ✅ 成功"
        PASS_COUNT=$((PASS_COUNT+1))
    else
        echo ""
        FAIL_COUNT=$((FAIL_COUNT+1))
    fi
}

# 运行测试用例
run_test "天气查询-基础测试" "明天北京天气怎么样" "天气查询" "天气服务" "明天|北京"
run_test "天气查询-无地点" "明天天气怎么样" "天气查询" "天气服务" "明天"
run_test "天气查询-无时间" "北京天气怎么样" "天气查询" "天气服务" "北京"
run_test "天气预警查询" "明天北京有暴雨预警吗" "天气预警查询" "天气预警服务" "明天|北京|暴雨预警"
run_test "天气查询-口语化" "今儿个北京热不热" "天气查询" "天气服务" "今儿个|北京|热"
run_test "租房查询-基础测试" "我要租个3000元的两室一厅" "租房查询" "租房服务" "3000元|两室一厅"
run_test "房价咨询测试" "北京朝阳区两室一厅多少钱一个月" "房价咨询" "房价服务" "两室一厅"
run_test "房源报修测试" "卫生间漏水了需要报修" "房源报修" "报修服务" "卫生间|漏水"
run_test "户型咨询测试" "这个房子有多大面积" "户型咨询" "户型服务" ""
run_test "租房查询-多实体" "我想在地铁10号线附近租个朝南的一室一厅，预算5000以内" "租房查询" "租房服务" "地铁10号线|朝南|一室一厅|5000以内"
run_test "兜底测试" "今天吃什么" "" "默认大模型服务" ""

echo "============================================="
echo "📊 测试结果统计:"
echo "✅ 成功用例: $PASS_COUNT"
echo "❌ 失败用例: $FAIL_COUNT"
echo "============================================="

# 6. 停止服务
echo "🧹 停止测试服务..."
kill $SERVER_PID 2>/dev/null
rm -f test_server.log

# 7. 输出结果
if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 全部测试用例通过！可以发布"
    echo "============================================="
    exit 0
else
    echo "❌ 存在测试用例失败！禁止发布"
    echo "============================================="
    exit 1
fi
