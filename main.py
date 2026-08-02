"""泰拉瑞亚联机地图同步助手 — 程序入口

支持两种模式:
- 普通启动: 显示 GUI
- --askpass 模式: 输出 GitHub token 并退出 (供 git 凭据调用)
"""

import sys
import os


def _run_askpass():
    """输出 GitHub token 到 stdout，不启动 GUI"""
    import subprocess
    from datetime import datetime

    gh = r"C:\Program Files\GitHub CLI\gh.exe"

    # 快速日志（不引入 logger.py 避免循环依赖）
    log_dir = os.path.join(os.environ.get("APPDATA", ""), "TerrariaMapHelper", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")

    if not os.path.isfile(gh):
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"{datetime.now().strftime('%H:%M:%S')} [ASKPASS] gh.exe not found\n")
        sys.exit(1)

    cf = 0x08000000 if sys.platform == "win32" else 0
    t0 = datetime.now()
    r = subprocess.run(
        [gh, "auth", "token"],
        capture_output=True, text=True, timeout=10,
        creationflags=cf,
    )
    dt = (datetime.now() - t0).total_seconds()
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"{datetime.now().strftime('%H:%M:%S')} [ASKPASS] rc={r.returncode} dt={dt:.1f}s\n")
    if r.returncode == 0:
        print(r.stdout.strip())
    else:
        sys.exit(1)


def main():
    # ====== askpass 模式 ======
    if "--askpass" in sys.argv:
        _run_askpass()
        return

    # ====== GUI 模式 ======
    # 隐藏控制台窗口（因为用 --console 打包）
    if sys.platform == "win32":
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    from config_manager import load_config, APP_NAME
    from ui.main_window import MainWindow

    # 高 DPI
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)

    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    config = load_config()
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
