"""统一日志模块"""

import logging
import os
from datetime import datetime
from pathlib import Path

_LOG_DIR = os.path.join(os.environ.get("APPDATA", ""), "TerrariaMapHelper", "logs")
_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """获取全局 logger"""
    global _logger
    if _logger is not None:
        return _logger

    os.makedirs(_LOG_DIR, exist_ok=True)

    log_file = os.path.join(_LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")

    _logger = logging.getLogger("TerrariaMapHelper")
    _logger.setLevel(logging.DEBUG)

    # 文件 handler — 详细日志
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    _logger.addHandler(fh)

    # 控制台 handler — 简要日志
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _logger.addHandler(ch)

    _logger.info(f"日志文件: {log_file}")
    return _logger


def log_path() -> str:
    """返回当前日志文件路径"""
    return os.path.join(_LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")
