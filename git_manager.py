"""Git 操作模块 — clone, pull, commit, push"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

# gh.exe 路径（用于认证）
_GH_PATH = r"C:\Program Files\GitHub CLI\gh.exe"

# git-askpass Python 脚本路径
_ASKPASS_DIR = os.path.join(os.environ.get("APPDATA", ""), "TerrariaMapHelper")
_ASKPASS_SCRIPT = os.path.join(_ASKPASS_DIR, "git-askpass.py")


def _ensure_askpass_script() -> str:
    """确保 askpass Python 脚本存在，返回 GIT_ASKPASS 值"""
    os.makedirs(_ASKPASS_DIR, exist_ok=True)

    if not os.path.isfile(_ASKPASS_SCRIPT):
        with open(_ASKPASS_SCRIPT, "w", encoding="ascii") as f:
            f.write(
                'import subprocess, sys\r\n'
                f'r = subprocess.run([r"{_GH_PATH}", "auth", "token"],'
                f' capture_output=True, text=True, timeout=10)\r\n'
                'if r.returncode == 0:\r\n'
                '    print(r.stdout.strip())\r\n'
                'else:\r\n'
                '    sys.exit(1)\r\n'
            )

    # 返回 "python.exe path/to/askpass.py"
    return f"{sys.executable} {_ASKPASS_SCRIPT}"


def _setup_auth() -> dict[str, str]:
    """准备带认证信息的环境变量"""
    env = os.environ.copy()
    env["GIT_ASKPASS"] = _ensure_askpass_script()
    env["GIT_TERMINAL_PROMPT"] = "0"

    # 确保 SSH URL 自动转为 HTTPS（一次性的全局配置）
    subprocess.run(
        ["git", "config", "--global",
         "url.https://github.com/.insteadOf", "git@github.com:"],
        capture_output=True, timeout=10,
    )

    return env


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
    env = _setup_auth()

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            env=env,
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

    if cache_path.exists() and (cache_path / ".git").exists():
        return (True, "仓库已存在")

    if cache_path.exists():
        import shutil
        shutil.rmtree(cache_path, ignore_errors=True)

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    return _run_git(["clone", repo_url, str(cache_path)], str(cache_path.parent))


def pull_repo(cache_dir: str) -> Tuple[bool, str]:
    """拉取仓库最新内容"""
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆，请先设置仓库地址")
    return _run_git(["pull", "--rebase"], cache_dir)


def commit_and_push(cache_dir: str, files: list[str], message: str) -> Tuple[bool, str]:
    """添加文件、提交并推送到远程仓库"""
    if not (Path(cache_dir) / ".git").exists():
        return (False, "仓库尚未克隆")

    ok, msg = _run_git(["add"] + files, cache_dir)
    if not ok:
        return (False, f"git add 失败: {msg}")

    ok, msg = _run_git(["commit", "-m", message], cache_dir)
    if not ok:
        if "nothing to commit" in msg.lower() or "nothing added" in msg.lower():
            pass
        else:
            return (False, f"git commit 失败: {msg}")

    ok, msg = _run_git(["push"], cache_dir)
    if not ok:
        return (False, f"git push 失败: {msg}")

    return (True, "提交并推送成功")
