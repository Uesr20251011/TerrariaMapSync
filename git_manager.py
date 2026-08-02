"""Git 操作模块 — clone, pull, commit, push"""

import subprocess
from pathlib import Path
from typing import Tuple


def is_git_installed() -> bool:
    """检测系统是否安装了 Git"""
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_git(args: list[str], cwd: str) -> Tuple[bool, str]:
    """执行 git 命令，返回 (success, message)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
        )
        if result.returncode == 0:
            output = result.stdout.strip() or result.stderr.strip() or "成功"
            return (True, output)
        else:
            error = result.stderr.strip() or result.stdout.strip() or "未知错误"
            return (False, error)
    except FileNotFoundError:
        return (False, "未找到 Git，请先安装 Git")
    except subprocess.TimeoutExpired:
        return (False, "Git 操作超时，请检查网络")
    except Exception as e:
        return (False, f"Git 操作异常: {e}")


def clone_repo(repo_url: str, cache_dir: str) -> Tuple[bool, str]:
    """克隆仓库到本地缓存目录"""
    cache_path = Path(cache_dir)

    # 如果目录已存在且是 git 仓库，则跳过克隆
    if cache_path.exists() and (cache_path / ".git").exists():
        return (True, "仓库已存在")

    # 如果目录存在但不是 git 仓库，先删除
    if cache_path.exists():
        import shutil
        shutil.rmtree(cache_path)

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    return _run_git(["clone", repo_url, str(cache_path)], str(cache_path.parent))


def pull_repo(cache_dir: str) -> Tuple[bool, str]:
    """拉取仓库最新内容"""
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆，请先设置仓库地址")
    return _run_git(["pull", "--rebase"], cache_dir)


def commit_and_push(cache_dir: str, files: list[str], message: str) -> Tuple[bool, str]:
    """
    添加文件、提交并推送到远程仓库
    files: 相对于 cache_dir 的文件名列表
    """
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆")

    # git add
    ok, msg = _run_git(["add"] + files, cache_dir)
    if not ok:
        return (False, f"git add 失败: {msg}")

    # git commit
    ok, msg = _run_git(["commit", "-m", message], cache_dir)
    if not ok:
        # 检查是否 "nothing to commit"
        if "nothing to commit" in msg.lower() or "nothing added" in msg.lower():
            pass  # 没有变更也算成功
        else:
            return (False, f"git commit 失败: {msg}")

    # git push
    ok, msg = _run_git(["push"], cache_dir)
    if not ok:
        return (False, f"git push 失败: {msg}")

    return (True, "提交并推送成功")
