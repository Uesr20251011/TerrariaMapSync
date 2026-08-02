"""配置管理模块 — 读写 %APPDATA%\TerrariaMapHelper\config.json"""

import json
import os
from pathlib import Path

APP_NAME = "TerrariaMapHelper"


def _get_config_dir() -> Path:
    """获取配置目录路径，不存在则创建"""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    config_dir = Path(appdata) / APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _get_config_path() -> Path:
    return _get_config_dir() / "config.json"


def _get_default_worlds_path() -> str:
    """推测默认的泰拉瑞亚 Worlds 文件夹路径"""
    documents = os.path.join(os.environ.get("USERPROFILE", ""), "Documents")
    fallback = os.path.join(documents, "My Games", "Terraria", "Worlds")
    if os.path.isdir(fallback):
        return fallback
    return ""


def load_config() -> dict:
    """加载配置，不存在或损坏时返回默认值"""
    config_path = _get_config_path()
    defaults = {
        "worlds_path": _get_default_worlds_path(),
        "repo_url": "",
        "repo_cache_dir": str(_get_config_dir() / "repo-cache"),
    }

    if not config_path.exists():
        return defaults

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # 合并，确保所有 key 都有值
        for key, val in defaults.items():
            if key not in saved:
                saved[key] = val
        return saved
    except (json.JSONDecodeError, OSError):
        return defaults


def save_config(config: dict) -> None:
    """保存配置到文件"""
    config_path = _get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
