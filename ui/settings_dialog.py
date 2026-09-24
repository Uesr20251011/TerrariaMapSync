"""Editable configuration, connection diagnostics, and guide re-entry."""

from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout,
)

from config_manager import save_config
from git_manager import clone_repo
from setup_services import (
    check_git_installation, check_github_cli, check_github_login,
    is_github_repo_url, load_github_profile,
)
from ui.account_badge import AccountBadge
from ui.setup_wizard import SetupWizard
from ui.theme import apply_glass_backdrop


class ConnectionWorker(QThread):
    result_ready = Signal(object)

    def __init__(self, repo_url: str, cache_dir: str):
        super().__init__()
        self.repo_url = repo_url
        self.cache_dir = cache_dir

    def run(self):
        try:
            git_ok, git_msg = check_git_installation()
            cli_ok, cli_msg = check_github_cli()
            auth_ok, auth_msg = check_github_login() if cli_ok else (False, "请先安装 GitHub CLI")
            repo_ok, repo_msg = (False, "请先完成环境和登录检测")
            if git_ok and cli_ok and auth_ok:
                repo_ok, repo_msg = clone_repo(self.repo_url, self.cache_dir)
            login, avatar = load_github_profile() if auth_ok else ("", b"")
        except Exception as error:
            git_ok, git_msg = False, "检测失败"
            cli_ok, cli_msg = False, "检测失败"
            auth_ok, auth_msg = False, "检测失败"
            repo_ok, repo_msg = False, str(error)
            login, avatar = "", b""
        self.result_ready.emit({
            "git": (git_ok, git_msg), "cli": (cli_ok, cli_msg),
            "auth": (auth_ok, auth_msg), "repo": (repo_ok, repo_msg),
            "login": login, "avatar": avatar,
        })


class SettingsDialog(QDialog):
    configuration_changed = Signal()

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._worker = None
        self.setWindowTitle("设置与连接检测")
        self.setMinimumSize(760, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(18)
        title = QLabel("设置与连接")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel("在这里更改地图目录和仓库，并随时检查连接。"))
        self.account = AccountBadge(config)
        layout.addWidget(self.account)

        form = QFormLayout()
        form.setSpacing(14)
        self.worlds_edit = QLineEdit(config.get("worlds_path", ""))
        row = QHBoxLayout()
        row.addWidget(self.worlds_edit)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        form.addRow("地图目录", row)
        self.repo_edit = QLineEdit(config.get("repo_url", ""))
        form.addRow("GitHub 仓库", self.repo_edit)
        layout.addLayout(form)

        self.status = QLabel("点击“检测连接”检查 Git、GitHub 登录和地图仓库。")
        self.status.setObjectName("statusText")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.rerun_button = QPushButton("重新运行使用向导")
        self.rerun_button.clicked.connect(self.rerun_wizard)
        actions.addWidget(self.rerun_button)
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_fields)
        actions.addWidget(self.save_button)
        self.test_button = QPushButton("检测连接")
        self.test_button.setProperty("variant", "primary")
        self.test_button.clicked.connect(self.test_connection)
        actions.addWidget(self.test_button)
        layout.addLayout(actions)
        layout.addStretch()
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        close_buttons.rejected.connect(self.reject)
        layout.addWidget(close_buttons)
        QTimer.singleShot(0, lambda: apply_glass_backdrop(self))

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "选择 Worlds 文件夹",
                                                   self.worlds_edit.text().strip())
        if folder:
            self.worlds_edit.setText(folder)

    def save_fields(self) -> bool:
        worlds = self.worlds_edit.text().strip()
        repo = self.repo_edit.text().strip()
        if not Path(worlds).is_dir():
            self.status.setText("✗ 地图目录不存在")
            return False
        if not is_github_repo_url(repo):
            self.status.setText("✗ 仓库地址应为 https://github.com/用户/仓库")
            return False
        if worlds != self._config.get("worlds_path") or repo != self._config.get("repo_url"):
            self._config["setup_complete"] = False
        self._config["worlds_path"] = worlds
        self._config["repo_url"] = repo
        save_config(self._config)
        self.configuration_changed.emit()
        self.status.setText("✓ 配置已保存；点击“检测连接”确认仓库可用")
        return True

    def test_connection(self):
        if not self.save_fields() or (self._worker and self._worker.isRunning()):
            return
        self.status.setText("正在检测 Git、账号与仓库连接…")
        self.test_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.rerun_button.setEnabled(False)
        self.worlds_edit.setEnabled(False)
        self.repo_edit.setEnabled(False)
        self._worker = ConnectionWorker(self._config["repo_url"], self._config["repo_cache_dir"])
        self._worker.result_ready.connect(self._connection_checked)
        worker = self._worker
        worker.finished.connect(lambda: self._release_worker(worker))
        self._worker.start()

    def _release_worker(self, worker: ConnectionWorker):
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def _connection_checked(self, result: dict):
        self.test_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.rerun_button.setEnabled(True)
        self.worlds_edit.setEnabled(True)
        self.repo_edit.setEnabled(True)
        lines = []
        for key, title in (("git", "Git"), ("cli", "GitHub CLI"),
                           ("auth", "GitHub 登录"), ("repo", "地图仓库")):
            ok, message = result[key]
            lines.append(f"{'✓' if ok else '✗'} {title}：{message}")
        self.status.setText("\n".join(lines))
        if result["login"]:
            self._config["github_login"] = result["login"]
            self.account.set_profile(result["login"], result["avatar"])
        elif not result["auth"][0]:
            self._config["github_login"] = ""
            self.account.set_profile("")
        self._config["setup_complete"] = result["repo"][0]
        save_config(self._config)
        self.configuration_changed.emit()

    def rerun_wizard(self):
        wizard = SetupWizard(self._config, self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.worlds_edit.setText(self._config.get("worlds_path", ""))
            self.repo_edit.setText(self._config.get("repo_url", ""))
            self.account.set_profile(self._config.get("github_login", ""))
            self.status.setText("✓ 使用向导已完成")
            self.configuration_changed.emit()

    def reject(self):
        if self._worker and self._worker.isRunning():
            self.status.setText("正在检测连接，请等待完成后再关闭")
            return
        super().reject()
