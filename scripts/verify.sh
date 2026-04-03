#!/bin/bash
# TOSRC 启动前验证脚本

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SINGLE_DIR="$PROJECT_ROOT/TOSRC-Single"

echo "=================================="
echo "    TOSRC 启动前验证"
echo "=================================="
echo ""

# 检查 1: Python 版本
echo -n "检查 Python 版本... "
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} $PYTHON_VERSION"
else
    echo -e "${RED}✗ 未找到 python3${NC}"
    exit 1
fi

# 检查 2: 虚拟环境
echo -n "检查虚拟环境... "
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${GREEN}✓${NC} 已存在"
else
    echo -e "${YELLOW}!${NC} 不存在，启动时将创建"
fi

# 检查 3: 依赖
echo -n "检查依赖... "
if [ -f "$PROJECT_ROOT/.requirements_installed" ]; then
    echo -e "${GREEN}✓${NC} 已安装"
else
    echo -e "${YELLOW}!${NC} 待安装"
fi

# 检查 4: 配置文件
echo -n "检查配置文件... "
if [ -f "$SINGLE_DIR/data/config/global_config.json" ]; then
    echo -e "${GREEN}✓${NC} global_config.json 存在"
else
    echo -e "${RED}✗ 配置文件缺失${NC}"
    exit 1
fi

# 检查 5: 静态资源
echo -n "检查静态资源... "
if [ -d "$SINGLE_DIR/static" ]; then
    FILE_COUNT=$(find "$SINGLE_DIR/static" -type f | wc -l)
    echo -e "${GREEN}✓${NC} $FILE_COUNT 个文件"
else
    echo -e "${RED}✗ 静态资源目录不存在${NC}"
    exit 1
fi

# 检查 6: 数据库
echo -n "检查数据库... "
if [ -d "$SINGLE_DIR/data/database" ]; then
    DB_COUNT=$(find "$SINGLE_DIR/data/database" -name "*.db" | wc -l)
    echo -e "${GREEN}✓${NC} $DB_COUNT 个数据库"
else
    echo -e "${YELLOW}!${NC} 数据库目录待初始化"
fi

# 检查 7: 环境变量
echo -n "检查环境变量... "
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}✓${NC} .env 文件存在"
else
    echo -e "${YELLOW}!${NC} 使用默认配置"
fi

# 检查 8: 端口可用性
echo -n "检查端口 8080... "
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}✗ 已被占用${NC}"
    exit 1
else
    echo -e "${GREEN}✓${NC} 可用"
fi

# 检查 9: 模块导入测试
echo -n "测试模块导入... "
cd "$SINGLE_DIR"
if python3 -c "from src.config.loader import get_global_config; get_global_config()" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 配置模块正常"
else
    echo -e "${RED}✗ 导入失败${NC}"
    exit 1
fi

echo ""
echo "=================================="
echo -e "${GREEN}    ✓ 所有检查通过${NC}"
echo "=================================="
echo ""
echo "可以启动服务:"
echo "  ./scripts/start.sh"
echo ""
