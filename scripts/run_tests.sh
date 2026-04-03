#!/bin/bash
# TOSRC 测试运行脚本

set -e

cd "$(dirname "$0")/../TOSRC-Single"

echo "================================"
echo "   TOSRC 测试套件"
echo "================================"
echo ""

# 检查 pytest
if ! command -v pytest &> /dev/null; then
    echo "正在安装 pytest..."
    pip install pytest pytest-cov
fi

# 运行参数
TEST_PATH=${1:-"tests/unit"}
COVERAGE=${2:-"true"}

echo "测试路径: $TEST_PATH"
echo "覆盖率检查: $COVERAGE"
echo ""

# 运行测试
if [ "$COVERAGE" = "true" ]; then
    pytest "$TEST_PATH" \
        -v \
        --tb=short \
        --cov=src \
        --cov-report=term-missing \
        --cov-report=html:htmlcov
else
    pytest "$TEST_PATH" -v --tb=short
fi

echo ""
echo "================================"
echo "   测试完成"
echo "================================"
