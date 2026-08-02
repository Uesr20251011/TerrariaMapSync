"""同步业务逻辑 — 上传和下载地图"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple

from git_manager import pull_repo, commit_and_push
from map_scanner import is_backup_file


def _find_map_files(worlds_path: str, base_name: str) -> dict[str, str]:
    """
    在 Worlds 文件夹中查找地图及其备份文件

    base_name: 不含扩展名的地图名，如 "我的世界"

    返回 {"wld": path, "bak": path_or_None, "bak2": path_or_None}
    """
    result = {"wld": None, "bak": None, "bak2": None}

    wld_name = f"{base_name}.wld"
    wld_path = os.path.join(worlds_path, wld_name)
    if os.path.isfile(wld_path):
        result["wld"] = wld_path

    bak_name = f"{base_name}.bak"
    bak_path = os.path.join(worlds_path, bak_name)
    if os.path.isfile(bak_path):
        result["bak"] = bak_path

    bak2_name = f"{base_name}.bak2"
    bak2_path = os.path.join(worlds_path, bak2_name)
    if os.path.isfile(bak2_path):
        result["bak2"] = bak2_path

    return result


def upload_map(worlds_path: str, cache_dir: str, map_name: str) -> Tuple[bool, str]:
    """
    上传地图到云端

    流程:
    1. 先 pull 最新
    2. 在 cache_dir 中生成 YYYYMMDD原名 副本（.wld + .bak + .bak2）
    3. git add → commit → push
    4. 删除 cache_dir 中的副本

    map_name: 不含 .wld 扩展名的地图名，如 "我的世界"
    """
    # 先拉取最新
    ok, msg = pull_repo(cache_dir)
    if not ok:
        return (False, f"拉取云端更新失败: {msg}")

    # 查找源文件
    source_files = _find_map_files(worlds_path, map_name)
    if not source_files["wld"]:
        return (False, f"未找到地图文件: {map_name}.wld")

    # 生成日期前缀
    today = datetime.now().strftime("%Y%m%d")

    # 复制到 cache_dir 并重命名
    copied_files = []
    try:
        for ext, src_path in source_files.items():
            if src_path and os.path.isfile(src_path):
                new_name = f"{today}{map_name}.{ext}"
                dst_path = os.path.join(cache_dir, new_name)
                shutil.copy2(src_path, dst_path)
                copied_files.append(new_name)

        if not copied_files:
            return (False, "没有文件可上传")

        # Git 提交推送
        message = f"上传地图 {map_name} - {today}"
        ok, msg = commit_and_push(cache_dir, copied_files, message)
        if not ok:
            return (False, msg)

        return (True, f"成功上传 {map_name} ({today})")

    finally:
        # 清理 cache_dir 中的副本
        for f in copied_files:
            f_path = os.path.join(cache_dir, f)
            try:
                if os.path.isfile(f_path):
                    os.remove(f_path)
            except OSError:
                pass


def download_map(worlds_path: str, cache_dir: str,
                 dated_wld: str, original_name: str) -> Tuple[bool, str]:
    """
    从云端下载地图到本地

    流程:
    1. 先 pull 最新
    2. 从 cache_dir 复制 dated_wld 到 worlds_path，去掉日期前缀重命名
    3. 同样处理对应的 .bak, .bak2
    4. 覆盖本地同名旧文件

    dated_wld: 如 "20260802我的世界.wld"
    original_name: 去掉日期后的文件名，如 "我的世界.wld"
    """
    # 先拉取最新
    ok, msg = pull_repo(cache_dir)
    if not ok:
        return (False, f"拉取云端更新失败: {msg}")

    # 源文件在 cache_dir 中
    src_wld = os.path.join(cache_dir, dated_wld)
    if not os.path.isfile(src_wld):
        return (False, f"云端文件不存在: {dated_wld}")

    # 目标路径（去日期前缀）
    dst_wld = os.path.join(worlds_path, original_name)
    base_name = Path(original_name).stem  # 不含扩展名的原名

    # 确保 Worlds 目录存在
    os.makedirs(worlds_path, exist_ok=True)

    copied_count = 0
    errors = []

    # 复制 .wld 文件
    try:
        shutil.copy2(src_wld, dst_wld)
        copied_count += 1
    except OSError as e:
        errors.append(f"复制 .wld 失败: {e}")

    # 处理对应的 .bak 和 .bak2 文件
    dated_prefix = Path(dated_wld).stem  # "20260802我的世界"
    for ext in ("bak", "bak2"):
        src_bak = os.path.join(cache_dir, f"{dated_prefix}.{ext}")
        dst_bak = os.path.join(worlds_path, f"{base_name}.{ext}")
        if os.path.isfile(src_bak):
            try:
                shutil.copy2(src_bak, dst_bak)
                copied_count += 1
            except OSError as e:
                errors.append(f"复制 .{ext} 失败: {e}")

    if errors:
        if copied_count > 0:
            return (True, f"部分下载成功 ({copied_count} 个文件)，但: {'; '.join(errors)}")
        return (False, f"下载失败: {'; '.join(errors)}")

    return (True, f"成功下载 {original_name}")
