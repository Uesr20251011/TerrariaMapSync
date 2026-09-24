"""主窗口"""

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QSplitter,
    QStatusBar, QMessageBox, QApplication, QFileDialog,
    QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QPixmap

from app_resources import asset_path
from config_manager import save_config
from map_scanner import scan_local_maps, scan_remote_maps
from git_manager import clone_repo
from sync_ops import upload_map, download_map
from ui.account_badge import AccountBadge, ProfileWorker
from ui.local_panel import LocalPanel
from ui.remote_panel import RemotePanel
from ui.settings_dialog import SettingsDialog
from ui.setup_wizard import SetupWizard
from ui.theme import apply_glass_backdrop


class GitWorker(QThread):
    """后台 Git 操作线程"""
    result_ready = Signal(bool, str)  # (success, message)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        import logging
        _log = logging.getLogger("TerrariaMapHelper")
        _log.info(">>> GitWorker.run() 开始: %s", self._func.__name__)
        try:
            ok, msg = self._func(*self._args, **self._kwargs)
            _log.info(">>> GitWorker.run() 完成: ok=%s", ok)
            self.result_ready.emit(ok, msg)
        except Exception as e:
            _log.exception(">>> GitWorker.run() 异常")
            self.result_ready.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._worker: GitWorker | None = None
        self._profile_worker: ProfileWorker | None = None
        self._init_ui()
        self._refresh_all()
        if config.get("setup_complete"):
            QTimer.singleShot(0, self._refresh_profile)

    def _init_ui(self):
        self.setWindowTitle("🗺️ 泰拉瑞亚地图同步助手")
        self.setMinimumSize(980, 620)
        self.resize(1120, 720)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 18, 20, 16)
        main_layout.setSpacing(16)

        header = QFrame()
        header.setObjectName("glassCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        header_layout.setSpacing(14)
        mark = QLabel()
        mark.setPixmap(QPixmap(str(asset_path("logo.png"))).scaled(
            54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(mark)
        brand = QVBoxLayout()
        brand_title = QLabel("地图同步")
        brand_title.setObjectName("brandTitle")
        brand.addWidget(brand_title)
        self.repo_hint = QLabel()
        self.repo_hint.setObjectName("sectionHint")
        brand.addWidget(self.repo_hint)
        header_layout.addLayout(brand)
        header_layout.addStretch()
        self.account = AccountBadge(self._config)
        header_layout.addWidget(self.account)
        self.settings_btn = QPushButton("设置与检测")
        self.settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(self.settings_btn)
        main_layout.addWidget(header)
        self._update_repo_hint()

        # === 中部：左右面板 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.local_panel = LocalPanel()
        self.local_panel.upload_requested.connect(self._upload_map)
        self.local_panel.refresh_requested.connect(self._refresh_local)
        splitter.addWidget(self.local_panel)

        self.remote_panel = RemotePanel()
        self.remote_panel.download_requested.connect(self._download_map)
        self.remote_panel.refresh_requested.connect(self._sync_repo)
        splitter.addWidget(self.remote_panel)

        splitter.setSizes([400, 500])
        main_layout.addWidget(splitter, stretch=1)

        # === 底部：日志提示 + 状态栏 ===
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(4, 2, 4, 2)

        hint = QLabel("同步遇到问题？")
        bottom_layout.addWidget(hint)

        export_btn = QPushButton("📋 导出日志")
        export_btn.setFixedWidth(100)
        export_btn.clicked.connect(self._export_log)
        bottom_layout.addWidget(export_btn)

        bottom_layout.addStretch()
        main_layout.addWidget(bottom_widget)

        # === 底部状态栏 ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        QTimer.singleShot(0, lambda: apply_glass_backdrop(self))

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
        if not self._config.get("setup_complete"):
            self.remote_panel.refresh_list({})
            self.status_bar.showMessage("请先在设置中检测仓库连接")
            return
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

    # ==================== Git 同步 ====================

    def _sync_repo(self):
        """克隆或更新仓库"""
        if self._operation_running():
            return
        if not self._config.get("setup_complete"):
            self.open_setup_wizard()
            return
        repo_url = self._config.get("repo_url", "")
        cache_dir = self._config.get("repo_cache_dir", "")

        if not repo_url:
            QMessageBox.warning(self, "提示", "请先在设置中填写仓库地址")
            return

        self._set_ui_enabled(False)
        self.status_bar.showMessage("正在同步仓库...")

        self._worker = GitWorker(clone_repo, repo_url, cache_dir)

        self._worker.result_ready.connect(self._on_sync_done)
        worker = self._worker
        worker.finished.connect(lambda: self._release_worker(worker))
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
        if self._operation_running():
            return
        worlds_path = self._config.get("worlds_path", "")
        cache_dir = self._config.get("repo_cache_dir", "")

        if not worlds_path or not cache_dir:
            QMessageBox.warning(self, "提示", "请先设置地图文件夹和仓库地址")
            return

        # 检查仓库是否已克隆
        import os
        if not self._config.get("setup_complete") or not os.path.isdir(os.path.join(cache_dir, ".git")):
            if not self.open_setup_wizard():
                return
            worlds_path = self._config.get("worlds_path", "")
            cache_dir = self._config.get("repo_cache_dir", "")

        self._set_ui_enabled(False)
        self.status_bar.showMessage(f"正在上传 {map_name}...")

        self._worker = GitWorker(upload_map, worlds_path, cache_dir, map_name)
        self._worker.result_ready.connect(self._on_upload_done)
        worker = self._worker
        worker.finished.connect(lambda: self._release_worker(worker))
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
        if self._operation_running():
            return
        import logging
        _log = logging.getLogger("TerrariaMapHelper")
        _log.info(">>> UI: _download_map 被调用 (%s)", original_name)

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
        self._worker.result_ready.connect(self._on_download_done)
        worker = self._worker
        worker.finished.connect(lambda: self._release_worker(worker))
        _log.info(">>> UI: 启动 GitWorker 线程...")
        self._worker.start()
        _log.info(">>> UI: GitWorker.start() 已返回")

    def _on_download_done(self, success: bool, message: str):
        import logging
        _log = logging.getLogger("TerrariaMapHelper")
        _log.info(">>> _on_download_done 被调用 ok=%s msg=%s", success, message)
        self._set_ui_enabled(True)
        _log.info(">>> _set_ui_enabled(True) 完成")
        if success:
            self.status_bar.showMessage(f"✓ {message}")
            self._refresh_local()
            _log.info(">>> _refresh_local 完成")
        else:
            self.status_bar.showMessage(f"✗ {message}")
            QMessageBox.warning(self, "下载失败", message)
        _log.info(">>> _on_download_done 全部完成")

    # ==================== 工具方法 ====================

    def _operation_running(self) -> bool:
        if self._worker and self._worker.isRunning():
            self.status_bar.showMessage("请等待当前操作完成")
            return True
        return False

    def _release_worker(self, worker: GitWorker):
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def _set_ui_enabled(self, enabled: bool):
        """操作期间禁用 UI"""
        self.settings_btn.setEnabled(enabled)
        self.local_panel.map_list.setEnabled(enabled)
        self.remote_panel.tree.setEnabled(enabled)
        self.local_panel.upload_btn.setEnabled(enabled and self.local_panel.map_list.currentItem() is not None)
        self.remote_panel.download_btn.setEnabled(
            enabled and self.remote_panel.tree.currentItem() is not None
            and bool(self.remote_panel.tree.currentItem().data(0, 1)))
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

    def _update_repo_hint(self):
        url = self._config.get("repo_url", "")
        self.repo_hint.setText(url.rsplit("/", 1)[-1].removesuffix(".git") if url else "连接你的 Terraria 世界仓库")

    def open_settings(self):
        dialog = SettingsDialog(self._config, self)
        dialog.configuration_changed.connect(self._on_config_changed)
        dialog.exec()
        self._on_config_changed()

    def open_setup_wizard(self) -> bool:
        wizard = SetupWizard(self._config, self)
        accepted = wizard.exec() == SetupWizard.DialogCode.Accepted
        if accepted:
            self._on_config_changed()
            self._refresh_profile()
        return accepted

    def _on_config_changed(self):
        self._update_repo_hint()
        self._refresh_all()
        self.account.set_profile(self._config.get("github_login", ""))

    def _refresh_profile(self):
        if self._profile_worker and self._profile_worker.isRunning():
            return
        self._profile_worker = ProfileWorker()
        self._profile_worker.profile_ready.connect(self._on_profile_ready)
        worker = self._profile_worker
        worker.finished.connect(lambda: self._release_profile_worker(worker))
        self._profile_worker.start()

    def _release_profile_worker(self, worker: ProfileWorker):
        if self._profile_worker is worker:
            self._profile_worker = None
        worker.deleteLater()

    def _on_profile_ready(self, login: str, avatar: bytes):
        if login:
            self._config["github_login"] = login
            save_config(self._config)
            self.account.set_profile(login, avatar)
