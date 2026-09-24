"""Small account identity component shared by the main window and settings."""

from PySide6.QtCore import QRectF, Qt, QThread, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app_resources import asset_path, avatar_cache_path
from setup_services import load_github_profile


class ProfileWorker(QThread):
    profile_ready = Signal(str, bytes)

    def run(self):
        self.profile_ready.emit(*load_github_profile())


class AccountBadge(QWidget):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("accountBadge")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(42, 42)
        layout.addWidget(self.avatar_label)
        labels = QVBoxLayout()
        labels.setSpacing(1)
        self.login_label = QLabel()
        self.login_label.setObjectName("accountName")
        labels.addWidget(self.login_label)
        subtitle = QLabel("GitHub 账号")
        subtitle.setObjectName("mutedText")
        labels.addWidget(subtitle)
        layout.addLayout(labels)
        self.set_profile(config.get("github_login", ""))

    def set_profile(self, login: str, avatar: bytes = b""):
        self.login_label.setText("@" + login if login else "尚未登录")
        cached_avatar = avatar_cache_path(login)
        if avatar:
            cached_avatar.write_bytes(avatar)
        source = QPixmap(str(cached_avatar))
        if source.isNull():
            source = QPixmap(str(asset_path("logo.png")))
        if source.isNull():
            return
        size = 42
        scaled = source.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               Qt.TransformationMode.SmoothTransformation)
        canvas = QPixmap(size, size)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, size, size), 12, 12)
        painter.setClipPath(clip)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self.avatar_label.setPixmap(canvas)
