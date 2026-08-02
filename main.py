"""泰拉瑞亚联机地图同步小助手 — 程序入口"""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from config_manager import load_config, APP_NAME
from ui.main_window import MainWindow


def main():
    # 高DPI适配 (PySide6 默认已启用，此处为兼容旧版)
    aa = Qt.ApplicationAttribute
    QApplication.setAttribute(aa.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(aa.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)

    # 设置默认字体，确保中文正常显示
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 加载配置
    config = load_config()

    # 创建并显示主窗口
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
