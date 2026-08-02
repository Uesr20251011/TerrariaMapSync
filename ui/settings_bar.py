"""顶部设置栏 — Worlds 路径选择 + 仓库地址输入"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Signal

from config_manager import save_config


class SettingsBar(QWidget):
    """设置栏组件"""

    world_path_changed = Signal(str)    # Worlds 路径变更
    repo_changed = Signal(str)           # 仓库地址变更
    sync_repo_requested = Signal()       # 请求克隆/更新仓库

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._init_ui()
        self._load_config_values()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # — 地图文件夹 —
        layout.addWidget(QLabel("地图文件夹:"))

        self.worlds_path_edit = QLineEdit()
        self.worlds_path_edit.setPlaceholderText("选择泰拉瑞亚 Worlds 文件夹...")
        self.worlds_path_edit.setMinimumWidth(250)
        self.worlds_path_edit.textChanged.connect(self._on_worlds_path_changed)
        layout.addWidget(self.worlds_path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_worlds_path)
        layout.addWidget(browse_btn)

        # 分隔线
        sep = QLabel("│")
        sep.setStyleSheet("color: #ccc;")
        layout.addWidget(sep)

        # — 仓库地址 —
        layout.addWidget(QLabel("仓库地址:"))

        self.repo_url_edit = QLineEdit()
        self.repo_url_edit.setPlaceholderText("https://github.com/user/repo.git")
        self.repo_url_edit.setMinimumWidth(250)
        self.repo_url_edit.textChanged.connect(self._on_repo_url_changed)
        layout.addWidget(self.repo_url_edit)

        self.sync_btn = QPushButton("克隆/更新")
        self.sync_btn.setToolTip("克隆仓库（首次）或拉取最新")
        self.sync_btn.clicked.connect(lambda: self.sync_repo_requested.emit())
        layout.addWidget(self.sync_btn)

    def _load_config_values(self):
        """加载配置到界面控件"""
        if self._config.get("worlds_path"):
            self.worlds_path_edit.setText(self._config["worlds_path"])
        if self._config.get("repo_url"):
            self.repo_url_edit.setText(self._config["repo_url"])

    def _browse_worlds_path(self):
        """浏览选择 Worlds 文件夹"""
        current = self.worlds_path_edit.text().strip()
        # 默认位置
        if not current:
            import os
            current = os.path.join(
                os.environ.get("USERPROFILE", ""),
                "Documents", "My Games", "Terraria", "Worlds"
            )

        folder = QFileDialog.getExistingDirectory(
            self, "选择泰拉瑞亚 Worlds 文件夹", current
        )
        if folder:
            self.worlds_path_edit.setText(folder)

    def _on_worlds_path_changed(self, text: str):
        path = text.strip()
        if path:
            self._config["worlds_path"] = path
            save_config(self._config)
        self.world_path_changed.emit(path)

    def _on_repo_url_changed(self, text: str):
        url = text.strip()
        if url:
            self._config["repo_url"] = url
            save_config(self._config)
        self.repo_changed.emit(url)

    def get_worlds_path(self) -> str:
        return self.worlds_path_edit.text().strip()

    def get_repo_url(self) -> str:
        return self.repo_url_edit.text().strip()
