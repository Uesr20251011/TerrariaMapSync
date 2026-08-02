"""Git 凭据助手 — 被 git 调用时输出 GitHub token，不启动 GUI"""
import subprocess
import sys
import os

if sys.platform == "win32":
    # 禁止弹出控制台窗口
    _CF = 0x08000000
else:
    _CF = 0

r = subprocess.run(
    [r"C:\Program Files\GitHub CLI\gh.exe", "auth", "token"],
    capture_output=True,
    text=True,
    timeout=10,
    creationflags=_CF,
)

if r.returncode == 0:
    print(r.stdout.strip())
else:
    sys.exit(1)
