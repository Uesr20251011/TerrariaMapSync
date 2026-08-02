"""地图扫描模块 — 本地和云端地图发现、文件名解析、分组"""

import os
import re
from pathlib import Path
from typing import Optional

# 匹配 YYYYMMDD+原名 格式: "20260802我的世界.wld"
DATED_PATTERN = re.compile(r"^(\d{8})(.+)$")


def parse_dated_filename(filename: str) -> Optional[tuple[str, str]]:
    """
    解析日期前缀文件名，返回 (date_str, original_name) 或 None

    >>> parse_dated_filename("20260802我的世界.wld")
    ('20260802', '我的世界.wld')
    >>> parse_dated_filename("我的世界.wld")
    None
    """
    # 去掉路径前缀，只取文件名
    name = os.path.basename(filename)
    match = DATED_PATTERN.match(name)
    if match:
        date_str = match.group(1)
        original_name = match.group(2)
        # 基本校验：日期应该看起来合理
        if len(date_str) == 8 and date_str.isdigit():
            return (date_str, original_name)
    return None


def is_world_file(filename: str) -> bool:
    """判断是否为 .wld 文件（排除 .bak, .bak2）"""
    name = os.path.basename(filename)
    return name.lower().endswith(".wld")


def is_backup_file(filename: str) -> bool:
    """判断是否为备份文件 (.bak / .bak2)"""
    name = os.path.basename(filename)
    lower = name.lower()
    return lower.endswith(".bak") or lower.endswith(".bak2")


def scan_local_maps(worlds_path: str) -> list[str]:
    """
    扫描本地 Worlds 文件夹中的地图
    只返回 .wld 文件名列表（不含路径，不含备份文件）
    本地文件没有日期前缀 — 直接返回文件名
    """
    path = Path(worlds_path)
    if not path.exists() or not path.is_dir():
        return []

    maps = []
    for f in path.iterdir():
        if f.is_file() and is_world_file(f.name):
            # 本地地图不会有日期前缀，直接添加
            maps.append(f.name)

    maps.sort()
    return maps


def scan_remote_maps(repo_cache_dir: str) -> dict[str, list[dict]]:
    """
    扫描本地 Git 缓存仓库中的云端地图

    解析 YYYYMMDD原名.wld 格式，按原名分组，每组内按日期降序排序
    同时查找对应的 .bak, .bak2 文件

    返回结构:
    {
        "我的世界": [
            {"date": "20260802", "wld": "20260802我的世界.wld",
             "bak": "20260802我的世界.bak", "bak2": "20260802我的世界.bak2"},
            ...
        ],
        ...
    }
    """
    path = Path(repo_cache_dir)
    if not path.exists() or not path.is_dir():
        return {}

    # 收集所有文件
    all_files = [f.name for f in path.iterdir() if f.is_file() and not f.name.startswith(".")]

    # 只处理 .wld 文件，后续再匹配 .bak/.bak2
    wld_files = [f for f in all_files if is_world_file(f)]
    maps_by_name: dict[str, list[dict]] = {}

    for wld_file in wld_files:
        parsed = parse_dated_filename(wld_file)
        if parsed is None:
            continue

        date_str, original_name = parsed
        # original_name 包含 .wld 后缀，提取纯地图名
        base_name = Path(original_name).stem  # 去掉 .wld

        # 查找对应的备份文件
        dated_prefix = f"{date_str}{base_name}"
        bak_file = f"{dated_prefix}.bak" if f"{dated_prefix}.bak" in all_files else None
        bak2_file = f"{dated_prefix}.bak2" if f"{dated_prefix}.bak2" in all_files else None

        entry = {
            "date": date_str,
            "wld": wld_file,
            "bak": bak_file,
            "bak2": bak2_file,
        }

        if base_name not in maps_by_name:
            maps_by_name[base_name] = []
        maps_by_name[base_name].append(entry)

    # 每组内按日期降序排序（最新在前）
    for name in maps_by_name:
        maps_by_name[name].sort(key=lambda x: x["date"], reverse=True)

    # 按原名排序
    return dict(sorted(maps_by_name.items()))
