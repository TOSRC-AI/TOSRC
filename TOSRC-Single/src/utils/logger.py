"""
日志工具模块，统一管理日志配置，支持JSON格式和滚动存储
"""
import logging
from logging.handlers import RotatingFileHandler
import json
import os
from datetime import datetime, timezone
from src.config.loader import get_global_config

class JsonFormatter(logging.Formatter):
    """JSON格式日志格式化器，便于日志收集分析"""
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", "unknown")
        }
        return json.dumps(log_record, ensure_ascii=False)

def get_logger(name="TOSRC-Single") -> logging.Logger:
    """获取配置完善的日志器（全局唯一）"""
    global_config = get_global_config()
    log_path = global_config["service"]["log_path"]
    
    os.makedirs(log_path, exist_ok=True)
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s  | %(module)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)

    # 文件滚动输出（最大100MB，保留5个备份）
    file_handler = RotatingFileHandler(
        os.path.join(log_path, "tosrc_single.log"),
        maxBytes=100 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(JsonFormatter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# 对外提供全局日志实例（全项目统一使用）
logger = get_logger()