"""主窗口"""

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QSplitter,
    QStatusBar, QMessageBox, QApplication, QFileDialog,
    QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import QThread, Signal, Qt

from config_manager import load_config, save_config
from map_scanner import scan_local_maps, scan_remote_maps
from git_manager import is_git_installed, clone_repo, pull_repo
from sync_ops import upload_map, download_map
from ui.settings_bar import SettingsBar
from ui.local_panel import LocalPanel
from ui.remote_panel import RemotePanel


class GitWorker(QThread):
    """后台 Git 操作线程"""
    finished = Signal(bool, str)  # (success, message)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            ok, msg = self._func(*self._args, **self._kwargs)
            self.finished.emit(ok, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._worker: GitWorker | None = None
        self._init_ui()
        self._check_git()
        self._refresh_all()

    def _init_ui(self):
        self.setWindowTitle("🗺️ 泰拉瑞亚地图同步助手")
        self.setMinimumSize(900, 550)
        self.resize(950, 600)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # === 顶部设置栏 ===
        self.settings_bar = SettingsBar(self._config)
        self.settings_bar.world_path_changed.connect(self._on_worlds_path_changed)
        self.settings_bar.repo_changed.connect(self._on_repo_changed)
        self.settings_bar.sync_repo_requested.connect(self._sync_repo)
        main_layout.addWidget(self.settings_bar)

        # === 中部：左右面板 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.local_panel = LocalPanel()
        self.local_panel.upload_requested.connect(self._upload_map)
        self.local_panel.refresh_requested.connect(self._refresh_local)
        splitter.addWidget(self.local_panel)

        self.remote_panel = RemotePanel()
        self.remote_panel.download_requested.connect(self._download_map)
        self.remote_panel.refresh_requested.connect(self._refresh_remote)
        splitter.addWidget(self.remote_panel)

        splitter.setSizes([400, 500])
        main_layout.addWidget(splitter, stretch=1)

        # === 底部：日志提示 + 状态栏 ===
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(6, 2, 6, 2)

        hint = QLabel("💡 遇到问题？请")
        bottom_layout.addWidget(hint)

        export_btn = QPushButton("📋 导出日志")
        export_btn.setFixedWidth(100)
        export_btn.clicked.connect(self._export_log)
        bottom_layout.addWidget(export_btn)

        hint2 = QLabel("发送给作者")
        bottom_layout.addWidget(hint2)

        bottom_layout.addStretch()
        main_layout.addWidget(bottom_widget)

        # === 底部状态栏 ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    # ==================== 刷新逻辑 ====================

    def _refresh_all(self):
        self._refresh_local()
        self._refresh_remote()

    def _refresh_local(self):
        path = self._config.get("worlds_path", "")
        if path:
            maps = scan_local_maps(path)
            self.local_panel.refresh_list(maps)
            self.status_bar.showMessage(f"找到 {len(maps)} 个本地地图")
        else:
            self.local_panel.refresh_list([])
            self.status_bar.showMessage("请先设置地图文件夹")

    def _refresh_remote(self):
        cache_dir = self._config.get("repo_cache_dir", "")
        if cache_dir:
            remote = scan_remote_maps(cache_dir)
            total_versions = sum(len(v) for v in remote.values())
            self.remote_panel.refresh_list(remote)
            if remote:
                self.status_bar.showMessage(
                    f"云端: {len(remote)} 个地图, {total_versions} 个版本"
                )
            else:
                self.status_bar.showMessage("云端暂无地图或仓库未克隆")
        else:
            self.remote_panel.refresh_list({})

    # ==================== 设置变更 ====================

    def _on_worlds_path_changed(self, path: str):
        self._refresh_local()

    def _on_repo_changed(self, url: str):
        # 仓库地址变更时自动尝试克隆
        if url:
            self._sync_repo()

    # ==================== Git 同步 ====================

    def _sync_repo(self):
        """克隆或更新仓库"""
        repo_url = self.settings_bar.get_repo_url()
        cache_dir = self._config.get("repo_cache_dir", "")

        if not repo_url:
            QMessageBox.warning(self, "提示", "请先输入仓库地址")
            return

        self._set_ui_enabled(False)
        self.status_bar.showMessage("正在同步仓库...")

        # 检查是否已克隆
        import os
        if os.path.isdir(os.path.join(cache_dir, ".git")):
            # 已克隆，执行 pull
            self._worker = GitWorker(pull_repo, cache_dir)
        else:
            # 首次克隆
            self._worker = GitWorker(clone_repo, repo_url, cache_dir)

        self._worker.finished.connect(self._on_sync_done)
        self._worker.start()

    def _on_sync_done(self, success: bool, message: str):
        self._set_ui_enabled(True)
        if success:
            self.status_bar.showMessage(f"✓ {message}")
            self._refresh_remote()
        else:
            self.status_bar.showMessage(f"✗ {message}")
            QMessageBox.warning(self, "同步失败", message)

    # ==================== 上传 ====================

    def _upload_map(self, map_name: str):
        """上传地图"""
        worlds_path = self._config.get("worlds_path", "")
        cache_dir = self._config.get("repo_cache_dir", "")

        if not worlds_path or not cache_dir:
            QMessageBox.warning(self, "提示", "请先设置地图文件夹和仓库地址")
            return

        # 检查仓库是否已克隆
        import os
        if not os.path.isdir(os.path.join(cache_dir, ".git")):
            reply = QMessageBox.question(
                self, "仓库未就绪",
                "仓库尚未克隆，是否现在克隆？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._sync_repo()
            return

        self._set_ui_enabled(False)
        self.status_bar.showMessage(f"正在上传 {map_name}...")

        self._worker = GitWorker(upload_map, worlds_path, cache_dir, map_name)
        self._worker.finished.connect(self._on_upload_done)
        self._worker.start()

    def _on_upload_done(self, success: bool, message: str):
        self._set_ui_enabled(True)
        if success:
            self.status_bar.showMessage(f"✓ {message}")
            self._refresh_remote()
        else:
            self.status_bar.showMessage(f"✗ {message}")
            QMessageBox.warning(self, "上传失败", message)

    # ==================== 下载 ====================

    def _download_map(self, dated_wld: str, original_name: str):
        """下载地图"""
        worlds_path = self._config.get("worlds_path", "")
        cache_dir = self._config.get("repo_cache_dir", "")

        if not worlds_path or not cache_dir:
            QMessageBox.warning(self, "提示", "请先设置地图文件夹和仓库地址")
            return

        self._set_ui_enabled(False)
        self.status_bar.showMessage(f"正在下载 {original_name}...")

        self._worker = GitWorker(
            download_map, worlds_path, cache_dir, dated_wld, original_name
        )
        self._worker.finished.connect(self._on_download_done)
        self._worker.start()

    def _on_download_done(self, success: bool, message: str):
        self._set_ui_enabled(True)
        if success:
            self.status_bar.showMessage(f"✓ {message}")
            self._refresh_local()
        else:
            self.status_bar.showMessage(f"✗ {message}")
            QMessageBox.warning(self, "下载失败", message)

    # ==================== 工具方法 ====================

    def _set_ui_enabled(self, enabled: bool):
        """操作期间禁用 UI"""
        self.settings_bar.setEnabled(enabled)
        self.local_panel.upload_btn.setEnabled(enabled and len(self.local_panel.map_list) > 0)
        self.remote_panel.download_btn.setEnabled(enabled)
        self.local_panel.refresh_btn.setEnabled(enabled)
        self.remote_panel.refresh_btn.setEnabled(enabled)

    def _export_log(self):
        """导出日志文件"""
        from logger import log_path
        src = log_path()

        if not os.path.isfile(src):
            QMessageBox.information(self, "提示", "暂无日志文件，请先执行操作")
            return

        dest, _ = QFileDialog.getSaveFileName(
            self, "导出日志", f"TerrariaMapHelper_{datetime.now().strftime('%Y%m%d')}.log",
            "日志文件 (*.log)"
        )
        if dest:
            try:
                import shutil
                shutil.copy2(src, dest)
                QMessageBox.information(self, "导出成功", f"日志已保存到:\n{dest}")
            except OSError as e:
                QMessageBox.critical(self, "导出失败", str(e))

    def _check_git(self):
        """检查 Git 是否安装"""
        if not is_git_installed():
            QMessageBox.critical(
                self,
                "Git 未安装",
                "未检测到 Git，请先安装 Git 后再使用本工具。\n\n"
                "下载地址: https://git-scm.com/download/win"
            )
