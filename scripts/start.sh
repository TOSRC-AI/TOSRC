#!/bin/bash
# TOSRC 一键启动脚本
# 支持开发模式、生产模式、调试模式

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# TOSRC-Single 目录
SINGLE_DIR="$PROJECT_ROOT/TOSRC-Single"

cd "$SINGLE_DIR"

# 默认配置
HOST="0.0.0.0"
PORT="8080"
MODE="dev"
WORKERS=1

# 打印帮助信息
print_help() {
    echo -e "${BLUE}TOSRC 启动脚本${NC}"
    echo ""
    echo "用法: ./scripts/start.sh [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -p, --port PORT     设置服务端口 (默认: 8080)"
    echo "  -m, --mode MODE     启动模式: dev/prod/debug (默认: dev)"
    echo "  -w, --workers NUM   工作进程数 (仅生产模式有效, 默认: 1)"
    echo "  --reload            启用热重载 (开发模式)"
    echo ""
    echo "示例:"
    echo "  ./scripts/start.sh                          # 开发模式启动"
    echo "  ./scripts/start.sh -m prod -p 8000          # 生产模式启动"
    echo "  ./scripts/start.sh -m debug                 # 调试模式启动"
    echo ""
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_help
            exit 0
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        --reload)
            RELOAD=1
            shift
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            print_help
            exit 1
            ;;
    esac
done

# 检查端口是否被占用
check_port() {
    if lsof -Pi :"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}错误: 端口 $PORT 已被占用${NC}"
        echo "请使用 -p 参数指定其他端口"
        exit 1
    fi
}

# 检查 Python 环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误: 未找到 python3${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}Python 版本: $PYTHON_VERSION${NC}"
}

# 检查并创建虚拟环境
setup_venv() {
    VENV_PATH="$PROJECT_ROOT/.venv"

    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${YELLOW}创建虚拟环境...${NC}"
        python3 -m venv "$VENV_PATH"
    fi

    # 激活虚拟环境
    source "$VENV_PATH/bin/activate"

    # 升级 pip
    pip install --quiet --upgrade pip

    echo -e "${GREEN}虚拟环境已激活${NC}"
}

# 安装依赖
install_deps() {
    echo -e "${YELLOW}检查依赖...${NC}"

    # 检查 requirements.txt 是否更新
    if [ ! -f "$PROJECT_ROOT/.requirements_installed" ] || [ "$SINGLE_DIR/requirements.txt" -nt "$PROJECT_ROOT/.requirements_installed" ]; then
        echo -e "${YELLOW}安装依赖...${NC}"
        pip install --quiet -r "$SINGLE_DIR/requirements.txt"
        touch "$PROJECT_ROOT/.requirements_installed"
        echo -e "${GREEN}依赖安装完成${NC}"
    else
        echo -e "${GREEN}依赖已是最新${NC}"
    fi
}

# 设置环境变量
setup_env() {
    echo -e "${YELLOW}配置环境变量...${NC}"

    # 加载 .env 文件（从项目根目录）
    if [ -f "$PROJECT_ROOT/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
        echo -e "${GREEN}已加载 .env 文件${NC}"
    fi

    # 设置默认值
    export ADMIN_API_KEY="${ADMIN_API_KEY:-admin-llm-router-2026}"
    export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000,http://localhost:8080}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"

    # 数据目录
    export DATA_DIR="${DATA_DIR:-$SINGLE_DIR/data}"
    mkdir -p "$DATA_DIR"

    echo -e "${GREEN}环境变量配置完成${NC}"
    echo -e "  ${BLUE}ADMIN_API_KEY:${NC} ${ADMIN_API_KEY:0:4}...${ADMIN_API_KEY: -4}"
    echo -e "  ${BLUE}CORS_ORIGINS:${NC} $CORS_ORIGINS"
    echo -e "  ${BLUE}LOG_LEVEL:${NC} $LOG_LEVEL"
}

# 预启动检查
pre_check() {
    echo -e "${YELLOW}执行预启动检查...${NC}"

    # 检查必要的目录
    mkdir -p "$SINGLE_DIR/logs"
    mkdir -p "$SINGLE_DIR/data/database"

    # 检查配置文件
    CONFIG_DIR="$SINGLE_DIR/data/config"
    if [ ! -f "$CONFIG_DIR/global_config.json" ]; then
        echo -e "${RED}错误: 全局配置文件不存在${NC}"
        echo "  路径: $CONFIG_DIR/global_config.json"
        exit 1
    fi

    echo -e "${GREEN}预启动检查完成${NC}"
}

# 打印启动信息
print_startup_info() {
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}    TOSRC 服务启动中...${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""
    echo -e "  ${BLUE}模式:${NC}    $MODE"
    echo -e "  ${BLUE}主机:${NC}    $HOST"
    echo -e "  ${BLUE}端口:${NC}    $PORT"
    echo -e "  ${BLUE}工作进程:${NC} $WORKERS"
    echo ""
    echo -e "  ${YELLOW}管理后台:${NC} http://localhost:$PORT/admin/"
    echo -e "  ${YELLOW}API 文档:${NC} http://localhost:$PORT/docs"
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo ""
}

# 启动服务
start_service() {
    print_startup_info

    case $MODE in
        dev)
            # 开发模式
            if [ "$RELOAD" = "1" ]; then
                uvicorn main:app --host "$HOST" --port "$PORT" --reload --log-level debug
            else
                uvicorn main:app --host "$HOST" --port "$PORT" --log-level info
            fi
            ;;
        prod)
            # 生产模式
            echo -e "${YELLOW}以生产模式启动...${NC}"
            uvicorn main:app --host "$HOST" --port "$PORT" \
                --workers "$WORKERS" \
                --log-level warning \
                --access-log \
                --proxy-headers
            ;;
        debug)
            # 调试模式
            echo -e "${YELLOW}以调试模式启动...${NC}"
            export LOG_LEVEL="DEBUG"
            uvicorn main:app --host "$HOST" --port "$PORT" \
                --reload \
                --log-level debug \
                --access-log
            ;;
        *)
            echo -e "${RED}错误: 未知模式 '$MODE'${NC}"
            echo "可选模式: dev, prod, debug"
            exit 1
            ;;
    esac
}

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}正在关闭服务...${NC}"
    # 可以在这里添加清理逻辑
    exit 0
}

# 捕获中断信号
trap cleanup SIGINT SIGTERM

# 主流程
main() {
    echo -e "${BLUE}TOSRC 启动脚本 v1.0${NC}"
    echo ""

    check_port
    check_python
    setup_venv
    install_deps
    setup_env
    pre_check
    start_service
}

# 运行主流程
main
