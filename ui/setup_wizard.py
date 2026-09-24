"""First-run guide for Git, GitHub login, and the map repository."""

from pathlib import Path

from PySide6.QtCore import QProcess, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWizard, QWizardPage,
)

from config_manager import save_config
from git_manager import clone_repo
from setup_services import (
    GH_DOWNLOAD_URL, GIT_DOWNLOAD_URL, check_git_installation,
    check_github_cli, is_github_repo_url,
)
from tool_paths import find_executable
from ui.theme import apply_glass_backdrop


class RequirementsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("准备运行环境")
        self.setSubTitle("只需安装一次。安装完成后回到这里点击“重新检测”。")
        self._ready = False
        layout = QVBoxLayout(self)
        self.git_status = QLabel()
        self.gh_status = QLabel()
        layout.addWidget(QLabel("1. Git 负责传输地图。Windows 安装程序使用默认选项，逐步点“下一步”即可。"))
        layout.addWidget(self.git_status)
        git_link = QPushButton("打开 Git 下载页")
        git_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GIT_DOWNLOAD_URL)))
        layout.addWidget(git_link)
        layout.addSpacing(14)
        layout.addWidget(QLabel("2. GitHub CLI 负责网页登录。安装程序使用默认选项即可。"))
        layout.addWidget(self.gh_status)
        gh_link = QPushButton("打开 GitHub CLI 下载页")
        gh_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GH_DOWNLOAD_URL)))
        layout.addWidget(gh_link)
        recheck = QPushButton("重新检测")
        recheck.clicked.connect(self.refresh)
        layout.addWidget(recheck)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        git_ok, git_message = check_git_installation()
        gh_ok, gh_message = check_github_cli()
        self.git_status.setText(("✓ " if git_ok else "✗ ") + git_message)
        self.gh_status.setText(("✓ " if gh_ok else "✗ ") + gh_message)
        self._ready = git_ok and gh_ok
        self.completeChanged.emit()

    def isComplete(self):
        return self._ready


class LoginPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("登录 GitHub")
        self.setSubTitle("点击网页登录；验证码会自动复制到剪贴板，无需配置 SSH 密钥。")
        self._ready = False
        layout = QVBoxLayout(self)
        self.status = QLabel("等待检测")
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.login_button = QPushButton("打开浏览器登录")
        self.login_button.clicked.connect(self.start_login)
        buttons.addWidget(self.login_button)
        self.check_button = QPushButton("重新检测登录")
        self.check_button.clicked.connect(self.refresh)
        buttons.addWidget(self.check_button)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("浏览器授权完成后，返回这里点击“重新检测登录”。"))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("登录进度会显示在这里")
        layout.addWidget(self.output)
        self.check_process = QProcess(self)
        self.check_process.finished.connect(self._check_finished)
        self.login_process = QProcess(self)
        self.login_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.login_process.readyReadStandardOutput.connect(self._read_login_output)
        self.login_process.finished.connect(self._login_finished)

    def initializePage(self):
        self.refresh()

    def refresh(self):
        gh = find_executable("gh")
        if not gh:
            self.status.setText("✗ 请先安装 GitHub CLI")
            return
        if self.check_process.state() != QProcess.ProcessState.NotRunning:
            return
        self.status.setText("正在检测 GitHub 登录状态…")
        self.check_button.setEnabled(False)
        self.check_process.start(gh, ["auth", "status", "--hostname", "github.com"])

    def _check_finished(self, exit_code, _status):
        self.check_button.setEnabled(True)
        self._ready = exit_code == 0
        self.status.setText("✓ GitHub 已登录" if self._ready else "✗ 尚未登录或登录已失效")
        self.completeChanged.emit()

    def start_login(self):
        gh = find_executable("gh")
        if not gh or self.login_process.state() != QProcess.ProcessState.NotRunning:
            return
        self._ready = False
        self.completeChanged.emit()
        self.output.clear()
        self.status.setText("正在打开浏览器；验证码已请求复制到剪贴板…")
        self.login_button.setEnabled(False)
        self.login_process.start(gh, ["auth", "login", "--hostname", "github.com",
                                      "--git-protocol", "https", "--web", "--clipboard"])

    def _read_login_output(self):
        data = bytes(self.login_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.output.insertPlainText(data)

    def _login_finished(self, _exit_code, _status):
        self._read_login_output()
        self.login_button.setEnabled(True)
        self.refresh()

    def isComplete(self):
        return self._ready


class RepositoryWorker(QThread):
    result_ready = Signal(bool, str)

    def __init__(self, repo_url: str, cache_dir: str):
        super().__init__()
        self.repo_url = repo_url
        self.cache_dir = cache_dir

    def run(self):
        try:
            self.result_ready.emit(*clone_repo(self.repo_url, self.cache_dir))
        except Exception as error:
            self.result_ready.emit(False, str(error))


class RepositoryPage(QWizardPage):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._ready = False
        self._worker = None
        self._checked_values = None
        self.setTitle("选择地图并连接仓库")
        self.setSubTitle("选择泰拉瑞亚 Worlds 文件夹，粘贴朋友分享的 GitHub 仓库地址。")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.worlds_edit = QLineEdit(config.get("worlds_path", ""))
        self.worlds_edit.setPlaceholderText("Documents\\My Games\\Terraria\\Worlds")
        world_row = QHBoxLayout()
        world_row.addWidget(self.worlds_edit)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        world_row.addWidget(browse)
        form.addRow("地图文件夹", world_row)
        self.repo_edit = QLineEdit(config.get("repo_url", ""))
        self.repo_edit.setPlaceholderText("https://github.com/owner/TerrariaMaps.git")
        form.addRow("GitHub 仓库", self.repo_edit)
        layout.addLayout(form)
        repo_help = QLabel("还没有仓库？创建私人仓库时勾选 README，并邀请朋友成为协作者。")
        repo_help.setObjectName("mutedText")
        layout.addWidget(repo_help)
        create_repo = QPushButton("打开 GitHub 创建仓库")
        create_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/new")))
        layout.addWidget(create_repo)
        self.worlds_edit.textChanged.connect(self._invalidate)
        self.repo_edit.textChanged.connect(self._invalidate)
        self.check_button = QPushButton("检测仓库连接")
        self.check_button.clicked.connect(self.check_repository)
        layout.addWidget(self.check_button)
        self.status = QLabel("完成检测后才能结束向导。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "选择 Worlds 文件夹",
                                                   self.worlds_edit.text().strip())
        if folder:
            self.worlds_edit.setText(folder)

    def _invalidate(self, *_args):
        self._ready = False
        self.completeChanged.emit()

    def check_repository(self):
        worlds = self.worlds_edit.text().strip()
        repo_url = self.repo_edit.text().strip()
        if not Path(worlds).is_dir():
            self.status.setText("✗ 地图文件夹不存在，请选择 Terraria 的 Worlds 文件夹")
            return
        if not is_github_repo_url(repo_url):
            self.status.setText("✗ 请填写 https://github.com/用户/仓库 格式的地址")
            return
        if self._worker and self._worker.isRunning():
            return
        self.check_button.setEnabled(False)
        self.worlds_edit.setEnabled(False)
        self.repo_edit.setEnabled(False)
        self._checked_values = (worlds, repo_url)
        self.status.setText("正在连接仓库，请稍候…")
        self._worker = RepositoryWorker(repo_url, self._config["repo_cache_dir"])
        self._worker.result_ready.connect(self._on_repository_checked)
        worker = self._worker
        worker.finished.connect(lambda: self._release_worker(worker))
        self._worker.start()

    def _release_worker(self, worker: RepositoryWorker):
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def _on_repository_checked(self, ok: bool, message: str):
        self.check_button.setEnabled(True)
        self.worlds_edit.setEnabled(True)
        self.repo_edit.setEnabled(True)
        self.status.setText(("✓ " if ok else "✗ ") + message)
        confirmed = ok and self._checked_values == (self.worlds_edit.text().strip(),
                                                    self.repo_edit.text().strip())
        self._ready = confirmed
        self.completeChanged.emit()

    def isComplete(self):
        return self._ready


class SetupWizard(QWizard):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("地图同步 · 使用向导")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setMinimumSize(720, 480)
        self.prerequisites_page = RequirementsPage()
        self.login_page = LoginPage()
        self.repository_page = RepositoryPage(config)
        self.addPage(self.prerequisites_page)
        self.addPage(self.login_page)
        self.addPage(self.repository_page)
        self.setButtonText(QWizard.WizardButton.BackButton, "上一步")
        self.setButtonText(QWizard.WizardButton.NextButton, "下一步")
        self.setButtonText(QWizard.WizardButton.FinishButton, "完成")
        self.setButtonText(QWizard.WizardButton.CancelButton, "取消")
        QTimer.singleShot(0, lambda: apply_glass_backdrop(self))

    def accept(self):
        if not self.repository_page.isComplete():
            return
        self.repository_page._config["worlds_path"] = self.repository_page.worlds_edit.text().strip()
        self.repository_page._config["repo_url"] = self.repository_page.repo_edit.text().strip()
        self.repository_page._config["setup_complete"] = True
        save_config(self.repository_page._config)
        super().accept()

    def reject(self):
        if self.repository_page._worker and self.repository_page._worker.isRunning():
            self.repository_page.status.setText("正在连接仓库，请等待检测完成后再关闭")
            return
        for process in (self.login_page.login_process, self.login_page.check_process):
            if process.state() != QProcess.ProcessState.NotRunning:
                process.kill()
                process.waitForFinished(1000)
        super().reject()
