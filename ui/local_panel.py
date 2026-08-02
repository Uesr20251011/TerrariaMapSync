"""本地地图列表面板"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox,
)
from PySide6.QtCore import Signal, Qt


class LocalPanel(QGroupBox):
    """本地地图列表"""

    upload_requested = Signal(str)   # 信号: 地图名 (不含 .wld)
    refresh_requested = Signal()     # 请求刷新列表

    def __init__(self, parent=None):
        super().__init__("📁 本地地图", parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 地图列表
        self.map_list = QListWidget()
        self.map_list.setAlternatingRowColors(True)
        main_layout.addWidget(self.map_list)

        # 按钮栏
        btn_layout = QHBoxLayout()

        self.upload_btn = QPushButton("⬆ 上传选中地图")
        self.upload_btn.clicked.connect(self._on_upload)
        self.upload_btn.setEnabled(False)
        btn_layout.addWidget(self.upload_btn)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(lambda: self.refresh_requested.emit())
        btn_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(btn_layout)

    def refresh_list(self, maps: list[str]):
        """刷新地图列表

        maps: .wld 文件名列表，如 ["我的世界.wld", "冒险世界.wld"]
        """
        self.map_list.clear()

        if not maps:
            item = QListWidgetItem("（未找到地图）")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.map_list.addItem(item)
            self.upload_btn.setEnabled(False)
            return

        for map_name in maps:
            # 去掉 .wld 后缀作为显示名
            display_name = map_name[:-4] if map_name.lower().endswith(".wld") else map_name
            item = QListWidgetItem(display_name)
            item.setData(1, map_name)  # 存储完整文件名
            self.map_list.addItem(item)

        self.upload_btn.setEnabled(True)

    def _on_upload(self):
        """上传当前选中的地图"""
        selected = self.map_list.currentItem()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择一个地图")
            return

        display_name = selected.text()
        reply = QMessageBox.question(
            self, "确认上传",
            f"确定要上传地图 \"{display_name}\" 到云端吗？\n\n"
            f"云端文件名: {self._today()}{display_name}.wld",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.upload_requested.emit(display_name)

    @staticmethod
    def _today() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d")
