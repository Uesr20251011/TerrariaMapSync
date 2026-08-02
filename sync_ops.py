"""同步业务逻辑 — 上传和下载地图"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple

from git_manager import pull_repo, commit_and_push
from map_scanner import is_backup_file
from logger import get_logger

log = get_logger()


def _find_map_files(worlds_path: str, base_name: str) -> dict:
    """
    在 Worlds 文件夹中查找地图及其备份文件

    base_name: 不含扩展名的地图名，如 "我的世界"

    返回 {"wld": path, "bak": path_or_None, "bak2": path_or_None}
    注意：备份文件后缀是 .wld.bak 和 .wld.bak2（不是 .bak）
    """
    result = {"wld": None, "bak": None, "bak2": None}

    wld_name = f"{base_name}.wld"
    wld_path = os.path.join(worlds_path, wld_name)
    if os.path.isfile(wld_path):
        result["wld"] = wld_path

    # 泰拉瑞亚的备份文件命名为: 地图名.wld.bak 和 地图名.wld.bak2
    bak_name = f"{base_name}.wld.bak"
    bak_path = os.path.join(worlds_path, bak_name)
    if os.path.isfile(bak_path):
        result["bak"] = bak_path

    bak2_name = f"{base_name}.wld.bak2"
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
    log.info("========== 开始上传地图 ==========")
    log.info("地图名: %s, 源路径: %s", map_name, worlds_path)

    # 先拉取最新
    log.info("步骤1: 拉取最新...")
    ok, msg = pull_repo(cache_dir)
    if not ok:
        log.error("拉取失败: %s", msg)
        return (False, f"拉取云端更新失败: {msg}")

    # 查找源文件
    source_files = _find_map_files(worlds_path, map_name)
    if not source_files["wld"]:
        log.error("未找到地图文件: %s.wld", map_name)
        return (False, f"未找到地图文件: {map_name}.wld")
    log.info("找到源文件: wld=%s, bak=%s, bak2=%s",
             bool(source_files["wld"]), bool(source_files["bak"]), bool(source_files["bak2"]))

    # 生成日期前缀
    today = datetime.now().strftime("%Y%m%d")
    log.info("步骤2: 复制文件，日期前缀: %s", today)

    # 后缀映射: dict key -> 实际文件后缀
    _ext_map = {"wld": "wld", "bak": "wld.bak", "bak2": "wld.bak2"}

    copied_files = []
    try:
        for ext, src_path in source_files.items():
            if src_path and os.path.isfile(src_path):
                real_ext = _ext_map.get(ext, ext)
                new_name = f"{today}{map_name}.{real_ext}"
                dst_path = os.path.join(cache_dir, new_name)
                file_size = os.path.getsize(src_path)
                log.info("  复制: %s -> %s (%d bytes)", src_path, new_name, file_size)
                shutil.copy2(src_path, dst_path)
                copied_files.append(new_name)

        if not copied_files:
            log.error("没有文件可上传")
            return (False, "没有文件可上传")

        log.info("步骤3: 提交推送 %d 个文件...", len(copied_files))
        message = f"上传地图 {map_name} - {today}"
        ok, msg = commit_and_push(cache_dir, copied_files, message)
        if not ok:
            log.error("提交推送失败: %s", msg)
            return (False, msg)

        # 推送成功后 reset 工作区，让新文件在目录中可见
        log.info("步骤4: 同步工作区...")
        import subprocess as _sp
        _sp.run(["git", "reset", "--hard", "HEAD"], cwd=cache_dir,
                capture_output=True, timeout=10, creationflags=0x08000000)

        log.info("========== 上传成功 ==========")
        return (True, f"成功上传 {map_name} ({today})")

    finally:
        # 清理未跟踪的临时文件
        log.info("清理临时文件...")
        for f in copied_files:
            f_path = os.path.join(cache_dir, f)
            try:
                if os.path.isfile(f_path):
                    # 文件已被 git 跟踪则 reset 已恢复它，无需删
                    log.debug("  跳过: %s (已跟踪)", f)
            except OSError as e:
                log.warning("  删除失败: %s - %s", f, e)


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

    # 处理对应的备份文件（.wld.bak 和 .wld.bak2）
    dated_prefix = Path(dated_wld).stem  # "20260802我的世界"
    for ext in ("wld.bak", "wld.bak2"):
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
