#!/bin/bash
# 快速测试启动脚本

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT/TOSRC-Single"

echo "启动 TOSRC 服务测试..."
echo ""

# 激活虚拟环境（如果存在）
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "虚拟环境已激活"
fi

# 设置环境变量
export ADMIN_API_KEY="test-api-key-12345"
export CORS_ORIGINS="http://localhost:3000,http://localhost:8080"
export LOG_LEVEL="INFO"

echo "环境变量设置完成"
echo "  ADMIN_API_KEY: ${ADMIN_API_KEY:0:5}..."
echo ""
echo "启动服务: http://localhost:8080"
echo "管理后台: http://localhost:8080/admin/"
echo "API 文档: http://localhost:8080/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8080 --log-level info
