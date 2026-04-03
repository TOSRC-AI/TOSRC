import sys
from loguru import logger
from pathlib import Path
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# 创建日志目录
Path("logs").mkdir(exist_ok=True)

# 清除默认配置
logger.remove()

# 控制台输出格式
console_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<magenta>{extra[request_id]}</magenta> | "
    "{message}"
)

# 文件输出格式
file_format = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{extra[request_id]} | "
    "{message}"
)

# 控制台日志
logger.add(
    sys.stdout,
    format=console_format,
    level="INFO",
    enqueue=True
)

# 普通日志文件，按天轮转，保留30天
logger.add(
    "logs/llm_router_{time:YYYY-MM-DD}.log",
    format=file_format,
    level="INFO",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    enqueue=True
)

# 错误日志文件
logger.add(
    "logs/error_{time:YYYY-MM-DD}.log",
    format=file_format,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    enqueue=True
)

def get_logger():
    """获取带request_id的日志实例"""
    return logger.bind(request_id=request_id_var.get())

def set_request_id(request_id: str = None):
    """设置请求ID，没有则自动生成"""
    if not request_id:
        request_id = str(uuid.uuid4()).replace("-", "")
    request_id_var.set(request_id)
    return request_id
