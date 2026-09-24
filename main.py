"""Terraria map synchronization desktop application."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app_resources import asset_path
from config_manager import APP_NAME, load_config
from ui.main_window import MainWindow
from ui.theme import STYLE_SHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setStyleSheet(STYLE_SHEET)
    app.setWindowIcon(QIcon(str(asset_path("logo.png"))))

    config = load_config()
    window = MainWindow(config)
    window.show()
    if not config.get("setup_complete"):
        QTimer.singleShot(0, window.open_setup_wizard)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
